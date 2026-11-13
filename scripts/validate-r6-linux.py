#!/usr/bin/env python3
"""Real Linux x86-64 R6 corpus with independent raw GDB oracle. No downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
C_SOURCE=r'''
#include <stdlib.h>
#include <stdint.h>
uintptr_t small[5], small_guards[5], big[3], guards[4], selected, selected_miss;
volatile int stage;
__attribute__((noinline)) void checkpoint(void){__asm__ volatile("" ::: "memory");}
int main(void){
 for(int i=0;i<5;i++){small[i]=(uintptr_t)malloc(32);small_guards[i]=(uintptr_t)malloc(32);if(!small[i]||!small_guards[i])return 1;}
 const size_t sizes[3]={0x600,0x500,0x580};
 for(int i=0;i<3;i++){big[i]=(uintptr_t)malloc(sizes[i]);guards[i]=(uintptr_t)malloc(32);if(!big[i]||!guards[i])return 2;}
 guards[3]=(uintptr_t)malloc(32);if(!guards[3])return 3;
 stage=1;checkpoint();
 for(int i=0;i<5;i++)free((void*)small[i]);
 stage=2;checkpoint();
 for(int i=0;i<3;i++)free((void*)big[i]);
 stage=3;checkpoint();
 selected=(uintptr_t)malloc(0x580);if(!selected)return 4;
 stage=4;checkpoint();selected_miss=(uintptr_t)malloc(0x550);if(!selected_miss)return 5;
 stage=5;checkpoint();return 0;
}
'''
RAW=r'''
import json
from pathlib import Path
def number(s):return int(gdb.parse_and_eval(s))
def word(a):return int.from_bytes(bytes(gdb.selected_inferior().read_memory(a,8)),'little')
def chain(head,user):
 nodes=[]
 while head:
  if head in nodes or len(nodes)>=32:raise ValueError('invalid independent chain')
  nodes.append(head);position=head if user else head+16
  head=word(position)^(position>>12)
 return nodes
def bin_chain(index):
 expression='main_arena.bins[%d]'%((index-1)*2)
 head=number(expression);sentinel=number('&'+expression)-16;nodes=[]
 while head!=sentinel:
  if not head or head in nodes or len(nodes)>=32:raise ValueError('invalid independent unsorted chain')
  nodes.append(head);head=word(head+16)
 return nodes
def raw():
 version=gdb.parse_and_eval('__libc_version').string()
 expected=76 if version=='2.43' else 64
 cache=gdb.parse_and_eval('tcache').dereference()
 field='num_slots' if version=='2.43' else 'counts'
 if cache['entries'].type.range()!=(0,expected-1):raise ValueError('unexpected raw tcache layout')
 state='active'
 if version=='2.43':
  if number('tcache')==number('&__tcache_dummy.inactive'):state='inactive'
  elif number('tcache')==number('&__tcache_dummy.disabled'):state='disabled'
 entries=[{'index':i,'raw_value':int(cache[field][i]),'nodes':chain(int(cache['entries'][i]),True)} for i in range(expected)] if state=='active' else []
 return {'version':version,'state':state,'field':field,'capacity':number('mp_.tcache_count'),'entries':entries,
  'unsorted':bin_chain(1),'smallbin3':bin_chain(3),'fastbin':chain(number('main_arena.fastbinsY[1]'),False) if version=='2.36' else [],'small':[number('small[%d]'%i) for i in range(5)],
  'big':[number('big[%d]'%i) for i in range(3)],'selected':number('selected'),'selected_miss':number('selected_miss'),'pc':number('$pc'),'sp':number('$sp'),
  'sizes':{str(n):word(n-8)&~7 for row in entries for n in row['nodes']}}
'''

def require(value,message):
 if not value:raise ValueError(message)
def block(code):return ['python']+code.strip().splitlines()+['end']

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('output',type=Path)
 parser.add_argument('--profile',choices=('2.36','2.43'))
 parser.add_argument('--cc',default='cc')
 parser.add_argument('--debug-directory')
 parser.add_argument('--skip-collectors',action='store_true')
 args=parser.parse_args()
 require(args.cc=='cc' or args.skip_collectors,'custom --cc requires --skip-collectors; use PATH compiler wrappers for complete mixed-userland corpus')
 require(platform.system()=='Linux' and platform.machine()=='x86_64','actual Linux x86-64 required')
 host_libc=os.confstr('CS_GNU_LIBC_VERSION');version=args.profile or host_libc.split()[-1]
 require(version in ('2.36','2.43'),'unsupported test profile')
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 report={'skip_collectors':args.skip_collectors,'compiler_command':args.cc,'debug_directory':args.debug_directory,'schema':'ressembly.r6-validation.v1','host_libc':host_libc,'target_profile':version,'checks':[],
  'scope':'Linux x86-64; distribution and virtualization declared externally; optional extracted old userland is not a Debian OS test',
  'oracle':'separate GDB session without Ressembly, direct debug fields and raw memory'}
 paths=sorted(set((ROOT/'src').rglob('*.py'))|{Path(__file__).resolve(),ROOT/'scripts/validate-heap-linux.py',ROOT/'scripts/validate-history-v2-linux.py',ROOT/'examples/heap_lab.c',ROOT/'examples/history_v2_lab.c'})
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 source=out/'r6_owned.c';source.write_text(C_SOURCE);binary=out/'r6_owned'
 build=subprocess.run([args.cc,'-g3','-O0','-fno-omit-frame-pointer','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
 (out/'build.log').write_text(build.stdout+build.stderr);build.check_returncode()
 for label,command in [('gdb',['gdb','--version']),('kernel',['uname','-a']),('compiler',[args.cc,'--version'])]:
  r=subprocess.run(command,capture_output=True,text=True,check=True);(out/(label+'.txt')).write_text(r.stdout+r.stderr)
 def save():(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
 def check(name,fn):
  try:fn();report['checks'].append({'name':name,'status':'PASS'});print('PASS',name,flush=True)
  except Exception as e:report['checks'].append({'name':name,'status':'FAIL','error':str(e)});print('FAIL',name,str(e),flush=True)
  save()
 def session(name,commands,expected=0,setup=True):
  directory=out/name;directory.mkdir()
  lines=['set pagination off','set confirm off','set debuginfod enabled off',
   'set environment GLIBC_TUNABLES glibc.malloc.tcache_count=3:glibc.malloc.tcache_max=32768']
  if args.debug_directory:lines+=['set debug-file-directory '+args.debug_directory]
  if setup:lines+=['file '+str(binary),'break checkpoint','run']
  script=directory/'commands.gdb';script.write_text('\n'.join(lines+commands)+'\n')
  r=subprocess.run(['gdb','-nx','-q','-batch','-x',str(script)],capture_output=True,text=True,timeout=180)
  text=r.stdout+r.stderr;(directory/'session.txt').write_text(text)
  (directory/'process.json').write_text(json.dumps({'returncode':r.returncode,'expected':expected})+'\n')
  require(r.returncode==expected,'unexpected GDB status: '+text[-1800:])
  if expected==0:require('Traceback' not in text and 'Python Exception' not in text,'unexpected Python exception')
  return text
 loader='source '+str(ROOT/'src/ressembly_heap_view.py')
 def oracle():
  commands=block(RAW)
  for stage in range(1,6):
   commands+=block('Path('+repr(str(out/'oracle'/('stage%d.json'%stage)))+').write_text(json.dumps(raw(),indent=2))')+['continue']
  session('oracle',commands)
 check('independent-raw-oracle',oracle)
 def snapshots():
  commands=[loader]+block('import json\nfrom pathlib import Path\nfrom ressembly.heap_view_gdb import HeapView')
  for stage in range(1,6):
   commands+=block('Path('+repr(str(out/'snapshots'/('stage%d.json'%stage)))+').write_text(json.dumps(HeapView().snapshot(),indent=2))')+['continue']
  session('snapshots',commands)
  for stage in range(1,6):
   oracle=json.loads((out/'oracle'/('stage%d.json'%stage)).read_text());state=json.loads((out/'snapshots'/('stage%d.json'%stage)).read_text())
   require(oracle['version']==version and state['glibc']==version,'loaded libc mismatch')
   require(len(state['tcache'])==len(oracle['entries']),'profile bin count mismatch')
   if version=='2.43':
    require(state['tcache_state']==oracle['state'],'dummy-state mismatch')
    require(oracle['state']==('inactive' if stage==1 else 'active'),'lazy first-free initialization not exercised')
   require(state['bins'][0]['nodes']==oracle['unsorted'],'unsorted/raw oracle mismatch')
   require(state['bins'][2]['nodes']==oracle['smallbin3'],'smallbin/raw oracle mismatch')
   if version=='2.36':require(state['fastbins'][1]['nodes']==oracle['fastbin'],'fastbin/raw oracle mismatch')
   else:require(not state['fastbins'],'removed fastbins invented')
   for actual,expected in zip(state['tcache'],oracle['entries']):
    require(actual['nodes']==expected['nodes'],'tcache raw chain mismatch')
    if version=='2.36':require(actual.get('declared_count')==expected['raw_value'],'count mismatch')
    else:
     require(actual.get('available_slots')==expected['raw_value'],'available slot mismatch')
     require(actual.get('declared_count')==oracle['capacity']-expected['raw_value'],'occupancy mismatch')
   if stage==2:
    require(oracle['entries'][1]['nodes']==list(reversed(oracle['small'][:3])),'count tunable not exercised')
    overflow=[oracle['small'][4]-16,oracle['small'][3]-16]
    require((oracle['fastbin'] if version=='2.36' else oracle['smallbin3'])==overflow,'overflow destination mismatch')
   if stage==3 and version=='2.43':
    nodes=[n for row in oracle['entries'][64:] for n in row['nodes']]
    require(set(nodes)==set(oracle['big']),'large tcache not exercised')
    sizes=[oracle['sizes'][str(n)] for n in nodes]
    require(sizes==sorted(sizes),'large tcache not sorted by chunk size')
   if stage==4 and version=='2.43':require(oracle['selected']==oracle['big'][2],'exact-size lookup did not unlink interior cached chunk')
   if stage==5 and version=='2.43':
    require(oracle['selected_miss'] not in oracle['big'],'nonexact request unexpectedly consumed cached large chunk')
    nodes=[n for row in oracle['entries'][64:] for n in row['nodes']]
    require(set(nodes)=={oracle['big'][0],oracle['big'][1]},'large-cache miss changed remaining nodes')
 check('structure-vs-separate-oracle',snapshots)
 def negative(name,commands,fragment):
  def run():require(fragment in session(name,[loader]+commands,1),'specific refusal missing')
  check(name,run)
 negative('unsupported-version',['set {char}&__libc_version = 57','rs-heap-view'],'supported profile')
 negative('limit-zero',['rs-heap-view arena 0'],'node limit')
 negative('invalid-chunk',['rs-heap-view chunk 1'],'aligned')
 negative('inferior-call-expression',['rs-heap-view chunk malloc(16)'],'invalid literal')
 def missing_debug():
  text=session('missing-debug',['set debug-file-directory /nonexistent','file '+str(binary),'break checkpoint','run',loader,'rs-heap-view'],1,setup=False)
  require('debug symbols' in text,'missing debug symbols refusal absent')
 check('missing-debug',missing_debug)
 def layout_guard():
  code="from ressembly.heap_view_gdb import HeapView\nh=HeapView()\nh.profile=dict(h.profile)\nh.profile['tcache_entries_offset']+=8\ntry:h.validate_tcache_type()\nexcept ValueError as e:\n if 'tcache array layout' not in str(e):raise\nelse:raise ValueError('injected incompatible layout accepted')"
  session('injected-layout-guard',[loader]+block(code))
 check('injected-layout-guard',layout_guard)
 for name,value,expected in [('cycle','small[2] ^ (small[2] >> 12)','cycle'),('unreadable','0x1000 ^ (small[2] >> 12)','unreadable'),('unaligned','0x1001 ^ (small[2] >> 12)','unaligned_or_invalid')]:
  commands=[loader,'continue','set *(unsigned long *)small[2] = '+value]+block("from ressembly.heap_view_gdb import HeapView\ns=HeapView().snapshot()\nif s['tcache'][1]['end'] != "+repr(expected)+":raise ValueError('wrong termination')")
  check(name,lambda name=name,commands=commands:session(name,commands))
 def read_only():session('read-only',[loader]+block(RAW+"\nbefore=raw()\nfrom ressembly.heap_view_gdb import HeapView\nHeapView().snapshot(1)\nif before!=raw():raise ValueError('snapshot changed raw memory/registers')"))
 check('read-only',read_only)
 def limited():
  session('bounded-traversal',[loader,'continue']+block("from ressembly.heap_view_gdb import HeapView\ns=HeapView().snapshot(1)\nif s['tcache'][1]['end']!='limit' or len(s['tcache'][1]['nodes'])!=1:raise ValueError('unbounded traversal')"))
 check('bounded-traversal',limited)
 def default_capacity():
  commands=['unset environment GLIBC_TUNABLES','file '+str(binary),'break checkpoint','run',loader]
  commands+=block("from ressembly.heap_view_gdb import HeapView\ns=HeapView().snapshot()\ncapacity=int(gdb.parse_and_eval('mp_.tcache_count'))\nif capacity!="+str(16 if version=='2.43' else 7)+":raise ValueError('default capacity changed')\nif gdb.parse_and_eval('tcache').type.target()['entries'].type.range()[1]+1!="+str(76 if version=='2.43' else 64)+":raise ValueError('default bin count')")
  session('default-capacity',commands,setup=False)
 check('default-capacity',default_capacity)
 if version=='2.43':
  def count_zero():
   commands=['set environment GLIBC_TUNABLES glibc.malloc.tcache_count=0','file '+str(binary),'break checkpoint','run',loader,'continue']
   commands+=block("from ressembly.heap_view_gdb import HeapView\ns=HeapView().snapshot()\nraw=int(gdb.parse_and_eval('tcache'))\ndisabled=int(gdb.parse_and_eval('&__tcache_dummy.disabled'))\nif raw!=disabled or s['tcache_state']!='disabled' or s['tcache']:raise ValueError('real count-zero path not disabled')")
   session('count-zero-real',commands,setup=False)
  check('count-zero-real',count_zero)
  def default_cutoff():
   commands=['set environment GLIBC_TUNABLES glibc.malloc.tcache_count=3','file '+str(binary),'break checkpoint','run',loader,'continue','continue']
   commands+=block(RAW+"\nfrom ressembly.heap_view_gdb import HeapView\ns=HeapView().snapshot()\no=raw()\nif any(row['nodes'] for row in s['tcache'][64:]):raise ValueError('default cutoff unexpectedly cached large chunks')\nif any(row.get('declared_count')!=0 for row in s['tcache'][64:]):raise ValueError('empty large bins mislabeled occupied')\nif s['tcache_max_chunk_size_exclusive']!=number('mp_.tcache_max_bytes'):raise ValueError('threshold/raw mismatch')\nif number('mp_.tcache_max_bytes')>=0x510:raise ValueError('default threshold corpus assumptions invalid')")
   session('default-large-cutoff',commands,setup=False)
  check('default-large-cutoff',default_cutoff)
  for state in ('inactive','disabled'):
   commands=[loader,'set tcache = &__tcache_dummy.'+state]+block("from ressembly.heap_view_gdb import HeapView\ns=HeapView().snapshot()\nif s['tcache_state']!="+repr(state)+" or s['tcache']:raise ValueError('dummy interpreted as active occupancy')")
   check('dummy-'+state,lambda state=state,commands=commands:session('dummy-'+state,commands))
  negative('null-tcache',['set tcache = 0','rs-heap-view'],'null tcache contradicts')
  negative('counter-exceeds-capacity',['continue','set tcache->num_slots[0] = 65535','rs-heap-view'],'available slots')
 if not args.skip_collectors:
  for label,validator in [('collector-v1','validate-heap-linux.py'),('collector-v2','validate-history-v2-linux.py')]:
   def run_validator(label=label,validator=validator):
    r=subprocess.run([sys.executable,str(ROOT/'scripts'/validator),str(out/label)],capture_output=True,text=True,timeout=1800)
    (out/(label+'.txt')).write_text(r.stdout+r.stderr);require(r.returncode==0,'collector corpus failed; inspect '+label+'.txt')
    captures=[json.loads(p.read_text()) for p in (out/label).glob('*/history.json')]
    versions={d['metadata'].get('glibc_version') for d in captures}
    require(versions=={version},'nested collector loaded profiles contradict declared target: '+repr(versions))
   check(label,run_validator)
  if version=='2.43':
   def interrupted_first_free():
    history=out/'first-free-interrupted.json'
    commands=['file '+str(out/'collector-v1/heap_lab'),'break lab_ready','run','source '+str(ROOT/'src/ressembly_heap.py'),
     'rsheap-start '+str(history),'break lab_initialized','rsheap-continue','break tcache_free_init','rsheap-continue']
    commands+=block("if gdb.newest_frame().name()!='tcache_free_init':raise ValueError('helper breakpoint not reached')")
    commands+=['rsheap-continue','rsheap-save']
    session('first-free-external-helper-breakpoint',commands,setup=False)
    data=json.loads(history.read_text())
    require(data['metadata'].get('exit_code')==0,'interrupted firstfree failed target exit')
    require(sum(e['kind']=='free_return' for e in data['events'])==2,'interrupted firstfree double counted or omitted')
   check('first-free-external-helper-breakpoint',interrupted_first_free)
   def interrupted_first_free_v2():
    history=out/'first-free-v2-interrupted.json'
    commands=['file '+str(out/'collector-v1/heap_lab'),'break lab_ready','run','source '+str(ROOT/'src/ressembly_history.py'),
     'rshist-start '+str(history),'break lab_initialized','rshist-continue','break tcache_free_init','rshist-continue']
    commands+=block("if gdb.newest_frame().name()!='tcache_free_init':raise ValueError('helper breakpoint not reached')")
    commands+=['rshist-continue','rshist-save']
    session('first-free-v2-external-helper-breakpoint',commands,setup=False)
    data=json.loads(history.read_text())
    require(data['metadata'].get('exit_code')==0,'v2 interrupted firstfree failed exit')
    require(sum(e['kind']=='free_return' for e in data['events'])==2,'v2 interrupted firstfree double counted or omitted')
   check('first-free-v2-external-helper-breakpoint',interrupted_first_free_v2)

 report['sources']=hashes;report['sources_unchanged']=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in hashes.items())
 report['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
 report['status']='PASS' if report['sources_unchanged'] and all(c['status']=='PASS' for c in report['checks']) else 'FAIL'
 save();return 0 if report['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
