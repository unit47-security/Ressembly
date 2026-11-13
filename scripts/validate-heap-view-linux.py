#!/usr/bin/env python3
"""Real Linux/GDB checks; saves raw sessions, source hashes and independent field oracles."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OWNED = ['src/ressembly/heap_view.py', 'src/ressembly/heap_view_gdb.py',
         'src/ressembly_heap_view.py', 'examples/heap_view_lab.c',
         'scripts/validate-heap-view-linux.py', 'tests/test_heap_view.py']


def run(output):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('real Linux x86-64 required')
    output.mkdir(parents=True, exist_ok=False)
    binary = output / 'heap_view_lab'
    build = subprocess.run(['gcc', '-g3', '-O0', '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror',
                            str(ROOT / 'examples/heap_view_lab.c'), '-o', str(binary)], capture_output=True, text=True)
    (output / 'build.log').write_text(build.stdout + build.stderr)
    build.check_returncode()
    sources = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in OWNED}
    (output / 'tested-source-sha256.json').write_text(json.dumps(sources, indent=2))
    checks = []

    def session(name, commands, expected=0):
        directory = output / name
        directory.mkdir()
        script = directory / 'commands.gdb'
        script.write_text('set pagination off\nset confirm off\nset debuginfod enabled off\n' + commands + '\n')
        process = subprocess.run(['gdb', '-nx', '-batch', '-x', str(script)], capture_output=True, text=True, timeout=60)
        (directory / 'gdb.log').write_text(process.stdout + process.stderr)
        (directory / 'process.json').write_text(json.dumps(dict(returncode=process.returncode), indent=2))
        okay = process.returncode == expected
        checks.append(dict(name=name, passed=okay, returncode=process.returncode))
        if not okay:
            raise RuntimeError(name + ' failed; see ' + str(directory / 'gdb.log'))
        return process.stdout + process.stderr

    load = 'source ' + str(ROOT / 'src/ressembly_heap_view.py') + '\n'
    setup = 'file ' + str(binary) + '\nbreak heap_view_checkpoint\nrun\n' + load
    normal = setup + '''python
import json
from ressembly.heap_view_gdb import HeapView, render
def must(condition, message):
    if not condition: raise RuntimeError(message)
def number(expr): return int(gdb.parse_and_eval(expr))
def record(name, value):
    with open(OUT + '/' + name + '.json', 'w') as f: json.dump(value, f, indent=2)
first = HeapView()
state = first.snapshot()
addresses = [number('small_addresses[%d]' % i) for i in range(9)]
large = number('large_address')
raw = bytes(gdb.selected_inferior().read_memory(addresses[0] - 16, 16))
chunk = first.chunk(addresses[0])
must(chunk['chunk']['size_word'] == int.from_bytes(raw[8:16], 'little'), 'raw chunk size differs')
must(chunk['chunk']['chunk_size'] == 48, 'known malloc(32) chunk size')
must(chunk['chunk']['allocation_state'] == 'unknown_from_header', 'invented lifetime')
must(state['arena']['top'] == hex(number('main_arena.top')), 'raw top differs')
must(state['arena']['system_mem'] == number('main_arena.system_mem'), 'raw system_mem differs')
must(not any(row['nodes'] for row in state['tcache']), 'tcache expected empty before free')
record('allocated', dict(snapshot=state, chunk=chunk, raw_header=raw.hex(), addresses=addresses, large=large))
print(render(state))
end
p/x main_arena.top
p main_arena.system_mem
x/2gx small_addresses[0]-16
continue
python
state = HeapView().snapshot()
must(state['tcache'][1]['nodes'] == list(reversed(addresses[:7])), 'tcache LIFO chain')
must(state['tcache'][1]['declared_count'] == 7 and state['tcache'][1]['count_matches_traversal'], 'tcache count')
must(state['fastbins'][1]['nodes'] == [addresses[8]-16, addresses[7]-16], 'fastbin LIFO chain')
must(state['tcache'][1]['nodes'][0] == number('tcache->entries[1]'), 'raw tcache head differs')
must(state['fastbins'][1]['nodes'][0] == number('main_arena.fastbinsY[1]'), 'raw fastbin head differs')
limited = HeapView().snapshot(1)
must(limited['tcache'][1]['end'] == 'limit' and len(limited['tcache'][1]['nodes']) == 1, 'bounded tcache traversal')
record('freed_small', state)
record('limit', limited)
print(render(state))
end
p tcache->counts[1]
p/x tcache->entries[1]
p/x main_arena.fastbinsY[1]
x/2gx small_addresses[6]
continue
python
state = HeapView().snapshot()
must(large - 16 in state['bins'][0]['nodes'], 'large freed block not in unsorted')
must(state['bins'][0]['nodes'][0] == number('main_arena.bins[0]'), 'raw unsorted differs')
record('unsorted', state)
print(render(state))
end
p/x main_arena.bins[0]
continue
python
state = HeapView().snapshot()
matches = [row for row in state['bins'] if large - 16 in row['nodes']]
must(len(matches) == 1 and matches[0]['category'] == 'large', 'large block not sorted into largebin')
must(not state['fastbins'][1]['nodes'], 'fastbins not consolidated')
record('sorted', state)
print(render(state))
end
continue
python
must(gdb.selected_inferior().pid == 0, 'inferior failed to exit')
end
'''.replace('OUT', repr(str(output / 'normal')))
    session('normal', normal)
    # Each corrupt-link test is isolated and does not resume its intentionally modified target.
    for name, mutate, expected_end in [
        ('cycle', 'set *(unsigned long *)small_addresses[6] = small_addresses[6] ^ (small_addresses[6] >> 12)', 'cycle'),
        ('unreadable', 'set *(unsigned long *)small_addresses[6] = 0x1000 ^ (small_addresses[6] >> 12)', 'unreadable'),
        ('unaligned', 'set *(unsigned long *)small_addresses[6] = 0x1001 ^ (small_addresses[6] >> 12)', 'unaligned_or_invalid')]:
        commands = setup + 'continue\n' + mutate + '\npython\nfrom ressembly.heap_view_gdb import HeapView\ns = HeapView().snapshot()\n'
        commands += "if s['tcache'][1]['end'] != %r: raise RuntimeError('wrong traversal termination')\nprint(s['tcache'][1])\nend\n" % expected_end
        session(name, commands)
    bad_version = setup + "set {char}&__libc_version = 57\nrs-heap-view\n"
    text = session('unsupported_version', bad_version, 1)
    if 'supported profile' not in text: raise RuntimeError('version rejection missing')
    text = session('missing_debug_types', 'set debug-file-directory /nonexistent\n' + setup + 'rs-heap-view\n', 1)
    if 'debug symbols' not in text: raise RuntimeError('debug type rejection missing')
    text = session('no_target', load + 'rs-heap-view\n', 1)
    if 'live stopped' not in text: raise RuntimeError('no target rejection missing')
    for name, command, error in [('limit_zero', 'rs-heap-view arena 0', 'node limit'),
                                  ('limit_large', 'rs-heap-view arena 257', 'node limit'),
                                  ('invalid_chunk', 'rs-heap-view chunk 1', 'aligned'),
                                  ('unreadable_chunk', 'rs-heap-view chunk 0x1000', 'Cannot access'),
                                  ('expression_rejected', 'rs-heap-view chunk malloc(16)', 'invalid literal')]:
        text = session(name, setup + command + '\n', 1)
        if error not in text: raise RuntimeError(name + ' wrong error')
    commands = setup + '''python
from ressembly.heap_view_gdb import HeapView
before = (int(gdb.parse_and_eval('$pc')), int(gdb.parse_and_eval('$sp')), bytes(gdb.selected_inferior().read_memory(gdb.parse_and_eval('&main_arena'), gdb.lookup_type('struct malloc_state').sizeof)), len(gdb.breakpoints()))
end
rs-heap-view
rs-heap-view arena 1 --json
python
after = (int(gdb.parse_and_eval('$pc')), int(gdb.parse_and_eval('$sp')), bytes(gdb.selected_inferior().read_memory(gdb.parse_and_eval('&main_arena'), gdb.lookup_type('struct malloc_state').sizeof)), len(gdb.breakpoints()))
if before != after: raise RuntimeError('view mutated inferior or breakpoints')
end
'''
    session('read_only', commands)
    result = dict(status='PASS', session_count=len(checks), checks=checks,
                  normal_assertions=['chunk raw header', 'arena top/system_mem', 'empty tcache', 'tcache LIFO/count',
                                     'fastbin LIFO', 'bounded traversal', 'unsorted bin', 'sorted largebin', 'normal exit'],
                  environment=dict(platform=platform.platform(), machine=platform.machine(),
                    gdb=subprocess.check_output(['gdb', '--version'], text=True).splitlines()[0],
                    glibc=os.confstr('CS_GNU_LIBC_VERSION')),
                  binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                  limits=['single-thread local glibc 2.36', 'main_arena only', 'structural snapshots do not infer lifetime',
                          'unsupported version test mutates the version symbol in an isolated owned target, not a second distro'])
    (output / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('usage: validate-heap-view-linux.py NEW_OUTPUT_DIRECTORY')
    run(Path(sys.argv[1]).resolve())
