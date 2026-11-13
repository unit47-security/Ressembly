"""Read-only Linux AMD64 context and memory commands; no stop callbacks."""
import hashlib
import json
import os
import platform
import uuid
import gdb
from .debug_core import checked_range, parse_maps, readable_prefix, find_matches, walk_pointers

REGISTERS = ('rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp',
             'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15', 'rip', 'eflags')


def target():
    inferior = gdb.selected_inferior()
    thread = gdb.selected_thread()
    if platform.system() != 'Linux' or not inferior.pid or thread is None:
        raise ValueError('requires a live local Linux inferior stopped in GDB')
    if inferior.connection is None or inferior.connection.type != 'native':
        raise ValueError('only a local native GDB connection is supported')
    threads = inferior.threads()
    if len(threads) != 1 or not thread.is_stopped():
        raise ValueError('requires a stopped single-thread inferior')
    frame = gdb.newest_frame()
    if frame is None or frame.architecture().name() != 'i386:x86-64':
        raise ValueError('only Linux x86-64 is supported')
    return inferior, thread, frame


def read_maps(inferior):
    with open('/proc/{}/maps'.format(inferior.pid), encoding='utf-8') as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError('maps exceeds 2 MiB budget')
    return parse_maps(data)


def read(inferior, regions, address, size):
    checked_range(address, size, 65536)
    if readable_prefix(regions, address, size) != size:
        raise ValueError('range is unmapped or lacks read permission')
    try:
        return bytes(inferior.read_memory(address, size))
    except gdb.error as error:
        raise ValueError('GDB memory read failed: ' + str(error)) from error


def metadata(inferior, thread, frame):
    proc = '/proc/{}/'.format(inferior.pid)
    digest = hashlib.sha256()
    with open(proc + 'exe', 'rb') as stream:
        if os.fstat(stream.fileno()).st_size > 256 * 1024 * 1024:
            raise ValueError('executable exceeds 256 MiB hash budget')
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    with open(proc + 'stat', encoding='utf-8') as stream:
        start_ticks = stream.read().rsplit(')', 1)[1].split()[19]
    with open('/proc/sys/kernel/random/boot_id', encoding='ascii') as stream:
        boot = stream.read().strip()
    return dict(pid=inferior.pid, inferior=inferior.num, thread=thread.global_num,
                run_id='{}:{}:{}'.format(boot, inferior.pid, start_ticks),
                executable=os.readlink(proc + 'exe'), executable_sha256=digest.hexdigest(),
                architecture=frame.architecture().name(), gdb_version=gdb.VERSION,
                platform=platform.platform(), frame_scope='newest frame of selected thread',
                argv_setting=gdb.parameter('args'),
                argv_provenance='GDB configuration; not proof of input consumed')


def context_snapshot():
    inferior, thread, frame = target()
    result = dict(schema='ressembly.debug-context.v1', snapshot_id=str(uuid.uuid4()),
                  metadata=metadata(inferior, thread, frame), registers={}, assembly={},
                  stack={}, breakpoints=[], errors={})
    for name in REGISTERS:
        try:
            result['registers'][name] = int(frame.read_register(name)) & ((1 << 64) - 1)
        except (gdb.error, ValueError) as error:
            result['registers'][name] = None
            result['errors']['register:' + name] = str(error)
    pc = result['registers'].get('rip')
    try:
        if pc is None:
            raise ValueError('instruction pointer unavailable')
        result['assembly'] = dict(start=pc, instructions=frame.architecture().disassemble(pc, count=8),
                                  direction='forward from current PC', requested_count=8)
    except (gdb.error, ValueError) as error:
        result['errors']['assembly'] = str(error)
    try:
        sp = result['registers'].get('rsp')
        if sp is None:
            raise ValueError('stack pointer unavailable')
        data = read(inferior, read_maps(inferior), sp, 64)
        result['stack'] = dict(address=sp, size=64, hex=data.hex(),
                              words=[int.from_bytes(data[i:i+8], 'little') for i in range(0, 64, 8)])
    except (OSError, ValueError, gdb.error) as error:
        result['errors']['stack'] = str(error)
    for breakpoint in gdb.breakpoints() or ():
        item = dict(number=breakpoint.number, type=breakpoint.type, enabled=breakpoint.enabled,
                    location=breakpoint.location, pending=breakpoint.pending,
                    temporary=breakpoint.temporary, hit_count=breakpoint.hit_count)
        result['breakpoints'].append(item)
    result['status'] = 'partial' if result['errors'] else 'complete'
    result['coverage'] = 'point-in-time snapshot; no history, writes, or exploitability inference'
    return result


def memory_maps():
    inferior, _, _ = target()
    return dict(schema='ressembly.memory-maps.v1', pid=inferior.pid, regions=read_maps(inferior),
                source='local /proc/PID/maps; current stopped process')


