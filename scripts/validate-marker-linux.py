"""Run actual GDB marker/lifecycle checks on owned targets in Linux x86-64.

Usage: python3 scripts/validate-marker-linux.py NEW_OUTPUT_DIRECTORY
No mock GDB is used here. Run in a disposable authorized laboratory.
"""
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NEGATIVE_C = r'''
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
__attribute__((noinline)) void rs_event(int kind, uintptr_t ptr, size_t size) {
    __asm__ volatile ("" : : "r"(kind), "r"(ptr), "r"(size) : "memory");
}
int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "read-failure") == 0) {
        /* Intentionally invalid marker declarations; never dereference this address. */
        rs_event(1, (uintptr_t)1, 32);
        rs_event(3, (uintptr_t)1, 32);
        return 0;
    }
    char *p = malloc(32);
    rs_event(1, (uintptr_t)p, 32);
    if (!p) return 1;
    memset(p, 'A', 32);
    raise(SIGUSR1);
    free(p);
    return 0;
}
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def quote(value):
    value = str(value)
    require('\n' not in value and '\r' not in value, 'newline in GDB path')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        print('Requires actual Linux x86-64 GDB environment; no validation performed.', file=sys.stderr)
        return 2
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    metadata = {'host': platform.platform(), 'tests': [], 'provenance': 'actual_gdb_subprocesses',
                'scope': 'owned_marker_laboratory_only'}
    for name, command in [('compiler', ['cc', '--version']), ('gdb', ['gdb', '--version']),
                          ('libc', ['getconf', 'GNU_LIBC_VERSION']), ('kernel', ['uname', '-a']),
                          ('gdb-python', ['gdb', '-nx', '-q', '-batch', '-ex', 'python import sys; print(sys.version)'])]:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        (output / (name + '.txt')).write_text(result.stdout + result.stderr)
    source = output / 'negative.c'
    source.write_text(NEGATIVE_C)
    binary, negative = output / 'marker_lab', output / 'negative_lab'
    for src, target in [(ROOT / 'examples/marker_lab.c', binary), (source, negative)]:
        subprocess.run(['cc', '-std=c11', '-g3', '-O0', '-fno-omit-frame-pointer', '-Wall',
                        '-Wextra', '-Werror', str(src), '-o', str(target)], check=True)
    metadata['target_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
    metadata['negative_target_sha256'] = hashlib.sha256(negative.read_bytes()).hexdigest()

    def session(name, executable, commands, expected_code=0, allow_traceback=False):
        directory = output / name
        directory.mkdir()
        history = directory / 'history.json'
        lines = ['set pagination off', 'set confirm off', 'file ' + quote(executable),
                 'source ' + str(ROOT / 'src/ressembly_gdb.py')]
        lines += [line.replace('{history}', quote(history)) for line in commands]
        script = directory / 'commands.gdb'
        script.write_text('\n'.join(lines) + '\n')
        start = time.monotonic()
        result = subprocess.run(['gdb', '-nx', '-q', '-batch', '-x', str(script)],
                                capture_output=True, text=True, timeout=180)
        elapsed = time.monotonic() - start
        (directory / 'session.txt').write_text(result.stdout + result.stderr)
        (directory / 'process.json').write_text(json.dumps(dict(
            command=['gdb', '-nx', '-q', '-batch', '-x', str(script)],
            returncode=result.returncode, seconds=elapsed), indent=2) + '\n')
        allowed = (expected_code,) if type(expected_code) is int else expected_code
        require(result.returncode in allowed,
                'GDB return code ' + str(result.returncode) + '; expected ' + str(allowed))
        require(allow_traceback or 'Traceback' not in result.stdout + result.stderr,
                'unexpected Python traceback in GDB session')
        return history, result, elapsed

    def record(name, operation):
        try:
            detail = operation()
            metadata['tests'].append(dict(name=name, result='PASS', **(detail or {})))
            print('PASS:', name)
        except Exception as exc:
            metadata['tests'].append(dict(name=name, result='FAIL', error=str(exc)))
            print('FAIL:', name, str(exc))
        (output / 'validation.json').write_text(json.dumps(metadata, indent=2) + '\n')

    def normal(name):
        history, result, elapsed = session(name, binary, ['rs-start {history}', 'run', 'rs-show', 'rs-save'])
        require(result.returncode == 0, result.stdout + result.stderr)
        verified = subprocess.run([sys.executable, str(ROOT / 'scripts/verify-marker-history.py'),
                                   str(history)], capture_output=True, text=True)
        (history.parent / 'verifier.txt').write_text(verified.stdout + verified.stderr)
        require(verified.returncode == 0, verified.stdout + verified.stderr)
        return {'seconds': elapsed, 'gdb_returncode': result.returncode,
                'history': str(history.relative_to(output))}

    record('normal-1', lambda: normal('normal-1'))
    record('normal-2', lambda: normal('normal-2'))

    def oracle_comparison():
        # Independent built-in GDB commands: no Ressembly Python source loaded.
        directory = output / 'independent-oracle'
        directory.mkdir()
        script = directory / 'commands.gdb'
        commands = ['set pagination off', 'set confirm off', 'file ' + quote(binary),
                    'break rs_event', 'commands', 'silent',
                    'printf "ORACLE kind=%d ptr=%lu size=%lu thread=%d\\n", kind, ptr, size, $_thread',
                    'if kind == 3', 'x/32bx ptr', 'end',
                    'info registers rip rdi rsi rdx', 'x/i $pc', 'continue', 'end', 'run']
        script.write_text('\n'.join(commands) + '\n')
        start = time.monotonic()
        result = subprocess.run(['gdb', '-nx', '-q', '-batch', '-x', str(script)],
                                capture_output=True, text=True, timeout=180)
        (directory / 'session.txt').write_text(result.stdout + result.stderr)
        (directory / 'process.json').write_text(json.dumps(dict(returncode=result.returncode,
            command=['gdb', '-nx', '-q', '-batch', '-x', str(script)]), indent=2) + '\n')
        require(result.returncode == 0, result.stdout + result.stderr)
        require('Traceback' not in result.stdout + result.stderr, 'unexpected oracle traceback')
        observed = []
        for line in result.stdout.splitlines():
            marker = re.match(r'ORACLE kind=(\d+) ptr=(\d+) size=(\d+) thread=(\d+)', line)
            if marker:
                observed.append(dict(zip(('marker_kind', 'address', 'size', 'thread'),
                                         map(int, marker.groups())), bytes_hex=''))
            elif observed and observed[-1]['marker_kind'] == 3:
                dump = re.match(r'^\s*0x[0-9a-fA-F]+(?:\s+<[^>]+>)?:\s*(.*)$', line)
                if dump:
                    observed[-1]['bytes_hex'] += ''.join(re.findall(r'0x([0-9a-fA-F]{2})\b', dump[1]))
        captured = json.loads((output / 'normal-1/history.json').read_text())['events']
        require(len(observed) == len(captured) == 7, 'independent oracle marker count differs')
        for manual, event in zip(observed, captured):
            require(manual['marker_kind'] == event['marker_kind'], 'oracle marker kind mismatch')
            require(manual['size'] == event['size'], 'oracle marker size mismatch')
            require(manual['thread'] > 0, 'oracle thread unavailable')
            if event['kind'] == 'snapshot':
                require(manual['bytes_hex'] == event['bytes_hex'], 'oracle sample mismatch')
        (directory / 'comparison.json').write_text(json.dumps(dict(
            result='PASS', observations=observed,
            compared=['marker_order', 'marker_size', 'snapshot_bytes'],
            not_compared=['absolute_addresses_across_runs', 'PC_addresses_across_runs'],
            reason='Independent GDB run; ASLR pointers are not cross-run identities.'), indent=2) + '\n')
        return {'seconds': time.monotonic() - start, 'gdb_returncode': result.returncode}
    record('independent-gdb-oracle', oracle_comparison)

    def repeat_run():
        history, result, elapsed = session('repeat-run', binary,
            ['rs-start {history}', 'run', 'run', 'rs-save'])
        capture = json.loads(history.read_text())
        require(len(capture['events']) == 7, 'second run merged or lost markers')
        require(capture['metadata']['process_status'] == 'exited', 'first run status was overwritten')
        require('REJECTED' in result.stdout, 'follow-up run was not visibly rejected')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('repeat-run', repeat_run)

    def budget():
        history, result, elapsed = session('event-budget', binary,
            ['rs-start {history} 1', 'run', 'rs-save'])
        capture = json.loads(history.read_text())
        require(len(capture['events']) == 1, 'event budget not respected')
        require(capture['metadata']['acquisition_status'] == 'event_limit_reached', 'missing limit state')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('event-budget', budget)

    def read_failure():
        history, result, elapsed = session('read-failure', negative,
            ['set args read-failure', 'rs-start {history}', 'run', 'rs-save'])
        capture = json.loads(history.read_text())
        require(capture['metadata']['acquisition_status'] == 'error', 'missing read error state')
        require(capture['events'][-1]['kind'] == 'acquisition_error', 'missing read error event')
        require('bytes_hex' not in capture['events'][-1], 'read error invented byte sample')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('read-failure', read_failure)

    def signal_stop():
        history, result, elapsed = session('signal-stop', negative,
            ['handle SIGUSR1 stop print nopass', 'rs-start {history}', 'run', 'rs-save'])
        capture = json.loads(history.read_text())
        # The signal checkpoint itself is interrupted. Normal GDB shutdown can
        # subsequently mark the still-open capture debugger_exit.
        require(capture['metadata'].get('stop_signal') == 'SIGUSR1', 'signal not retained')
        require(capture['metadata']['acquisition_status'] == 'interrupted', 'signal run appears complete')
        require(len(capture['events']) == 1, 'unexpected markers after signal stop')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('signal-stop', signal_stop)

    def explicit_stop():
        history, result, elapsed = session('explicit-stop', negative,
            ['handle SIGUSR1 stop print nopass', 'rs-start {history}', 'run', 'rs-stop', 'rs-save'])
        capture = json.loads(history.read_text())
        require(capture['metadata']['process_status'] == 'stopped_by_user', 'missing explicit stop')
        require(capture['metadata']['acquisition_status'] == 'interrupted', 'explicit stop appears complete')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('explicit-stop', explicit_stop)

    def exit_unknown():
        history, result, elapsed = session('kill', negative,
            ['handle SIGUSR1 stop print nopass', 'rs-start {history}', 'run', 'kill', 'rs-save'])
        capture = json.loads(history.read_text())
        require(capture['metadata']['process_status'] == 'ended_without_exit_code', 'kill appears normal')
        require(capture['metadata']['exit_code'] is None, 'kill invented exit code')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('kill', exit_unknown)

    def source_again():
        history, result, elapsed = session('reload', binary,
            ['rs-start {history}', 'source ' + str(ROOT / 'src/ressembly_gdb.py')],
            expected_code=0, allow_traceback=True)
        diagnostic = result.stdout + result.stderr
        require(diagnostic.count('Traceback (most recent call last):') == 1 and
                diagnostic.count('gdb.GdbError: Ressembly is already loaded; use a new GDB session') == 1,
                'reload did not produce only its expected source diagnostic')
        require(json.loads(history.read_text())['events'] == [], 'reload invented markers')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('reload', source_again)

    def path_preserved():
        directory = output / 'existing-output'
        directory.mkdir()
        existing = directory / 'preserve.json'
        existing.write_text('existing capture must survive\n')
        history, result, elapsed = session('existing-path-check', binary,
            ['rs-start ' + quote(existing)], expected_code=1)
        require(existing.read_text() == 'existing capture must survive\n', 'existing output was overwritten')
        require('File exists' in result.stderr + result.stdout, 'existing file rejection not visible')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('existing-output', path_preserved)

    def already_running():
        history, result, elapsed = session('already-running', binary, ['start', 'rs-start {history}'], expected_code=1)
        require(not history.exists(), 'already running target acquired a capture')
        require('before run' in result.stdout + result.stderr, 'running target rejection not visible')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('already-running', already_running)

    def retarget():
        history, result, elapsed = session('changed-target', binary,
            ['rs-start {history}', 'file ' + quote(negative), 'set args read-failure', 'run', 'rs-save'])
        capture = json.loads(history.read_text())
        require(capture['metadata']['process_status'] == 'context_changed', 'changed target not rejected')
        require(capture['events'] == [], 'different target markers merged')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('changed-target', retarget)

    def replaced_build():
        changed = output / 'changed-build-target'
        shutil.copy2(binary, changed)
        history, result, elapsed = session('changed-build', changed,
            ['rs-start {history}', 'python open(' + repr(str(changed)) + ", 'ab').write(b'x')",
             'run', 'rs-save'])
        capture = json.loads(history.read_text())
        require(capture['metadata']['process_status'] == 'context_changed', 'changed build not rejected')
        require('build changed' in capture['metadata'].get('last_error', ''), 'missing build mismatch reason')
        require(capture['events'] == [], 'different build markers merged')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('changed-build', replaced_build)

    def missing_marker():
        plain_source, plain_binary = output / 'plain.c', output / 'plain'
        plain_source.write_text('int main(void) { return 0; }\n')
        subprocess.run(['cc', '-g3', '-O0', str(plain_source), '-o', str(plain_binary)], check=True)
        history, result, elapsed = session('missing-marker', plain_binary,
            ['set breakpoint pending on', 'rs-start {history}'], expected_code=1)
        require(not history.exists(), 'unresolved marker left a capture')
        require('not resolved' in result.stderr + result.stdout, 'unresolved marker not rejected')
        return {'seconds': elapsed, 'gdb_returncode': result.returncode}
    record('missing-marker', missing_marker)

    def reject_late_command_error():
        name = 'late-command-error'
        try:
            session(name, binary, ['rs-start {history}', 'run', 'rs-save',
                                   'this_command_must_not_exist'])
        except ValueError as exc:
            require('GDB return code' in str(exc), 'unexpected failure in late-command-error check')
            directory = output / name
            process = json.loads((directory / 'process.json').read_text())
            require(process['returncode'] == 1, 'expected explicit GDB command failure')
            verify = subprocess.run([sys.executable, str(ROOT / 'scripts/verify-marker-history.py'),
                                     str(directory / 'history.json')], capture_output=True, text=True)
            require(verify.returncode == 0, 'control capture was not valid before late error')
            return {'gdb_returncode': process['returncode'], 'expected_rejection': True,
                    'reason': 'Valid JSON does not mask a later GDB command failure.'}
        raise ValueError('validator incorrectly accepted late GDB command failure')
    record('validator-rejects-late-command-error', reject_late_command_error)

    failures = sum(test['result'] != 'PASS' for test in metadata['tests'])
    metadata['status'] = 'PASS' if failures == 0 else 'FAIL'
    metadata['limitations'] = ['No general allocator tracking or write tracing validated here.',
                               'Elapsed times describe this environment, not native performance.']
    (output / 'validation.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
