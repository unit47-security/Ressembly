#!/usr/bin/env python3
"""Independent real-GDB plugin tests; trusted code is not security-confined."""
import ast
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def require(value,message):
    if not value: raise ValueError(message)

def main():
    require(platform.system()=='Linux' and platform.machine()=='x86_64','actual Linux x86-64 required')
    require(len(sys.argv)==2,'usage: validate-plugins-linux.py NEW_DIRECTORY')
    out=Path(sys.argv[1]).resolve(); out.mkdir(parents=True,exist_ok=False)
    source_names=['src/ressembly/plugins.py','src/ressembly/plugin_worker.py','src/ressembly/plugin_gdb.py',
                  'src/ressembly/debug_gdb.py','src/ressembly/debug_core.py','src/ressembly/experiments.py',
                  'scripts/ressembly-plugins.py','scripts/validate-plugins-linux.py','tests/test_plugins.py',
                  'examples/experiments_lab.c','examples/plugins/summary/plugin.json','examples/plugins/summary/plugin.py']
    sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_names}
    def run(name,cmd,expected=0):
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
        (out/(name+'.stdout')).write_text(result.stdout); (out/(name+'.stderr')).write_text(result.stderr)
        (out/(name+'.process.json')).write_text(json.dumps({'argv':cmd,'returncode':result.returncode},indent=2))
        require(result.returncode==expected,name+': '+result.stderr[-2500:]); return result
    run('offline-contract-tests',[sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_plugins.py','-v'])
    for label,cmd in [('kernel',['uname','-a']),('gdb',['gdb','--version']),('libc',['getconf','GNU_LIBC_VERSION']),('compiler',['cc','--version'])]:
        run(label,cmd)
    binary=out/'owned-target'
    run('compile',['cc','-g3','-O0','-Wall','-Wextra','-Werror',str(ROOT/'examples/experiments_lab.c'),'-o',str(binary)])
    plug=out/'owned-plugin'; plug.mkdir(); marker=out/'plugin-executed.txt'
    (plug/'plugin.json').write_text(json.dumps({'id':'ownedprobe','version':'1.0.0','api_version':1}))
    code='from pathlib import Path\nPath('+repr(str(marker))+').write_text("explicitly executed")\ndef analyze(snapshot):\n snapshot["registers"]["rax"]=123456\n return {"api_version":1,"annotations":[{"message":"owned annotation, not observation"}]}\n'
    (plug/'plugin.py').write_text(code)
    oracle=r'''
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,SOURCE)
from ressembly import plugin_gdb,debug_gdb
plugin_gdb.register()
checks=[]
def require(value,label):
    if not value: raise ValueError(label)
    checks.append(label)
def command(text): return gdb.execute(text,to_string=True)
require(json.loads(command('rs-plugin list'))==[],'fresh registry empty')
info=json.loads(command('rs-plugin inspect '+PLUGIN))
require(not Path(MARKER).exists(),'inspection executes nothing')
try: command('rs-plugin load '+PLUGIN+' '+'0'*64)
except gdb.error: checks.append('wrong trust rejected')
else: raise ValueError('wrong trust accepted')
command('rs-plugin load '+PLUGIN+' '+info['sha256'])
require(not Path(MARKER).exists(),'load executes nothing')
require(len(json.loads(command('rs-plugin list')))==1,'explicit load registered')
try: command('rs-plugin load '+PLUGIN+' '+info['sha256'])
except gdb.error: checks.append('duplicate id rejected')
else: raise ValueError('duplicate id accepted')
regs={name:int(gdb.newest_frame().read_register(name)) for name in ('rax','rsp','rip')}
sp=regs['rsp']; memory=bytes(gdb.selected_inferior().read_memory(sp,64))
output=json.loads(command('rs-plugin run ownedprobe'))
require(Path(MARKER).read_text()=='explicitly executed','explicit trusted run executes')
require(output['evidence_status']=='annotations_not_debugger_observations','annotations not promoted')
require(output['provenance']=='trusted_local_plugin_output','provenance distinct')
require(output['snapshot_id'] and len(output['snapshot_sha256'])==64,'snapshot references retained')
require({name:int(gdb.newest_frame().read_register(name)) for name in regs}==regs,'raw GDB registers unchanged')
require(bytes(gdb.selected_inferior().read_memory(sp,64))==memory,'raw GDB stack bytes unchanged')
require(int(gdb.parse_and_eval('experiment_stage'))==1,'target not resumed')
Path(OUTPUT).write_text(json.dumps(output,indent=2))
with (Path(PLUGIN)/'plugin.py').open('a') as stream: stream.write('\n# changed after trust\n')
try: command('rs-plugin run ownedprobe')
except gdb.error: checks.append('changed code rejected on run')
else: raise ValueError('changed plugin accepted')
command('rs-plugin unload ownedprobe')
require(json.loads(command('rs-plugin list'))==[],'unload empties registry')
try: command('rs-plugin run ownedprobe')
except gdb.error: checks.append('unloaded run rejected')
else: raise ValueError('unloaded plugin ran')
Path(CHECKS).write_text(json.dumps(checks,indent=2))
'''
    replacements={'SOURCE':str(ROOT/'src'),'PLUGIN':str(plug),'MARKER':str(marker),'OUTPUT':str(out/'annotations.json'),'CHECKS':str(out/'checks.json')}
    for key,value in replacements.items(): oracle=oracle.replace(key,repr(value))
    ast.parse(oracle)
    script=out/'commands.gdb'
    script.write_text('set pagination off\nset confirm off\nfile '+str(binary)+'\nbreak experiment_checkpoint\nrun < /dev/null\npython\n'+oracle+'\nend\n')
    run('actual-gdb',['gdb','-nx','-q','-batch','-x',str(script)])
    # No registry persists across a fresh debugger, and no target means no stale snapshot.
    script2=out/'fresh.gdb'
    script2.write_text('python\nimport sys,json\nsys.path.insert(0,'+repr(str(ROOT/'src'))+')\nfrom ressembly import plugin_gdb\nplugin_gdb.register()\nif json.loads(gdb.execute("rs-plugin list",to_string=True)) != []: raise ValueError("registry persisted")\nprint("fresh registry empty")\nend\n')
    result=run('fresh-gdb',['gdb','-nx','-q','-batch','-x',str(script2)])
    require('fresh registry empty' in result.stdout,'fresh registry evidence missing')
    checks=json.loads((out/'checks.json').read_text())
    require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in sources.items()),'sources changed during validation')
    report={'status':'PASS','scope':'actual Linux x86-64; trusted plugins are not a security sandbox','gdb_sessions':2,
            'gdb_checks':checks+['fresh debugger registry empty'],'offline_test_count':9,'sources':sources}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))

if __name__=='__main__': main()
