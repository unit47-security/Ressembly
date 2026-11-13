"""Real GDB validation for R3a/b. Usage: python3 scripts/validate-debug-linux.py NEW_DIR."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'actual Linux x86-64 required')
    require(len(sys.argv) == 2, __doc__)
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    binary = output / 'debug_lab'
    subprocess.run(['cc', '-g3', '-O0', '-fno-pie', '-no-pie', '-fno-omit-frame-pointer',
                    '-Wall', '-Wextra', '-Werror', str(ROOT / 'examples/debug_lab.c'), '-o', str(binary)], check=True)
    symbols = {}
    nm = subprocess.run(['nm', '-n', str(binary)], check=True, capture_output=True, text=True).stdout
    (output / 'nm.txt').write_text(nm)
    for line in nm.splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    stripped = output / 'debug_lab.stripped'
    shutil.copy2(binary, stripped)
    subprocess.run(['strip', '--strip-all', str(stripped)], check=True)
    report = dict(scope='actual Linux x86-64 GDB; virtualization declared externally', tests=[])
    for name, command in [('gdb', ['gdb', '--version']), ('compiler', ['cc', '--version']),
                          ('kernel', ['uname', '-a']), ('libc', ['getconf', 'GNU_LIBC_VERSION'])]:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        (output / (name + '.txt')).write_text(result.stdout + result.stderr)
    def run(name, lines, expected=0):
        path = output / name
        path.mkdir()
        script = path / 'commands.gdb'
        script.write_text('\n'.join(lines) + '\n')
        result = subprocess.run(['gdb', '-nx', '-q', '-batch', '-x', str(script)], capture_output=True, text=True, timeout=120)
        (path / 'session.txt').write_text(result.stdout + result.stderr)
        (path / 'process.json').write_text(json.dumps(dict(returncode=result.returncode, expected=expected), indent=2))
        require(result.returncode == expected, name + ': unexpected GDB exit: ' + result.stderr[-1500:])
        return path
    pre = ['set pagination off', 'set confirm off', 'set style enabled off', 'set breakpoint pending on']
    loader = 'source ' + str(ROOT / 'src/ressembly_debug.py')
    for name, executable in [('symbols', binary), ('stripped', stripped)]:
        target_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
        directory = output / name
        python = '''
import json, re
from pathlib import Path
from ressembly import debug_gdb as dg
out = Path(OUTPUT)
symbols = SYMBOLS
checks = []
def require(value, label):
    if not value: raise ValueError(label)
    checks.append(label)
def save(name, value):
    (out / (name + '.json')).write_text(json.dumps(value, indent=2))
def text(name, command):
    value = gdb.execute(command, to_string=True)
    (out / (name + '.txt')).write_text(value)
    return value
def address(name): return symbols[name]
def scalar(name): return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address(name), 8)), 'little')
def oracle(snapshot, tag):
    regs = text(tag+'-registers', 'info registers ' + ' '.join(dg.REGISTERS))
    for register, value in snapshot['registers'].items():
        match = re.search(r'^'+register+r'\\s+0x([0-9a-fA-F]+)', regs, re.M)
        require(match and int(match[1], 16) == value, tag+'-register-'+register)
    disasm = text(tag+'-assembly', 'x/8i $pc')
    addresses = [int(x,16) for x in re.findall(r'(0x[0-9a-fA-F]+)(?:\\s+<[^>]*>)?:', disasm)]
    require(addresses == [i['addr'] for i in snapshot['assembly']['instructions']], tag+'-assembly-addresses')
    for line, instruction in zip(disasm.splitlines(), snapshot['assembly']['instructions']):
        actual = line.split(':',1)[1].strip()
        require(' '.join(actual.split()) == ' '.join(instruction['asm'].split()), tag+'-assembly-mnemonic')
    stack = text(tag+'-stack', 'x/8gx $rsp')
    words = []
    for line in stack.splitlines(): words.extend(int(x,16) for x in re.findall(r'0x[0-9a-fA-F]+', line.split(':',1)[1]))
    require(words == snapshot['stack']['words'], tag+'-stack-words')
    bp = text(tag+'-breakpoints', 'info breakpoints')
    require('debug_stop' in bp or symbols['debug_stop'] in [int(x,16) for x in re.findall(r'0x[0-9a-fA-F]+',bp)], tag+'-breakpoint-position')
    require(any(b['enabled'] and b['number']==1 for b in snapshot['breakpoints']), tag+'-breakpoint-enabled')
    require(any(not b['enabled'] and b['number']==2 for b in snapshot['breakpoints']), tag+'-breakpoint-disabled')
    require(any(b['pending'] for b in snapshot['breakpoints']), tag+'-breakpoint-pending')
    require(snapshot['metadata']['executable_sha256'] == HASH, tag+'-actual-executable-hash')
first = dg.context_snapshot()
save('context-first', first)
require(first['status']=='complete', 'first-complete')
oracle(first, 'first')
text('context-rendered', 'rs-context')
text('context-command-json', 'rs-context --json')
text('maps-command', 'rs-maps')
raw_maps = Path('/proc/%d/maps'%gdb.selected_inferior().pid).read_text()
(out / 'maps.raw').write_text(raw_maps)
maps = dg.memory_maps()
save('maps', maps)
text('gdb-maps', 'info proc mappings')
for line, region in zip(raw_maps.splitlines(),maps['regions']):
    require(line.split()[1] == region['permissions'], 'mapping-permissions')
require(len(raw_maps.splitlines())==len(maps['regions']), 'mapping-count')
base = address('lab_bytes')
dump = dg.memory_dump(base,64)
save('dump-first', dump)
bytes_text = text('dump-oracle','x/64bx '+hex(base))
expected=[]
for line in bytes_text.splitlines(): expected.extend(int(x,16) for x in re.findall(r'0x[0-9a-fA-F]+',line.split(':',1)[1]))
require(dump['hex']==bytes(expected).hex(), 'dump-gdb-byte-oracle')
require(bytes.fromhex(dump['hex']).startswith(b'abcabcabc'), 'owned-bytes-first')
search = dg.memory_search(base,64,b'abc')
save('search',search)
require(search['matches']==[base,base+3,base+6] and search['status']=='complete', 'search-all-matches')
limited = dg.memory_search(base,64,b'abc',2)
require(limited['reason']=='match_limit' and limited['matches']==[base,base+3], 'search-match-budget')
guard=scalar('lab_guard'); page=scalar('lab_page')
partial=dg.memory_search(guard+page-2,8,b'ab')
save('search-partial',partial)
require(partial['scanned_bytes']==2 and partial['matches']==[guard+page-2] and partial['status']=='partial', 'search-unreadable-boundary')
require(dg.memory_search(guard+page,8,b'a')['scanned_bytes']==0, 'search-no-readable-bytes')
chain=dg.pointer_chain(address('lab_chain'),8)
save('chain-cycle',chain)
text('chain-oracle','x/3gx '+hex(address('lab_chain')))
require(chain['termination']=='cycle' and [n['address'] for n in chain['nodes']]==[address('lab_chain')+i*8 for i in range(3)], 'pointer-cycle')
require(dg.pointer_chain(address('lab_chain'),1)['termination']=='depth_limit','pointer-depth-budget')
require(dg.pointer_chain(0,8)['termination']=='null','pointer-null')
require(dg.pointer_chain(1,8)['termination']=='unreadable','pointer-unreadable')
for command in ['rs-dump 0 0','rs-dump 0 4097','rs-search 0 65537 61','rs-search 0 1 zz','rs-chain 0 33','rs-context extra','rs-dump (exit(9)) 1','rs-dump '+hex(guard+page)+' 1']:
    try: gdb.execute(command,to_string=True)
    except gdb.error: checks.append('reject:'+command)
    else: raise ValueError('accepted bad command '+command)
text('dump-command','rs-dump '+hex(base)+' 16')
text('search-command','rs-search '+hex(base)+' 64 616263')
text('chain-command','rs-chain '+hex(address('lab_chain'))+' 8')
require(dg.context_snapshot()['registers']==first['registers'],'read-only-registers')
require(int(gdb.parse_and_eval('*(unsigned int*)'+hex(address('lab_stage'))))==1,'no-target-execution')
gdb.execute('continue')
second=dg.context_snapshot()
save('context-second',second)
oracle(second,'second')
require(second['metadata']['run_id']==first['metadata']['run_id'],'same-run-identity')
require(second['snapshot_id']!=first['snapshot_id'],'new-snapshot-identity')
require(dg.memory_dump(base,1)['hex']=='7a','fresh-memory-after-continue')
require(dg.pointer_chain(address('lab_chain'),8)['termination']=='null','chain-updated-after-continue')
original_sp=int(gdb.parse_and_eval('$rsp'))
gdb.execute('set $rsp = 1')
partial_context=dg.context_snapshot()
save('context-unavailable-stack',partial_context)
require(partial_context['status']=='partial' and 'stack' in partial_context['errors'],'unavailable-stack-explicit')
gdb.execute('set $rsp = '+hex(original_sp))
gdb.execute('continue')
try: dg.context_snapshot()
except ValueError: checks.append('exited-target-rejected')
else: raise ValueError('stale snapshot after exit')
save('checks', checks)
'''.replace('OUTPUT', repr(str(directory))).replace('SYMBOLS', repr(symbols)).replace('HASH', repr(target_hash))
        lines = pre + ['file ' + str(executable), loader, 'break *' + hex(symbols['debug_stop']),
                       'break *' + hex(symbols['main']), 'disable 2', 'break no_such_ressembly_symbol',
                       'run', 'python'] + python.strip().splitlines() + ['end']
        run(name, lines)
        checks = json.loads((directory / 'checks.json').read_text())
        report['tests'].append(dict(name=name, status='PASS', assertions=len(checks)))
    path = run('no-inferior', pre + [loader, 'rs-context'], 1)
    require('requires a live local Linux inferior' in (path/'session.txt').read_text(), 'wrong no-target diagnostic')
    report['tests'].append(dict(name='no-inferior',status='PASS'))
    report['status']='PASS'
    report['target_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
    sources=['src/ressembly_debug.py','src/ressembly/debug_core.py','src/ressembly/debug_gdb.py',
             'examples/debug_lab.c','scripts/validate-debug-linux.py']
    (output/'tested-source-sha256.txt').write_text(''.join(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()+'  '+p+'\n' for p in sources))
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    sys.exit(main())
