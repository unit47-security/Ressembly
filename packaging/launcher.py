#!/usr/bin/env python3
"""Local Ressembly launcher; installed prefix is resolved from this file."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
PREFIX = Path(__file__).resolve().parent.parent
ROOT = PREFIX/'lib/ressembly'
sys.path.insert(0, str(ROOT/'packaging'))
import local_package


def doctor():
    result = {'schema':'ressembly.doctor.v1', 'package_version':local_package.VERSION,
              'host_system':platform.system(), 'host_machine':platform.machine(),
              'python':platform.python_version(), 'host_libc':list(platform.libc_ver()),
              'gdb_path':shutil.which('gdb'), 'scope':'environment discovery, not operational certification'}
    if result['gdb_path']:
        expression = "python import gdb,sys,json; print('RESSEMBLY_DOCTOR='+json.dumps({'gdb':gdb.VERSION,'python':sys.version.split()[0]}))"
        try:
            run = subprocess.run([result['gdb_path'],'-nx','-q','-batch','-iex','set auto-load off',
                                  '-ex',expression], capture_output=True,text=True,timeout=20)
            lines=[line.partition('=')[2] for line in run.stdout.splitlines() if line.startswith('RESSEMBLY_DOCTOR=')]
            if run.returncode != 0 or len(lines) != 1:
                result['gdb_error']='GDB Python probe failed'
            else: result['gdb_runtime']=json.loads(lines[0])
        except (OSError,subprocess.TimeoutExpired,ValueError) as error:
            result['gdb_error']=str(error)
    result['basic_requirements_found'] = (result['host_system']=='Linux' and result['host_machine']=='x86_64'
        and sys.version_info >= (3,9) and 'gdb_runtime' in result
        and tuple(int(n) for n in result['gdb_runtime']['python'].split('.')[:2]) >= (3,9))
    result['module_prechecks'] = {'debug_memory': 'candidate' if result['basic_requirements_found'] else 'requirements_missing',
        'lab_experiments': 'available' if sys.version_info >= (3,9) else 'python_too_old',
        'heap_history_structure': ('candidate_glibc_'+result['host_libc'][1]) if result['host_libc'] in (['glibc','2.36'], ['glibc','2.43']) else 'unsupported_host_libc',
        'heap_debug_symbols': 'not_probed', 'ghidra_bridge': 'requires_separate_Ghidra_validation'}
    result['heap_profile_note']='Allocator modules independently validate loaded glibc; host version alone is insufficient.'
    print(json.dumps(result,indent=2))
    return 0 if result['basic_requirements_found'] else 1


def main():
    args=sys.argv[1:]
    if not args or args[0] in ('-h','--help','help'):
        print('Ressembly local alpha — GPL-3.0-or-later, without warranty\n'
              '  ressembly gdb [GDB arguments]      GDB -nx with suite loaded\n'
              '  ressembly lab [arguments]          pattern / offset / ELF\n'
              '  ressembly experiment [arguments]   local dossiers\n'
              '  ressembly plugins [arguments]      explicit trusted local plugins\n'
              '  ressembly ghidra [arguments]       offline build/offset bridge\n'
              '  ressembly doctor                  discover environment (not certification)\n'
              '  ressembly verify                  verify installed files\n'
              '  ressembly uninstall               remove only unchanged owned files\n'
              'Docs and examples: '+str(ROOT))
        return 0
    try:
        if args[0]=='uninstall' and len(args)==1:
            print(json.dumps(local_package.uninstall(PREFIX),indent=2)); return 0
        local_package.verify(PREFIX)
        if args[0]=='verify' and len(args)==1:
            print('Installed manifest and all files match. This does not authenticate the publisher.'); return 0
        if args[0]=='doctor' and len(args)==1: return doctor()
        if args[0] in ('lab','experiment','plugins','ghidra'):
            script=ROOT/'scripts'/('ressembly-'+args[0]+'.py')
            return subprocess.call([sys.executable,'-B',str(script)]+args[1:])
        if args[0]=='gdb':
            if platform.system()!='Linux' or platform.machine()!='x86_64':
                raise ValueError('operational target requires Linux x86-64')
            executable=shutil.which('gdb')
            if not executable: raise ValueError('GDB is missing; install the documented prerequisites separately')
            bootstrap='python import runpy,sys; sys.dont_write_bytecode=True; runpy.run_path('+repr(str(ROOT/'src/ressembly_suite.py'))+')'
            return subprocess.call([executable,'-nx','-iex','set auto-load off','-ex',bootstrap]+args[1:])
        raise ValueError('unknown command; use --help')
    except (ValueError,OSError,TypeError,KeyError) as error:
        print('Ressembly: '+str(error),file=sys.stderr); return 1


if __name__=='__main__':
    sys.exit(main())
