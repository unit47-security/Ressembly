#!/usr/bin/env python3
"""Actual Linux clean-prefix packaging, launch, integrity and uninstall checks."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def require(value,message):
    if not value: raise ValueError(message)


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    require(platform.system()=='Linux' and platform.machine()=='x86_64','actual Linux x86-64 required')
    require(os.geteuid()!=0,'run as ordinary lab user, not root')
    require(len(sys.argv) in (2,3),'usage: validate-package-linux.py NEW_DIRECTORY [EXISTING_ZIP]')
    out=Path(sys.argv[1]).resolve(); out.mkdir(parents=True,exist_ok=False)
    report={'scope':'actual Linux x86-64 clean prefix; host emulation declared separately','checks':[]}
    def check(name,value):
        require(value,name); report['checks'].append({'name':name,'status':'PASS'})
    def run(name,command,expected=0):
        result=subprocess.run(command,capture_output=True,text=True,timeout=180)
        (out/(name+'.stdout')).write_text(result.stdout)
        (out/(name+'.stderr')).write_text(result.stderr)
        (out/(name+'.process.json')).write_text(json.dumps({'argv':command,'returncode':result.returncode},indent=2))
        require(result.returncode==expected,name+': '+result.stderr[-2000:])
        return result
    def config_state():
        return {name: digest(Path.home()/name) if (Path.home()/name).is_file() else None
                for name in ('.gdbinit','.profile','.bashrc','.zshrc')}
    before=config_state()
    for label,command in [('kernel',['uname','-a']),('gdb-version',['gdb','--version']),
                          ('libc',['getconf','GNU_LIBC_VERSION']),('compiler',['cc','--version'])]:
        run(label,command)
    (out/'os-release.txt').write_text(Path('/etc/os-release').read_text())
    package=out/'ressembly.zip'; repeat=out/'ressembly-repeat.zip'
    builder=[sys.executable,str(ROOT/'scripts/build-local-package.py')]
    installer=[sys.executable,str(ROOT/'scripts/install-local.py')]
    if len(sys.argv)==2:
        run('build',builder+[str(package)]); run('rebuild',builder+[str(repeat)])
        check('byte reproducible package',package.read_bytes()==repeat.read_bytes())
        report['build_reproducibility']='verified from source on this guest'
    else:
        supplied=Path(sys.argv[2]).resolve()
        shutil.copyfile(supplied,package)
        check('supplied archive copied byte-for-byte',digest(package)==digest(supplied))
        report['build_reproducibility']='not tested here; supplied prebuilt archive'
    with zipfile.ZipFile(package) as archive:
        manifest=json.loads(archive.read('PACKAGE.json'))
        report['manifest']=manifest
        check('no workspace evidence keys or comparators in archive',all(
            not any(part in name.split('/') for part in ('work','prototype','.git','__pycache__'))
            and not name.endswith(('.qcow2','.pem','.key')) for name in archive.namelist()))
    prefix=out/'prefix with spaces'
    run('install',installer+['install',str(package),str(prefix)])
    launcher=str(prefix/'bin/ressembly')
    run('verify',[launcher,'verify'])
    check('complete install verified',True)
    discovery=json.loads(run('doctor',[launcher,'doctor']).stdout)
    (out/'doctor.json').write_text(json.dumps(discovery,indent=2))
    check('doctor probes actual GDB Python',discovery['basic_requirements_found'] and 'gdb_runtime' in discovery)
    for command in ('lab','experiment','plugins','ghidra'):
        run('help-'+command,[launcher,command,'--help'])
    check('all standalone CLI wrappers load',True)
    plugin=json.loads(run('sample-plugin-inspect',[launcher,'plugins','inspect',str(prefix/'lib/ressembly/examples/plugins/summary')]).stdout)
    check('installed sample includes manifest and code',plugin['id']=='summary' and len(plugin['sha256'])==64)
    pattern=json.loads(run('offset',[launcher,'lab','offset','--hex','62616161','--length','64','--width','4']).stdout)
    check('installed pattern offset vector',pattern['offsets']==[4])
    binary=out/'debug_lab'
    run('compile',['cc','-g3','-O0','-Wall','-Wextra','-Werror',str(prefix/'lib/ressembly/examples/debug_lab.c'),'-o',str(binary)])
    script=out/'session.gdb'
    script.write_text('set pagination off\nset confirm off\nbreak debug_stop\nrun\nrs-help\nrs-context\nrs-maps\npython\n'
        "import gdb,json\nfrom pathlib import Path\nfrom ressembly import debug_gdb as dg\n"
        "snap=dg.context_snapshot()\n"
        "if snap['registers']['rip']!=int(gdb.parse_and_eval('$pc')): raise ValueError('PC mismatch')\n"
        "if snap['status']!='complete': raise ValueError('incomplete context')\n"
        "p=int(gdb.parse_and_eval('&lab_bytes'))\n"
        "if dg.memory_dump(p,3)['hex']!='616263': raise ValueError('bytes mismatch')\n"
        "Path("+repr(str(out/'installed-snapshot.json'))+").write_text(json.dumps(snap))\n"
        'end\ncontinue\ncontinue\n')
    run('gdb-installed',[launcher,'gdb','-q','-batch',str(binary),'-x',str(script)])
    check('actual installed GDB context and bytes match primitives',(out/'installed-snapshot.json').exists())
    run('verify-after-launch',[launcher,'verify'])
    check('launches do not add cache files or mutate install',True)
    dossier=out/'experiment.json'
    run('experiment-create',[launcher,'experiment','create',str(dossier),str(binary),'Installed example'])
    reopened=json.loads(run('experiment-show',[launcher,'experiment','show',str(dossier)]).stdout)
    check('installed dossier roundtrip',reopened['build']['sha256']==digest(binary))
    # Added user content must prevent any removal; it is deleted only by this test afterwards.
    added=prefix/'user-note.txt'; added.write_text('owned test sentinel')
    run('uninstall-refuses-extra',[launcher,'uninstall'],1)
    check('extra content preserved and no partial uninstall',added.read_text()=='owned test sentinel' and (prefix/'bin/ressembly').exists())
    added.unlink()
    run('uninstall',[launcher,'uninstall'])
    check('clean uninstall removes own prefix',not prefix.exists())
    check('dossier outside prefix preserved',dossier.exists())
    # CRC-valid content tampering must be rejected before prefix creation.
    tampered=out/'tampered.zip'
    with zipfile.ZipFile(package) as original, zipfile.ZipFile(tampered,'w') as bad:
        for info in original.infolist():
            data=original.read(info.filename)
            if info.filename=='lib/ressembly/README.md': data=b'tampered'
            bad.writestr(info,data)
    bad_prefix=out/'must-not-exist'
    run('tampered-refused',installer+['install',str(tampered),str(bad_prefix)],1)
    check('tampered package rejected before writes',not bad_prefix.exists())
    check('user global configuration untouched',config_state()==before)
    run('offline-packaging-tests',[sys.executable,'-B','-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_packaging.py','-v'])
    check('packaging unit tests on Linux',True)
    sources=['packaging/local_package.py','packaging/launcher.py','scripts/build-local-package.py',
             'scripts/install-local.py','scripts/validate-package-linux.py','tests/test_packaging.py']
    report['sources']={name:digest(ROOT/name) for name in sources}
    report['package_sha256']=digest(package); report['status']='PASS'
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'PASS','checks':len(report['checks']),'package_sha256':report['package_sha256']},indent=2))

if __name__=='__main__': main()
