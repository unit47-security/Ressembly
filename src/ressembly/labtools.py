"""Bounded lab patterns and static ELF64/x86-64 properties; no exploitability verdict."""
import hashlib
import struct
from pathlib import Path

MAX_PATTERN = 1024 * 1024
MAX_ELF = 64 * 1024 * 1024


def _parameters(length, width, alphabet):
    if type(length) is not int or not 0 <= length <= MAX_PATTERN:
        raise ValueError('length must be 0..1048576')
    if type(width) is not int or not 2 <= width <= 8:
        raise ValueError('width must be 2..8')
    if not isinstance(alphabet, bytes) or not 2 <= len(alphabet) <= 64 or len(set(alphabet)) != len(alphabet):
        raise ValueError('alphabet must contain 2..64 distinct bytes')
    if length > len(alphabet) ** width:
        raise ValueError('length exceeds the unique cyclic sequence')


def cyclic(length, width=4, alphabet=b'abcdefghijklmnopqrstuvwxyz'):
    """Prefix of a de Bruijn sequence, without wrapping or repeating the cycle."""
    _parameters(length, width, alphabet)
    if not length:
        return b''
    state = [0] * (len(alphabet) * width + 1)

    def generate(t, period):
        if t > width:
            if width % period == 0:
                for index in range(1, period + 1):
                    yield alphabet[state[index]]
        else:
            state[t] = state[t - period]
            yield from generate(t + 1, period)
            for value in range(state[t - period] + 1, len(alphabet)):
                state[t] = value
                yield from generate(t + 1, t)

    result = bytearray()
    for value in generate(1, 1):
        result.append(value)
        if len(result) == length:
            break
    return bytes(result)


def cyclic_offset(value, length, width=4, endian='little', alphabet=b'abcdefghijklmnopqrstuvwxyz'):
    """Search only the requested prefix; short byte queries may be ambiguous."""
    _parameters(length, width, alphabet)
    if endian not in ('little', 'big'):
        raise ValueError('endian must be little or big')
    if type(value) is int:
        if not 0 <= value < 1 << (8 * width):
            raise ValueError('integer does not fit the explicit width')
        needle = value.to_bytes(width, endian)
    elif isinstance(value, bytes) and 1 <= len(value) <= width:
        needle = value
    else:
        raise ValueError('value must be an integer or 1..width bytes')
    pattern = cyclic(length, width, alphabet)
    offsets, start, truncated = [], 0, False
    while True:
        index = pattern.find(needle, start)
        if index < 0:
            break
        if len(offsets) == 100:
            truncated = True
            break
        offsets.append(index)
        start = index + 1
    return {'status': 'not_found' if not offsets else 'unique' if len(offsets) == 1 else 'ambiguous',
            'offsets': offsets, 'offsets_truncated': truncated, 'needle_hex': needle.hex(),
            'searched_length': length, 'width': width, 'integer_endian': endian,
            'alphabet_hex': alphabet.hex()}


class ELFError(ValueError):
    pass


def elf_properties(path):
    """Parse a bounded regular file, without loading or executing the target."""
    path = Path(path)
    if not path.is_file():
        raise ELFError('ELF input must be an existing regular file')
    with path.open('rb') as stream:
        data = stream.read(MAX_ELF + 1)
    if len(data) > MAX_ELF:
        raise ELFError('ELF exceeds 64 MiB budget')
    result = inspect_elf(data)
    result.update(path=str(path.resolve()), sha256=hashlib.sha256(data).hexdigest(), size=len(data))
    return result


