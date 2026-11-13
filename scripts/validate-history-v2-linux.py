"""Actual Linux/GDB tests for opt-in allocator v2. Pass a fresh output directory."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def require(value,message):
    if not value: raise ValueError(message)


def main():
    require(platform.system()=='Linux' and platform.machine()=='x86_64','Linux x86-64 required')
    require(len(sys.argv)==2,__doc__)
    out=Path(sys.argv[1]).resolve(); out.mkdir(parents=True,exist_ok=False)
    binary=out/'history_lab'
    subprocess.run(['cc','-g3','-O0','-fno-omit-frame-pointer','-Wall','-Wextra','-Werror',str(ROOT/'examples/history_v2_lab.c'),'-o',str(binary)],check=True)
    report={'checks':[],'scope':'Linux x86-64 loaded profile; host libc and virtualization do not identify target libc'}
    for name,command in [('gdb',['gdb','--version']),('glibc',['getconf','GNU_LIBC_VERSION']),('kernel',['uname','-a']),('cc',['cc','--version'])]:
        result=subprocess.run(command,capture_output=True,text=True,check=True); (out/(name+'.txt')).write_text(result.stdout+result.stderr)
    source=['src/ressembly/history_v2.py','src/ressembly/history_v2_gdb.py','src/ressembly_history.py','src/ressembly/heap_gdb.py','src/ressembly/lifetime.py','examples/history_v2_lab.c','scripts/validate-history-v2-linux.py']
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source}
    def record(name,fn):
        try:
            fn(); report['checks'].append({'name':name,'status':'PASS'}); print('PASS',name,flush=True)
        except Exception as error:
            report['checks'].append({'name':name,'status':'FAIL','error':str(error)}); print('FAIL',name,str(error),flush=True)
        (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(name,commands,mode=None,expected=0,limit=1000,loader=True):
        directory=out/name; directory.mkdir()
        path=directory/'history.json'
        lines=['set pagination off','set confirm off','file '+str(binary)]
        if mode: lines+=['set args '+mode]
        lines+=['break hist_ready','run']
        if loader: lines+=['source '+str(ROOT/'src/ressembly_history.py'),'rshist-start '+str(path)+' '+str(limit)]
        lines+=commands
        script=directory/'commands.gdb'; script.write_text('\n'.join(lines)+'\n')
        result=subprocess.run(['gdb','-nx','-q','-batch','-x',str(script)],capture_output=True,text=True,timeout=180)
        transcript=result.stdout+result.stderr
        (directory/'session.txt').write_text(transcript)
        (directory/'process.json').write_text(json.dumps({'returncode':result.returncode,'expected':expected}))
        require(result.returncode==expected,'unexpected GDB exit: '+transcript[-2000:])
        if expected==0: require('Traceback' not in transcript and 'Python Exception' not in transcript,'unexpected Python error: '+transcript[-1000:])
        return json.loads(path.read_text()) if path.exists() else None,transcript,directory
    normal='''
python
import json
from pathlib import Path
from ressembly import history_v2_gdb as h
checks=[]
def check(ok,label):
    if not ok: raise ValueError(label)
    checks.append(label)
def cmd(text): return gdb.execute(text,to_string=True)
def p(): return int(gdb.parse_and_eval('hist_p'))
def oid(): return h._session.model.active[p()]
for point in ('hist_initialized','hist_resized','hist_moved','hist_failed','hist_done'): cmd('break '+point)
cmd('rshist-continue')
check(bytes(gdb.selected_inferior().read_memory(p(),32))==b'\\0'*32,'calloc zero bytes direct GDB')
first=oid(); original=p(); other=int(gdb.parse_and_eval('hist_other')); other_id=h._session.model.active[other]
for target,offset in ((first,0),(first,8),(other_id,0),(other_id,8)): cmd('rshist-watch %s %d 1'%(target,offset))
check(all(w['state']=='pending' for w in h._session.model.observing.values()),'four pending windows')
cmd('rshist-continue')
check(gdb.newest_frame().name()=='hist_resized' and p()==original,'inplace realloc direct oracle')
second=oid(); check(first!=second,'inplace generation replaced')
check(len(h._session.model.observing)==2,'only other object remains watched')
check(bytes(gdb.selected_inferior().read_memory(p(),9))==b'A'+b'\\0'*7+b'B','realloc preserved observed prefix')
cmd('rshist-watch '+second+' 0 1')
cmd('rshist-continue')
check(gdb.newest_frame().name()=='hist_moved' and p()!=original,'moved realloc direct oracle')
third=oid(); check(third!=second,'moved identity')
cmd('rshist-watch '+third+' 0 1')
cmd('rshist-continue')
check(gdb.newest_frame().name()=='hist_failed' and oid()==third,'failed realloc keeps identity')
check(h._session.model.objects[third]['state']=='live','failed realloc restores live')
check(not any(w['object_id']==third for w in h._session.model.observing.values()),'failed realloc needs explicit reselection')
cmd('rshist-continue'); check(gdb.newest_frame().name()=='hist_done','nested realloc paths completed')
cmd('rshist-continue')
Path(CHECKS).write_text(json.dumps(checks,indent=2))
end
'''.replace('CHECKS',repr(str(out/'normal'/'checks.json')))
    def normal_case():
        data,_,directory=run('normal',normal.strip().splitlines())
        require(data['schema']=='ressembly.object-history.v2','schema')
        require(data['metadata']['exit_code']==0,'target failed')
        require(all(o['state'] in ('replaced','freed') for o in data['objects'].values()),'live or unknown final objects')
        changes=[e for e in data['events'] if e['kind']=='value_change']
        require(len(changes)==3,'expected only A,B,C changes; same value A absent')
        require(len(set(e['window_id'] for e in changes))==3,'window attribution')
        require(all('code' in e and e['pc_semantics'].startswith('stop_pc_after') for e in changes),'code refs')
        require(any(e['kind']=='allocation_failed' and e.get('size_t_overflow') for e in data['events']),'calloc overflow absent')
        require(sum(e['kind']=='realloc_zero_free' for e in data['events'])==1,'zero policy')
        require(all(w['state']=='ended' for w in data['coverage']['windows']),'window not ended')
        require(not data['coverage']['nested_allocator_calls_observed'],'overclaimed nested coverage')
    record('transactions-four-regions',normal_case)
    watch='python from ressembly import history_v2_gdb as h; gdb.execute("rshist-watch "+h._session.model.active[int(gdb.parse_and_eval("hist_p"))]+" 0 1")'
    def negative(name,commands,fragment,mode=None,limit=1000):
        data,text,_=run(name,commands,mode,expected=1,limit=limit)
        require(fragment in text, 'expected refusal missing: '+text[-1500:])
        return data
    record('incomplete-realloc',lambda: require(any(o['state']=='unknown_after_incomplete_realloc' for o in negative(
        'incomplete-realloc',['break __libc_realloc','rshist-continue','return (void *)0','rshist-continue'],
        'allocator frame left before observed return')['objects'].values()),'incomplete realloc not unknown'))
    record('overlap',lambda: negative('overlap',['break hist_initialized','rshist-continue',watch,watch],'overlapping observation'))
    def fifth():
        cmd='python from ressembly import history_v2_gdb as h; oid=h._session.model.active[int(gdb.parse_and_eval("hist_p"))]; [gdb.execute("rshist-watch %s %d 1"%(oid,i)) for i in range(5)]'
        data=negative('fifth-region',['break hist_initialized','rshist-continue',cmd],'selected region limit')
        require(len(data['coverage']['windows'])==4,'fifth created a window')
    record('fifth-region',fifth)
    record('software-refusal',lambda: negative('software-refusal',['break hist_initialized','rshist-continue','set can-use-hw-watchpoints 0',watch],'software fallback refused'))
    def hardware():
        data=negative('hardware-exhausted',['break hist_initialized','rshist-continue']+['watch -location hist_slots[%d]'%i for i in range(4)]+[watch,'rshist-continue'],'Could not insert')
        require(all('active_sequence' not in w for w in data['coverage']['windows']),'false hardware activation')
        require(data['metadata']['acquisition_status']=='error','hardware error lost')
    record('hardware-exhausted',hardware)
    record('unreadable',lambda: negative('unreadable',['break hist_initialized','rshist-continue',watch],'Cannot access memory',mode='unreadable'))
    def signal():
        data,_,_=run('signal',['handle SIGUSR1 stop print nopass','rshist-continue','rshist-stop'],mode='signal')
        require(data['metadata']['acquisition_status']=='interrupted' and data['metadata']['stop_signal']=='SIGUSR1','signal state')
    record('signal',signal)
    def budget():
        data,_,_=run('event-budget',['rshist-continue'],limit=1)
        require(data['metadata']['acquisition_status']=='event_limit_reached','event budget')
    record('event-budget',budget)
    record('second-run',lambda: negative('second-run',['rshist-continue','run','rshist-continue'],'capture closed'))
    def conflict_new_first():
        data=negative('v2-then-v1',['source '+str(ROOT/'src/ressembly_heap.py'),'rsheap-start '+str(out/'v1-rejected.json')], 'extended history has already started')
        require(not (out/'v1-rejected.json').exists(),'v1 capture created')
    record('v2-then-v1',conflict_new_first)
    def conflict_old_first():
        _,text,_=run('v1-then-v2',['source '+str(ROOT/'src/ressembly_heap.py'),'rsheap-start '+str(out/'v1-history.json'),
                      'source '+str(ROOT/'src/ressembly_history.py'),'rshist-start '+str(out/'v2-rejected.json')],loader=False,expected=1)
        require('v1 collector has already started' in text and not (out/'v2-rejected.json').exists(),'v2 conflict')
    record('v1-then-v2',conflict_old_first)
    def oracle():
        commands=['break hist_initialized','break hist_resized','break hist_moved','break hist_failed','continue']
        commands+=['python print("ORACLE_ZERO",bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval("hist_p")),32)).hex())',
                   'continue','python print("ORACLE_INPLACE",int(gdb.parse_and_eval("hist_p"))==int(gdb.parse_and_eval("hist_old")))',
                   'continue','python print("ORACLE_MOVED",int(gdb.parse_and_eval("hist_p"))!=int(gdb.parse_and_eval("hist_old")))',
                   'continue','python print("ORACLE_FAILED_PRESERVED",int(gdb.parse_and_eval("hist_p"))==int(gdb.parse_and_eval("hist_old")))','continue']
        _,text,_=run('primitive-oracle',commands,loader=False)
        require('ORACLE_ZERO '+('00'*32) in text and all(x+' True' in text for x in ('ORACLE_INPLACE','ORACLE_MOVED','ORACLE_FAILED_PRESERVED')),'primitive oracle mismatch')
    record('independent-primitive-oracle',oracle)
    def failed_constructor():
        commands = ['source '+str(ROOT/'src/ressembly_history.py'),'python',
            'from ressembly import history_v2_gdb as h',
            'from pathlib import Path',
            'before = len(gdb.breakpoints() or ())',
            'save_original = h.Session.save',
            'save_count = [0]',
            'def fail_second_save(self):',
            '    save_count[0] += 1',
            '    if save_count[0] == 2: raise OSError("injected initial save failure")',
            '    return save_original(self)',
            'h.Session.save = fail_second_save',
            'try:',
            '    gdb.execute("rshist-start '+str(out/'constructor-failed.json')+'")',
            'except gdb.error as error:',
            '    if "injected initial save failure" not in str(error): raise',
            'else: raise ValueError("save failure was ignored")',
            'finally: h.Session.save = save_original',
            'if h._session is not None or len(gdb.breakpoints() or ()) != before: raise ValueError("constructor leaked session or hooks")',
            'if Path('+repr(str(out/'constructor-failed.json'))+').exists(): raise ValueError("constructor left a misleading capture")',
            'end']
        run('constructor-save-failure',commands,loader=False)
    record('constructor-save-failure',failed_constructor)
    report['host_glibc']=os.confstr('CS_GNU_LIBC_VERSION')
    report['loaded_profile_versions']=sorted({json.loads(p.read_text())['metadata'].get('glibc_version') for p in out.glob('*/history.json')})
    report['sources']=hashes
    report['sources_unchanged']=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in hashes.items())
    report['status']='PASS' if report['sources_unchanged'] and all(c['status']=='PASS' for c in report['checks']) else 'FAIL'
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__': sys.exit(main())
