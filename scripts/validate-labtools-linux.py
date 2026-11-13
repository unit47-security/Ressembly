#!/usr/bin/env python3
"""Compile owned ELF variants and compare static properties against GNU readelf."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ressembly.labtools import elf_properties, cyclic, cyclic_offset


def main():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('requires Linux x86_64; offline tests cannot close this gate')
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    records = []
    def run(name, argv, expected=0):
        process = subprocess.run(argv, capture_output=True, text=True, timeout=60,
                                 env={**os.environ, 'LC_ALL': 'C'})
        (out / (name + '.stdout')).write_text(process.stdout)
        (out / (name + '.stderr')).write_text(process.stderr)
        (out / (name + '.process.json')).write_text(json.dumps({'argv': list(map(str, argv)), 'exit': process.returncode}, indent=2))
        if process.returncode != expected:
            raise RuntimeError(name + ' unexpected process exit: ' + str(process.returncode))
        return process.stdout
    def check(name, condition):
        records.append({'name': name, 'pass': bool(condition)})
        if not condition:
            raise RuntimeError('failed: ' + name)
    versions = {tool: run('version-' + tool, [tool, '--version']).splitlines()[0] for tool in ('gcc', 'readelf', 'strip')}
    versions.update(kernel=platform.release(), machine=platform.machine(), python=platform.python_version())
    (out / 'versions.json').write_text(json.dumps(versions, indent=2))
    try:
        flags = {
            'hardened': ['-fPIE', '-pie', '-fstack-protector-all', '-Wl,-z,relro,-z,now,-z,noexecstack'],
            'partial': ['-fno-pie', '-no-pie', '-fno-stack-protector', '-Wl,-z,relro,-z,lazy,-z,noexecstack'],
            'unprotected': ['-fno-pie', '-no-pie', '-fno-stack-protector', '-Wl,-z,norelro,-z,lazy,-z,execstack'],
            'shared': ['-fPIC', '-shared', '-fno-stack-protector', '-Wl,-z,relro,-z,lazy,-z,noexecstack'],
        }
        for name, options in flags.items():
            binary = out / name
            run('compile-' + name, ['gcc', '-O0', '-g', *options, str(ROOT / 'examples/protections_lab.c'), '-o', str(binary)])
        shutil.copyfile(out / 'hardened', out / 'stripped')
        run('strip', ['strip', '--strip-all', str(out / 'stripped')])
        expected = {
            'hardened': ('yes', 'yes', 'full_configuration', 'symbol_present'),
            'partial': ('no', 'yes', 'partial_configuration', 'not_observed'),
            'unprotected': ('no', 'no', 'none', 'not_observed'),
            'shared': ('undetermined', 'yes', 'partial_configuration', 'not_observed'),
            'stripped': ('yes', 'yes', 'full_configuration', 'symbol_present'),
        }
        for name, wanted in expected.items():
            binary = out / name
            parsed = elf_properties(binary)
            output = run('cli-' + name, [sys.executable, str(ROOT / 'scripts/ressembly-lab.py'), 'elf', str(binary)])
            check(name + '-cli', json.loads(output) == parsed)
            oracle = run('readelf-' + name, ['readelf', '-W', '-h', '-l', '-d', '-s', str(binary)])
            actual = tuple(parsed[key] for key in ('pie', 'nx_stack', 'relro', 'canary_indicator'))
            check(name + '-compiler-configuration', actual == wanted)
            stack_line = next(line for line in oracle.splitlines() if line.strip().startswith('GNU_STACK'))
            oracle_nx = 'no' if 'E' in ''.join(stack_line.split()[6:-1]) else 'yes'
            oracle_now = any(('BIND_NOW' in line or 'NOW' in line and ('FLAGS' in line)) for line in oracle.splitlines())
            oracle_relro = 'full_configuration' if 'GNU_RELRO' in oracle and oracle_now else 'partial_configuration' if 'GNU_RELRO' in oracle else 'none'
            check(name + '-readelf-stack-relro', parsed['nx_stack'] == oracle_nx and parsed['relro'] == oracle_relro)
            check(name + '-readelf-pie-canary', parsed['pie_flag'] == ('Flags: PIE' in oracle or 'Flags: NOW PIE' in oracle) and
                  (parsed['canary_indicator'] == 'symbol_present') == ('__stack_chk_fail' in oracle))
            (out / (name + '.json')).write_text(json.dumps(parsed, indent=2))
        data = bytearray((out / 'hardened').read_bytes())
        struct.pack_into('<Q', data, 40, 0)
        struct.pack_into('<HHH', data, 58, 0, 0, 0)
        (out / 'sectionless').write_bytes(data)
        sectionless = elf_properties(out / 'sectionless')
        check('sectionless-canary-unknown', sectionless['canary_indicator'] == 'unknown_no_symbol_tables')
        check('sectionless-segment-properties', tuple(sectionless[k] for k in ('pie', 'nx_stack', 'relro')) == expected['hardened'][:3])
        (out / 'malformed').write_bytes(b'\x7fELF' + bytes(60))
        for name in ('malformed', 'missing'):
            run('reject-' + name, [sys.executable, str(ROOT / 'scripts/ressembly-lab.py'), 'elf', str(out / name)], 2)
            check(name + '-rejected', True)
        check('known-pattern', cyclic(40) == b'aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaa')
        for width in (4, 8):
            pattern = cyclic(1024, width)
            for offset in (0, 33, 512, 1024 - width):
                needle = pattern[offset:offset + width]
                for endian in ('little', 'big'):
                    result = cyclic_offset(int.from_bytes(needle, endian), len(pattern), width, endian)
                    check('offset-%d-%d-%s' % (width, offset, endian), result['status'] == 'unique' and result['offsets'] == [offset])
        check('ambiguous-explicit', cyclic_offset(b'a', 100)['status'] == 'ambiguous')
        check('missing-explicit', cyclic_offset(b'ZZZZ', 100)['status'] == 'not_found')
        run('unit-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-p', 'test_labtools.py', '-v'])
        check('offline-regressions-in-linux', True)
        status = 'PASS'
    except Exception as error:
        status = 'FAIL'
        (out / 'failure.txt').write_text(str(error))
        raise
    finally:
        paths = ['src/ressembly/labtools.py', 'scripts/ressembly-lab.py', 'examples/protections_lab.c',
                 'scripts/validate-labtools-linux.py', 'tests/test_labtools.py']
        (out / 'tested-source-sha256.txt').write_text(''.join(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() + '  ' + p + '\n' for p in paths))
        (out / 'validation.json').write_text(json.dumps({'status': status, 'checks': records,
              'scope': 'ELF file properties on owned Linux x86_64 binaries; no runtime protection or exploitability claim'}, indent=2))
    print(json.dumps({'status': status, 'checks': len(records), 'output': str(out)}))


if __name__ == '__main__':
    main()