def inspect_elf(data):
    """ELF64 little-endian amd64 ET_EXEC/ET_DYN, ordinary numbering only."""
    if not isinstance(data, bytes) or not 64 <= len(data) <= MAX_ELF:
        raise ELFError('invalid ELF size')

    def unpack(fmt, offset):
        size = struct.calcsize(fmt)
        if offset < 0 or offset + size > len(data):
            raise ELFError('truncated ELF structure')
        return struct.unpack_from(fmt, data, offset)

    def span(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ELFError('ELF range outside file')
        return memoryview(data)[offset:offset + size]

    ident = data[:16]
    if ident[:7] != b'\x7fELF\x02\x01\x01':
        raise ELFError('only ELF64 little-endian version 1 is supported')
    typ, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = unpack('<HHIQQQIHHHHHH', 16)
    if machine != 62 or typ not in (2, 3) or version != 1 or ehsize != 64:
        raise ELFError('only amd64 ET_EXEC/ET_DYN version 1 is supported')
    if not 1 <= phnum <= 1024 or phsize != 56 or phoff < 64:
        raise ELFError('unsupported or missing program-header table')
    if shnum > 8192 or (shnum and (shsize != 64 or shoff < 64)) or (shoff and not shnum):
        raise ELFError('unsupported section table or extended numbering')
    span(phoff, phnum * phsize)
    if shnum:
        span(shoff, shnum * shsize)
        if shstr >= shnum and shstr != 0:
            raise ELFError('invalid section-name table index')
    program = [unpack('<IIQQQQQQ', phoff + i * phsize) for i in range(phnum)]
    for ptype, pflags, off, va, pa, filesz, memsz, align in program:
        span(off, filesz)
        if ptype == 1 and filesz > memsz:
            raise ELFError('load file size exceeds memory size')
    stacks = [p for p in program if p[0] == 0x6474e551]
    dynamic = [p for p in program if p[0] == 2]
    if len(stacks) > 1 or len(dynamic) > 1:
        raise ELFError('duplicate stack or dynamic segments')
    tags = []
    for p in dynamic:
        if p[5] % 16 or p[5] // 16 > 65536:
            raise ELFError('invalid or excessive dynamic table')
        terminated = False
        for off in range(p[2], p[2] + p[5], 16):
            tag, value = unpack('<qQ', off)
            if tag == 0:
                terminated = True
                break
            tags.append((tag, value))
        if not terminated:
            raise ELFError('unterminated dynamic table')
    bind_now = any(tag == 24 or (tag == 30 and value & 8) or
                   (tag == 0x6ffffffb and value & 1) for tag, value in tags)
    pie_flag = any(tag == 0x6ffffffb and value & 0x08000000 for tag, value in tags)
    relro = any(p[0] == 0x6474e552 and p[6] > 0 for p in program)
    sections = [unpack('<IIQQQQIIQQ', shoff + i * shsize) for i in range(shnum)]
    for section in sections:
        if section[1] != 8:
            span(section[4], section[5])
    canaries, scanned, symbol_count, name_bytes = [], 0, 0, 0
    for table_index, section in enumerate(sections):
        if section[1] not in (2, 11):
            continue
        off, size, link, entsize = section[4], section[5], section[6], section[9]
        if entsize != 24 or size % entsize or size // entsize > 100000 or link >= shnum:
            raise ELFError('invalid or excessive symbol table')
        symbol_count += size // entsize
        if symbol_count > 100000:
            raise ELFError('total symbol budget exceeded')
        strings = sections[link]
        if strings[1] != 3:
            raise ELFError('symbol table link is not a string table')
        span(strings[4], strings[5])
        scanned += 1
        for offset in range(off, off + size, entsize):
            name, info, other, ndx, value, symsize = unpack('<IBBHQQ', offset)
            if name >= strings[5]:
                raise ELFError('invalid symbol name offset')
            start = strings[4] + name
            end = data.find(b'\0', start, min(start + 4096, strings[4] + strings[5]))
            if end < 0:
                raise ELFError('unterminated or excessive symbol name')
            name_bytes += end - start
            if name_bytes > 16 * 1024 * 1024:
                raise ELFError('symbol name scanning budget exceeded')
            symbol = data[start:end]
            if symbol in (b'__stack_chk_fail', b'__stack_chk_fail_local', b'__stack_chk_guard'):
                canaries.append({'name': symbol.decode('ascii'), 'table_index': table_index,
                                 'binding': 'undefined' if ndx == 0 else 'defined'})
    return {'schema': 'ressembly.elf-properties.v1', 'architecture': 'amd64',
            'elf_type': 'ET_EXEC' if typ == 2 else 'ET_DYN',
            'pie': 'yes' if typ == 3 and pie_flag else 'no' if typ == 2 else 'undetermined',
            'pie_flag': pie_flag, 'interpreter_segment': any(p[0] == 3 for p in program),
            'stack_execution': 'unknown' if not stacks else 'requested' if stacks[0][1] & 1 else 'not_requested',
            'nx_stack': 'unknown' if not stacks else 'no' if stacks[0][1] & 1 else 'yes',
            'relro': 'full_configuration' if relro and bind_now else 'partial_configuration' if relro else 'none',
            'bind_now': bind_now, 'gnu_relro_segment': relro,
            'canary_indicator': 'symbol_present' if canaries else 'not_observed' if scanned else 'unknown_no_symbol_tables',
            'canary_symbols': canaries, 'symbol_tables_scanned': scanned,
            'limits': ['Static file properties, not runtime enforcement or exploitability.',
                       'Canary symbol evidence does not establish per-function instrumentation.',
                       'Symbol absence does not prove absence of stack protection.',
                       'No ASLR runtime, CET, fortify, PAC, or dependency coverage.']}
