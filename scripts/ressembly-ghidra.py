#!/usr/bin/env python3
"""Validate or resolve a local GDB code reference with an explicitly selected Ghidra."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ressembly import code_reference
from ressembly.experiments import read_json, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('validate', 'analyze'):
        p = sub.add_parser(action)
        p.add_argument('reference'); p.add_argument('binary')
        if action == 'analyze':
            p.add_argument('--ghidra-home', required=True)
            p.add_argument('--java-home', required=True)
            p.add_argument('--workdir', required=True)
    args = parser.parse_args()
    try:
        reference = code_reference.validate(read_json(args.reference, 1048576), args.binary)
        if args.action == 'validate':
            print(json.dumps({'status':'consistent_reference','module_sha256':reference['module_sha256'],
                              'file_offset':reference['file_offset'],'authenticity':'not_proven_by_file'}, indent=2))
            return 0
        home, java = Path(args.ghidra_home).resolve(), Path(args.java_home).resolve() / 'bin/java'
        utility = home / 'Ghidra/Framework/Utility/lib/Utility.jar'
        require(java.is_file() and utility.is_file(), 'Ghidra installation or JDK missing')
        output = Path(args.workdir).absolute()
        require(not output.exists() and not output.is_symlink(), 'workdir must be new')
        output.mkdir(parents=True)
        for name in ('projects', 'settings', 'cache', 'tmp'):
            (output / name).mkdir()
        normalized = output / 'reference.json'
        normalized.write_text(json.dumps(reference, ensure_ascii=True))
        result_path = output / 'ghidra-link.json'
        scripts = Path(__file__).resolve().parents[1] / 'integrations/ghidra'
        # Direct invocation avoids LaunchSupport -save and keeps all caches/settings local.
        command = [str(java), '-Xmx1G', '-XX:ParallelGCThreads=2', '-XX:CICompilerCount=2',
            '-Djava.awt.headless=true', '-Djava.system.class.loader=ghidra.GhidraClassLoader', '-Dapplication.settingsdir='+str(output/'settings'),
            '-Dapplication.cachedir='+str(output/'cache'), '-Dapplication.tempdir='+str(output/'tmp'),
            '-Djava.io.tmpdir='+str(output/'tmp'), '-cp', str(utility), 'ghidra.Ghidra',
            'ghidra.app.util.headless.AnalyzeHeadless', str(output/'projects'), 'ressembly',
            '-import', str(Path(args.binary).resolve()), '-scriptPath', str(scripts),
            '-postScript', 'RessemblyLink.java', str(normalized), str(result_path),
            '-analysisTimeoutPerFile', '60', '-max-cpu', '2', '-log', str(output/'ghidra.log'),
            '-scriptlog', str(output/'script.log')]
        (output/'command.json').write_text(json.dumps(command, indent=2))
        with (output/'stdout.txt').open('w') as stdout, (output/'stderr.txt').open('w') as stderr:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=180,
                                    stdin=subprocess.DEVNULL, cwd=str(output))
        (output/'process.json').write_text(json.dumps({'returncode':result.returncode}))
        require(result.returncode == 0 and result_path.is_file(), 'Ghidra failed or did not resolve the reference; inspect workdir logs')
        linked = read_json(result_path)
        require(linked.get('schema') == 'ressembly.ghidra-link.v1' and linked.get('module_sha256') == reference['module_sha256']
                and linked.get('file_offset') == reference['file_offset'], 'Ghidra output identity mismatch')
        print(json.dumps(linked, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
        print('Ressembly Ghidra: '+str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
