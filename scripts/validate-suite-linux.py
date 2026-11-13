#!/usr/bin/env python3
"""Integrated R2+R3 lab, with actual GDB and retained process transcripts."""
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ressembly import experiments as ex


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'Linux x86-64 required')
    require(len(sys.argv) == 2, 'usage: validate-suite-linux.py NEW_DIRECTORY')
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=False)
    files = ['src/ressembly_suite.py', 'src/ressembly/suite_gdb.py', 'src/ressembly/experiments.py',
             'src/ressembly/experiment_gdb.py', 'src/ressembly/debug_gdb.py', 'src/ressembly/debug_core.py',
             'src/ressembly/heap_view.py', 'src/ressembly/heap_view_gdb.py', 'src/ressembly/heap_gdb.py',
             'src/ressembly/lifetime.py', 'src/ressembly/labtools.py', 'examples/heap_lab.c',
             'scripts/validate-suite-linux.py']
    report = {'sources': {name: ex.digest((ROOT/name).read_bytes()) for name in files}, 'sessions': []}
    binary = out / 'heap_lab'
    subprocess.run(['cc','-g3','-O0','-Wall','-Wextra','-Werror',str(ROOT/'examples/heap_lab.c'),'-o',str(binary)], check=True)
    for mode in ('suite-first', 'modules-first'):
        directory = out/mode; directory.mkdir()
        history, dossier = directory/'history.json', directory/'experiment.json'
        ex.create(dossier, binary, 'Integrated owned lab')
        code = '''
import gdb, json
from pathlib import Path
from ressembly import heap_gdb as hg, debug_gdb as dg, heap_view_gdb as hv
checks=[]
def require(value,label):
    if not value: raise ValueError(label)
    checks.append(label)
def command(text): return gdb.execute(text,to_string=True)
require('rs-context' in command('rs-help'), 'suite help')
require(json.loads(command('rs-lab pattern 8 4'))['hex']=='6161616162616161','pattern wrapper')
require(json.loads(command('rs-lab offset 62616161 64 4'))['offsets']==[4],'offset wrapper')
require(json.loads(command('rs-lab elf '+BINARY))['architecture']=='amd64','ELF wrapper')
for bad in ('rs-lab pattern 99999999 4','rs-lab offset zz 64 4','rs-lab elf /no-such-file','rs-lab unknown'):
    try: command(bad)
    except gdb.error: checks.append('reject:'+bad)
    else: raise ValueError('bad lab command accepted')
command('rsheap-start '+HISTORY)
command('break lab_initialized')
command('break lab_reused')
command('rsheap-continue')
require(gdb.newest_frame().name()=='lab_initialized','first external stop')
active=hg._session
p=int(gdb.parse_and_eval('lab_p'))
oid=active.model.active[p]
regs=dg.context_snapshot()['registers']
events=len(active.model.events)
command('source '+LOADER)
require(hg._session is active and len(active.model.events)==events,'reload preserves active session')
require(json.loads(command('rs-context --json'))['registers']==regs,'context with collector')
require(json.loads(command('rs-dump %d 4'%p))['hex']=='00000000','dump with collector')
require(json.loads(command('rs-search %d 4 00'%p))['matches']==[p,p+1,p+2,p+3],'search with collector')
require(json.loads(command('rs-chain 0 4'))['termination']=='null','chain with collector')
structure=json.loads(command('rs-heap-view chunk %d --json'%p))
require(structure['chunk']['chunk_size']>=32,'structural view with collector')
command('rs-experiment-snapshot '+DOSSIER+' first %d 4'%p)
require(dg.context_snapshot()['registers']==regs and len(active.model.events)==events,'inspection no target execution or allocator events')
command('rsheap-watch '+oid+' 0 1')
command('rsheap-continue')
require(gdb.newest_frame().name()=='lab_reused','reused external stop')
q=int(gdb.parse_and_eval('lab_q'))
require(q==p and active.model.active[q]!=oid,'reused address distinct identity')
require(json.loads(command('rs-dump %d 4'%q))['hex']=='43434343','fresh reused bytes')
command('rs-experiment-snapshot '+DOSSIER+' reused %d 4'%q)
command('rs-heap-view arena 8')
command('rsheap-continue')
require(active.closed,'collector closed on exit')
Path(CHECKS).write_text(json.dumps(checks,indent=2))
'''
        for key, value in {'BINARY':str(binary),'HISTORY':str(history),'DOSSIER':str(dossier),
                           'LOADER':str(ROOT/'src/ressembly_suite.py'),'CHECKS':str(directory/'checks.json')}.items():
            code=code.replace(key, repr(value))
        initial=['set pagination off','set confirm off','file '+str(binary)]
        if mode=='modules-first':
            initial += ['source '+str(ROOT/'src/ressembly_debug.py'), 'source '+str(ROOT/'src/ressembly_heap.py')]
        initial += ['source '+str(ROOT/'src/ressembly_suite.py'),'break lab_ready','run','python']
        script=directory/'commands.gdb'; script.write_text('\n'.join(initial)+code+'\nend\n')
        result=subprocess.run(['gdb','-nx','-q','-batch','-x',str(script)],capture_output=True,text=True,timeout=180)
        (directory/'session.txt').write_text(result.stdout+result.stderr)
        (directory/'process.json').write_text(json.dumps({'returncode':result.returncode}))
        require(result.returncode==0, result.stderr[-2500:])
        checks=json.loads((directory/'checks.json').read_text())
        capture=json.loads(history.read_text())
        require(capture['metadata']['exit_code']==0,'target failed')
        allocations=[event for event in capture['events'] if event['kind']=='allocation']
        require(len(allocations)==2 and allocations[0]['object_id']!=allocations[1]['object_id'],'bad history generations')
        require(all(obj['state']=='freed' for obj in capture['objects'].values()),'free not completed')
        # Retain collector as a supplied evidence snapshot, explicitly not an authenticated import.
        identity=ex.add_snapshot(dossier,capture,capture['metadata']['target_sha256'],capture['metadata']['run_id'],
                                 'allocator history imported')
        ex.add_note(dossier,'Allocator events and selected value-change events have separate coverage.',identity)
        exported=directory/'export.json'; ex.export(dossier,exported)
        require(ex.load(exported)==ex.load(dossier),'export mismatch')
        report['sessions'].append({'name':mode,'status':'PASS','gdb_checks':len(checks),
                                   'additional_checks':['target exit','generation separation','completed frees','dossier export']})
    # A historical marker adapter must not be silently combined with suite state.
    script=out/'marker-conflict.gdb'
    script.write_text('source '+str(ROOT/'src/ressembly_gdb.py')+'\nsource '+str(ROOT/'src/ressembly_suite.py')+'\n')
    result=subprocess.run(['gdb','-nx','-q','-batch','-x',str(script)],capture_output=True,text=True,timeout=30)
    (out/'marker-conflict.txt').write_text(result.stdout+result.stderr)
    require('historical marker adapter is loaded' in result.stderr, 'marker conflict not explicit')
    # GDB source Python exceptions can print diagnostics while returning zero; inspect actual diagnostic.
    report['marker_conflict']={'returncode':result.returncode,'explicit_rejection':True}
    report['sources_unchanged']=all(ex.digest((ROOT/name).read_bytes())==value for name,value in report['sources'].items())
    require(report['sources_unchanged'],'sources changed during run')
    report['status']='PASS'
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