def memory_dump(address, length):
    checked_range(address, length, 4096)
    inferior, _, _ = target()
    data = read(inferior, read_maps(inferior), address, length)
    return dict(schema='ressembly.memory-dump.v1', pid=inferior.pid, address=address,
                length=length, hex=data.hex(), status='complete')


def memory_search(address, length, pattern, matches=256):
    checked_range(address, length, 65536)
    find_matches(b'', pattern, matches)
    inferior, _, _ = target()
    regions = read_maps(inferior)
    readable = readable_prefix(regions, address, length)
    data = read(inferior, regions, address, readable) if readable else b''
    offsets, truncated = find_matches(data, pattern, matches)
    return dict(schema='ressembly.memory-search.v1', pid=inferior.pid, address=address,
                requested_bytes=length, bytes_read=readable,
                scanned_bytes=None if truncated else readable, pattern_hex=pattern.hex(),
                matches=[address + offset for offset in offsets],
                status='partial' if readable != length or truncated else 'complete',
                reason='match_limit' if truncated else 'unreadable_boundary' if readable != length else None,
                coverage='only requested readable prefix; overlapping matches included')


def pointer_chain(address, depth=8):
    inferior, _, _ = target()
    regions = read_maps(inferior)
    result = walk_pointers(address, lambda a, n: read(inferior, regions, a, n), depth)
    result.update(schema='ressembly.pointer-chain.v1', pid=inferior.pid, pointer_width=8,
                  byte_order='little', depth_limit=depth)
    return result


def printable(value):
    return json.dumps(value, ensure_ascii=True)


def render_context(snapshot):
    lines = ['Ressembly context | PID {} | {} | {}'.format(snapshot['metadata']['pid'],
             snapshot['metadata']['architecture'], snapshot['status']), 'REGISTERS']
    regs = snapshot['registers']
    for start in range(0, len(REGISTERS), 3):
        lines.append('  '.join('{}={}'.format(name, 'unavailable' if regs[name] is None else
                     '0x{:016x}'.format(regs[name])) for name in REGISTERS[start:start+3]))
    lines.append('ASSEMBLY (forward from PC)')
    for item in snapshot['assembly'].get('instructions', []):
        lines.append('0x{:016x}  {}'.format(item['addr'], printable(item['asm'])))
    lines.append('STACK (8 words from RSP)')
    stack = snapshot['stack']
    for index, word in enumerate(stack.get('words', [])):
        lines.append('0x{:016x}: 0x{:016x}'.format(stack['address'] + index * 8, word))
    lines.append('BREAKPOINTS')
    for item in snapshot['breakpoints']:
        lines.append('#{} {} {} pending={} hits={}'.format(item['number'],
            'enabled' if item['enabled'] else 'disabled', printable(item['location']),
            item['pending'], item['hit_count']))
    for section, error in snapshot['errors'].items():
        lines.append('UNAVAILABLE {}: {}'.format(section, printable(error)))
    return '\n'.join(lines) + '\n'


class Command(gdb.Command):
    def __init__(self, name, function, usage):
        super().__init__(name, gdb.COMMAND_DATA)
        self.function, self.usage = function, usage

    def invoke(self, argument, from_tty):
        self.dont_repeat()
        try:
            args = gdb.string_to_argv(argument)
            result = self.function(args)
            gdb.write(result if isinstance(result, str) else json.dumps(result, indent=2, ensure_ascii=True) + '\n')
        except (ValueError, OSError, gdb.error) as error:
            raise gdb.GdbError('{}; usage: {}'.format(error, self.usage)) from error


def args_count(args, count):
    if len(args) != count:
        raise ValueError('wrong number of arguments')


def context_command(args):
    if args not in ([], ['--json']):
        raise ValueError('expected no argument or --json')
    snapshot = context_snapshot()
    return snapshot if args else render_context(snapshot)


def maps_command(args):
    args_count(args, 0)
    return memory_maps()


def dump_command(args):
    args_count(args, 2)
    return memory_dump(int(args[0], 0), int(args[1], 0))


def search_command(args):
    args_count(args, 3)
    return memory_search(int(args[0], 0), int(args[1], 0), bytes.fromhex(args[2]))


def chain_command(args):
    args_count(args, 2)
    return pointer_chain(int(args[0], 0), int(args[1], 0))


def register():
    Command('rs-context', context_command, 'rs-context [--json]')
    Command('rs-maps', maps_command, 'rs-maps')
    Command('rs-dump', dump_command, 'rs-dump ADDRESS LENGTH (max 4096)')
    Command('rs-search', search_command, 'rs-search ADDRESS LENGTH HEXBYTES (max 65536 bytes)')
    Command('rs-chain', chain_command, 'rs-chain ADDRESS DEPTH (max 32)')
