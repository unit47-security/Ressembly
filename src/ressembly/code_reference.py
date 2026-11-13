"""Identity-preserving links between an ELF file offset and a runtime code address."""
import hashlib
import struct
from .experiments import require, read_bytes, sha
from .labtools import inspect_elf, MAX_ELF


def virtual_address(data, offset):
    inspect_elf(data)
    require(type(offset) is int and 0 <= offset < len(data), 'file offset outside binary')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    phnum = struct.unpack_from('<H', data, 56)[0]
    addresses = set()
    for index in range(phnum):
        typ, flags, fileoff, vaddr, _, size, memsize, _ = struct.unpack_from('<IIQQQQQQ', data, phoff + index * 56)
        if typ == 1:
            require(vaddr + memsize <= 2**64 and vaddr + size <= 2**64, 'ELF virtual segment overflows uint64')
        if typ == 1 and flags & 1 and fileoff <= offset < fileoff + size:
            addresses.add(vaddr + offset - fileoff)
    require(len(addresses) == 1, 'offset must resolve uniquely to executable ELF file bytes')
    return addresses.pop()


def validate(reference, binary):
    require(isinstance(reference, dict) and reference.get('schema') == 'ressembly.code-reference.v1', 'unsupported reference schema')
    sha(reference.get('module_sha256'))
    data = read_bytes(binary, MAX_ELF)
    require(hashlib.sha256(data).hexdigest() == reference['module_sha256'], 'binary build hash mismatch')
    offset = reference.get('file_offset')
    expected_va = virtual_address(data, offset)
    require(type(reference.get('elf_virtual_address')) is int and reference['elf_virtual_address'] == expected_va,
            'ELF virtual address contradicts file offset')
    for key in ('runtime_pc', 'mapping_start', 'mapping_end', 'mapping_offset'):
        require(type(reference.get(key)) is int and 0 <= reference[key] < 2**64, 'invalid ' + key)
    require(reference['mapping_start'] <= reference['runtime_pc'] < reference['mapping_end'], 'runtime PC outside mapping')
    require(offset == reference['mapping_offset'] + reference['runtime_pc'] - reference['mapping_start'], 'runtime mapping contradicts file offset')
    require(isinstance(reference.get('run_id'), str) and 0 < len(reference['run_id']) < 128, 'run identity missing')
    sample = reference.get('file_bytes_hex')
    require(isinstance(sample, str) and 2 <= len(sample) <= 32 and len(sample) % 2 == 0, 'invalid code sample')
    try: expected = bytes.fromhex(sample)
    except ValueError as error: raise ValueError('invalid sample encoding') from error
    require(data[offset:offset + len(expected)] == expected, 'reference code bytes differ from binary')
    return reference
