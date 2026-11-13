#!/usr/bin/env python3
"""Validate the real headless bridge using an owned Linux ELF/GDB capture corpus.
The corpus must include pie/exec, *-reference.json, *-nm.txt, *-readelf.txt,
and oracle-provenance.txt with sha256sum and GNU tool versions. No debugger
claims are derived from this Mac Ghidra run alone.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PATCH='''// Owned negative validation fixture; changes only a disposable imported program.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.mem.MemoryBlockSourceInfo;
public class PatchOwnedProgram extends GhidraScript {
 public void run() throws Exception {
  long offset=Long.parseLong(getScriptArgs()[0]);
  for(MemoryBlock block:currentProgram.getMemory().getBlocks()) {
   if(!block.isExecute()) continue;
   for(MemoryBlockSourceInfo source:block.getSourceInfos()) {
    Address a=source.locateAddressForFileOffset(offset);
    if(a!=null) { currentProgram.getMemory().setByte(a,(byte)(currentProgram.getMemory().getByte(a)^255)); println("OWNED_PROGRAM_PATCHED"); return; }
   }
  }
  throw new Exception("owned fixture offset not mapped");
 }
}
'''


def require(value,message):
    if not value: raise ValueError(message)


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output'); parser.add_argument('--corpus',required=True)
    parser.add_argument('--ghidra-home',required=True); parser.add_argument('--java-home',required=True)
    args=parser.parse_args()
    output=Path(args.output).resolve(); output.mkdir(parents=True,exist_ok=False)
    source=Path(args.corpus).resolve(); corpus=output/'owned corpus with spaces'; corpus.mkdir()
    for path in source.iterdir():
        if path.is_file(): shutil.copy2(path,corpus/path.name)
    home=Path(args.ghidra_home).resolve(); java=Path(args.java_home).resolve()/'bin/java'
    utility=home/'Ghidra/Framework/Utility/lib/Utility.jar'
    require(java.is_file() and utility.is_file(),'Ghidra/JDK missing')
    source_names=['scripts/ressembly-ghidra.py','src/ressembly/code_reference.py',
                  'integrations/ghidra/RessemblyLink.java','scripts/validate-ghidra-local.py']
    hashes={name:digest(ROOT/name) for name in source_names}
    report={'scope':'Ghidra headless on '+platform.platform()+'; owned ELF and references previously captured on Linux',
            'sources':hashes,'checks':[], 'corpus_hashes':{p.name:digest(p) for p in corpus.iterdir() if p.is_file()}}
    def check(name,value):
        report['checks'].append({'name':name,'status':'PASS' if value else 'FAIL'})
        report['status']='IN_PROGRESS' if value else 'FAIL'
        (output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
        require(value,name)
    def run(name,command,expected=0,timeout=240):
        result=subprocess.run(command,capture_output=True,text=True,timeout=timeout,stdin=subprocess.DEVNULL,cwd=output)
        (output/(name+'.stdout')).write_text(result.stdout)
        (output/(name+'.stderr')).write_text(result.stderr)
        (output/(name+'.process.json')).write_text(json.dumps({'argv':command,'returncode':result.returncode},indent=2))
        if expected is not None: require(result.returncode==expected,name+': '+result.stderr[-2000:])
        return result
    run('java-version',[str(java),'-version'])
    shutil.copy2(home/'Ghidra/application.properties',output/'ghidra-application.properties')
    cli=[sys.executable,str(ROOT/'scripts/ressembly-ghidra.py')]
    provenance=(corpus/'oracle-provenance.txt').read_text()
    references={}
    for name in ('pie','exec'):
        binary=corpus/name; reference_path=corpus/(name+'-reference.json')
        reference=json.loads(reference_path.read_text()); references[name]=reference
        check(name+' corpus build bound to Linux oracle hash',digest(binary)+'  '+name in provenance and
              digest(binary)==reference['module_sha256'])
        sample=bytes.fromhex(reference['file_bytes_hex']); offset=reference['file_offset']
        check(name+' sampled bytes match binary',binary.read_bytes()[offset:offset+len(sample)]==sample)
        symbols=[]
        for line in (corpus/(name+'-nm.txt')).read_text().splitlines():
            parts=line.split()
            if len(parts)==3 and parts[1] in ('t','T'): symbols.append((int(parts[0],16),parts[2]))
        entry=next(address for address,symbol in symbols if symbol=='debug_stop')
        end=min(address for address,symbol in symbols if address>entry)
        executable=[]
        for line in (corpus/(name+'-readelf.txt')).read_text().splitlines():
            fields=line.split()
            if fields and fields[0]=='LOAD' and 'E' in fields:
                fileoff,va,_,size,_=[int(v,16) for v in fields[1:6]]
                if fileoff<=offset<fileoff+size: executable.append(va+offset-fileoff)
        check(name+' nm/readelf resolve runtime sample inside debug_stop',executable==[reference['elf_virtual_address']]
              and entry<=executable[0]<end)
        run(name+'-validate',cli+['validate',str(reference_path),str(binary)])
        workdir=output/(name+' Ghidra positive')
        positive=run(name+'-analyze',cli+['analyze',str(reference_path),str(binary),
            '--ghidra-home',str(home),'--java-home',str(java.parent.parent),'--workdir',str(workdir)])
        linked=json.loads(positive.stdout)
        check(name+' Ghidra function and relative address match independent nm',linked['function']=='debug_stop'
              and int(linked['ghidra_address'],16)-int(linked['function_entry'],16)==executable[0]-entry
              and linked['module_sha256']==digest(binary) and linked['file_offset']==offset)
        check(name+' bridge reports no program mutation',linked['program_modified'] is False)
        if name=='exec': check('nonPIE Ghidra address equals ELF virtual address',int(linked['ghidra_address'],16)==executable[0])
        saved=(workdir/'ghidra-link.json').read_bytes()
        run(name+'-refuse-existing',cli+['analyze',str(reference_path),str(binary),
            '--ghidra-home',str(home),'--java-home',str(java.parent.parent),'--workdir',str(workdir)],1)
        check(name+' existing result cannot be overwritten',(workdir/'ghidra-link.json').read_bytes()==saved)
    ref=references['pie']; binary=corpus/'pie'
    bad_inputs=[('wrong-hash',dict(ref,module_sha256='0'*64)),('fractional-offset',dict(ref,file_offset=ref['file_offset']+0.5)),
                ('overflow-offset',dict(ref,file_offset=2**64)),('wrong-runtime',dict(ref,runtime_pc=ref['runtime_pc']+1)),
                ('wrong-elf-va',dict(ref,elf_virtual_address=ref['elf_virtual_address']+1))]
    for name,bad in bad_inputs:
        path=output/(name+'.json'); path.write_text(json.dumps(bad))
        run('cli-'+name,cli+['validate',str(path),str(binary)],1)
        check('CLI rejects '+name,True)
    # Run Java directly too: the Python guard must not conceal script acceptance bugs.
    def direct(name,reference,patch=False,existing=False,raw=None):
        directory=output/('direct '+name); directory.mkdir()
        for component in ('projects','settings','cache','tmp','scripts'): (directory/component).mkdir()
        shutil.copy2(ROOT/'integrations/ghidra/RessemblyLink.java',directory/'scripts/RessemblyLink.java')
        (directory/'scripts/PatchOwnedProgram.java').write_text(PATCH)
        reference_path=directory/'reference.json'; reference_path.write_text(raw if raw is not None else json.dumps(reference))
        result_path=directory/'result.json'
        if existing: result_path.write_text('owned-result-sentinel')
        command=[str(java),'-Xmx1G','-XX:ParallelGCThreads=2','-XX:CICompilerCount=2',
            '-Djava.awt.headless=true','-Djava.system.class.loader=ghidra.GhidraClassLoader',
            '-Dapplication.settingsdir='+str(directory/'settings'),'-Dapplication.cachedir='+str(directory/'cache'),
            '-Dapplication.tempdir='+str(directory/'tmp'),'-Djava.io.tmpdir='+str(directory/'tmp'),
            '-cp',str(utility),'ghidra.Ghidra','ghidra.app.util.headless.AnalyzeHeadless',
            str(directory/'projects'),'owned','-import',str(binary),'-scriptPath',str(directory/'scripts')]
        if patch: command+=['-preScript','PatchOwnedProgram.java',str(ref['file_offset'])]
        command+=['-postScript','RessemblyLink.java',str(reference_path),str(result_path),
                  '-analysisTimeoutPerFile','60','-max-cpu','2','-log',str(directory/'ghidra.log'),
                  '-scriptlog',str(directory/'script.log')]
        actual=run('direct-'+name,command,expected=None)
        log=actual.stdout+actual.stderr
        require('Execute script: RessemblyLink.java' in log and 'Import succeeded' in log,
                name+': script not actually reached on imported program')
        require('RESSEMBLY_LINK_OK' not in log and ('Exception' in log or 'ERROR' in log),
                name+': explicit script rejection missing')
        if patch: require('OWNED_PROGRAM_PATCHED' in log and 'Program bytes changed' in log,'negative patch was not observed')
        check('direct Java rejects '+name,(result_path.read_text()=='owned-result-sentinel') if existing else not result_path.exists())
        report.setdefault('direct_process_codes',{})[name]=actual.returncode
    for name,bad in bad_inputs: direct(name,bad)
    direct('duplicate-key',ref,raw=json.dumps(ref)[:-1]+',"file_offset":'+str(ref['file_offset'])+'}')
    direct('patched-program',ref,patch=True)
    direct('existing-output',ref,existing=True)
    check('source code unchanged during validation',all(digest(ROOT/name)==value for name,value in hashes.items()))
    report['status']='PASS'
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'PASS','checks':len(report['checks']),'headless_positive_runs':2,
                      'headless_negative_runs':len(report['direct_process_codes'])},indent=2))

if __name__=='__main__': main()
