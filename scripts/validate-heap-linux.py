"""Actual owned-target GDB checks for selected glibc 2.36/2.43 object histories.
Usage: python3 scripts/validate-heap-linux.py NEW_DIRECTORY
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MODULE = 'from ressembly import heap_gdb as hg; '
OID = 'hg._session.model.active[int(gdb.parse_and_eval("lab_p"))]'
WATCH = 'python ' + MODULE + 'gdb.execute("rsheap-watch " + ' + OID + ' + " 0 1")'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def quote(path):
    text = str(path)
    require('\n' not in text and '\r' not in text, 'newline in command path')
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def load(history):
    return json.loads(history.read_text())


def lifecycle(capture):
    require(capture['schema'] == 'ressembly.object-history.v1', 'wrong schema')
    require(capture['metadata']['acquisition_status'] == 'partial', 'capture not normally completed')
    require(capture['metadata']['exit_code'] == 0, 'target exit failed')
    events = capture['events']
    allocated = [event for event in events if event['kind'] == 'allocation']
    require(len(allocated) == 2, 'expected two successful malloc calls')
    require(allocated[0]['address'] == allocated[1]['address'], 'address reuse not exercised in this run')
    require(allocated[0]['object_id'] != allocated[1]['object_id'], 'reused address kept old identity')
    require([obj['generation'] for obj in capture['objects'].values()] == [1, 2], 'wrong generations')
    require(all(obj['state'] == 'freed' for obj in capture['objects'].values()), 'normal frees not completed')
    require(sum(event['kind'] == 'free_return' for event in events) == 2, 'missing completed frees')
    require(sum(event['kind'] == 'free_null' for event in events) == 1, 'free(NULL) not observed')
    failed = [event for event in events if event['kind'] == 'allocation_failed']
    require(len(failed) == 1 and failed[0]['requested_size'] == 2 ** 64 - 1, 'malloc failure missing')
    require(not capture['coverage']['all_allocator_calls'] and not capture['coverage']['all_writes'],
            'coverage is overstated')
    require(all(event['sequence'] == index + 1 for index, event in enumerate(events)), 'sequence mismatch')
    require(all(event.get('thread') == 1 and event.get('pc') for event in events), 'event context missing')


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        print('Linux x86-64 actual GDB required; no validation performed.', file=sys.stderr)
        return 2
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    binary = output / 'heap_lab'
    subprocess.run(['cc', '-std=c11', '-g3', '-O0', '-fno-omit-frame-pointer', '-Wall', '-Wextra',
                    '-Werror', str(ROOT / 'examples/heap_lab.c'), '-o', str(binary)], check=True)
    report = dict(environment='actual Linux x86-64 guest; declare external virtualization separately',
                  target_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), tests=[], timings=[])
    for name, command in [('gdb', ['gdb', '--version']), ('compiler', ['cc', '--version']),
                          ('libc', ['getconf', 'GNU_LIBC_VERSION']), ('kernel', ['uname', '-a'])]:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        (output / (name + '.txt')).write_text(result.stdout + result.stderr)

    def session(name, commands, mode=None, checkpoints=(), expected=0, adapter=True, limit=1000, error_fragment=None):
        directory = output / name
        directory.mkdir()
        history = directory / 'history.json'
        lines = ['set pagination off', 'set confirm off', 'file ' + quote(binary)]
        if mode:
            lines += ['set args ' + mode]
        lines += ['break lab_ready', 'run']
        lines += ['break ' + point for point in checkpoints]
        if adapter:
            lines += ['source ' + str(ROOT / 'src/ressembly_heap.py'), 'rsheap-start ' + quote(history) + ' ' + str(limit)]
        lines += commands
        script = directory / 'commands.gdb'
        script.write_text('\n'.join(lines) + '\n')
        start = time.monotonic()
        result = subprocess.run(['gdb', '-nx', '-q', '-batch', '-x', str(script)],
                                capture_output=True, text=True, timeout=180)
        elapsed = time.monotonic() - start
        transcript = result.stdout + result.stderr
        (directory / 'session.txt').write_text(transcript)
        (directory / 'process.json').write_text(json.dumps(dict(returncode=result.returncode,
            seconds=elapsed, command=['gdb', '-nx', '-q', '-batch', '-x', str(script)]), indent=2) + '\n')
        require(result.returncode == expected, 'GDB code {} expected {}: {}'.format(
            result.returncode, expected, transcript[-800:]))
        if error_fragment is not None:
            old_style = (transcript.count('Traceback (most recent call last):') == 1 and
                         'gdb.error: ' + error_fragment in transcript)
            new_style = (transcript.count("Python Exception <class 'gdb.error'>: " + error_fragment) == 1 and
                         'Error occurred in Python: ' + error_fragment in transcript and
                         'Traceback (most recent call last):' not in transcript)
            require(expected == 1 and (old_style or new_style),
                    'expected one explicit wrapper command refusal: ' + transcript[-800:])
        else:
            require('Traceback' not in transcript and 'Python Exception' not in transcript,
                    'unexpected Python diagnostic: ' + transcript[-800:])
        return history, transcript, elapsed

    def record(name, function):
        try:
            detail = function() or {}
            report['tests'].append(dict(name=name, result='PASS', **detail))
            print('PASS:', name, flush=True)
        except Exception as exc:
            report['tests'].append(dict(name=name, result='FAIL', error=str(exc)))
            print('FAIL:', name, str(exc), flush=True)
        (output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')

    def ledger(name):
        history, _, elapsed = session(name, ['rsheap-continue', 'rsheap-save'])
        lifecycle(load(history))
        require(not load(history)['coverage']['windows'], 'ledger-only capture has a watch')
        report['timings'].append(dict(mode='gdb_ledger', seconds=elapsed))
    record('ledger-1', lambda: ledger('ledger-1'))
    record('ledger-2', lambda: ledger('ledger-2'))

    def region(name):
        history, _, elapsed = session(name, ['rsheap-continue', WATCH, 'rsheap-continue', 'rsheap-save'],
                                      checkpoints=['lab_initialized'])
        capture = load(history)
        lifecycle(capture)
        changes = [event for event in capture['events'] if event['kind'] == 'value_change']
        require([event['observed_hex'] for event in changes] == ['41', '42'], 'expected A,B changes only')
        require(all('writer_instruction_unknown' in event['pc_semantics'] for event in changes),
                'watch stop PC misrepresented as writer instruction')
        windows = capture['coverage']['windows']
        require(len(windows) == 1 and windows[0]['end_reason'] == 'free_entry', 'wrong observation end')
        first_free = next(event for event in capture['events'] if event['kind'] == 'free_begin')
        require(windows[0]['end_sequence'] < first_free['sequence'], 'allocator writes could enter window')
        require(not capture['coverage']['same_value_writes_observed'], 'same-value writes coverage overstated')
        second_oid = list(capture['objects'])[1]
        require(all(event['object_id'] != second_oid for event in changes), 'watch rebound on address reuse')
        report['timings'].append(dict(mode='gdb_ledger_one_watch', seconds=elapsed))
    record('region-1', lambda: region('region-1'))
    record('region-2', lambda: region('region-2'))

    def external_stop():
        history, _, _ = session('external-stop', ['rsheap-continue', 'rsheap-save', 'rsheap-stop'],
                                checkpoints=['lab_initialized'])
        capture = load(history)
        require(len(capture['objects']) == 1, 'continue ran past external breakpoint')
        require(all(obj['state'] == 'live' for obj in capture['objects'].values()), 'external stop state wrong')
        require(capture['metadata']['acquisition_status'] == 'interrupted', 'explicit pause became complete')
    record('external-stop', external_stop)

    def pending_malloc():
        history, _, _ = session('pending-malloc', ['rsheap-continue', 'rsheap-stop'],
                                checkpoints=['*__libc_malloc'])
        capture = load(history)
        require(capture['objects'] == {}, 'unreturned malloc fabricated allocation')
        require(any(event['kind'] == 'call_incomplete' for event in capture['events']), 'missing incomplete call')
    record('pending-malloc', pending_malloc)

    def incomplete_free():
        history, _, _ = session('incomplete-free', ['rsheap-continue', 'return', 'rsheap-continue'],
                                checkpoints=['*__libc_free'], expected=1)
        capture = load(history)
        require(capture['metadata']['acquisition_status'] == 'error', 'lost return not rejected')
        require(next(iter(capture['objects'].values()))['state'] == 'unknown_after_incomplete_free',
                'unreturned free declared freed')
    record('incomplete-free', incomplete_free)

    def signal():
        history, _, _ = session('signal', ['handle SIGUSR1 stop print nopass', 'rsheap-continue', 'rsheap-stop'],
                                mode='signal')
        capture = load(history)
        require(capture['metadata'].get('stop_signal') == 'SIGUSR1', 'signal not retained')
        require(capture['metadata']['acquisition_status'] == 'interrupted', 'signal appears normal completion')
    record('signal', signal)

    def wrong_selection(name, selection):
        command = 'python ' + MODULE + 'gdb.execute("rsheap-watch " + ' + OID + ' + " ' + selection + '")'
        history, _, _ = session(name, ['rsheap-continue', command],
                                checkpoints=['lab_initialized'], expected=1, error_fragment=(
                                    'selected region exceeds the requested allocation' if selection == '32 1'
                                    else 'region must be naturally aligned'))
        require(not load(history)['coverage']['windows'], 'invalid selection created a window')
    record('out-of-bounds', lambda: wrong_selection('out-of-bounds', '32 1'))
    record('misaligned', lambda: wrong_selection('misaligned', '1 8'))

    def duplicate_watch():
        history, _, _ = session('second-watch', ['rsheap-continue', WATCH, WATCH],
                                checkpoints=['lab_initialized'], expected=1,
                                error_fragment='only one own observation region is allowed')
        windows = load(history)['coverage']['windows']
        require(len(windows) == 1 and 'active_sequence' not in windows[0], 'second watch broadened coverage')
    record('second-watch', duplicate_watch)

    def stale_identity():
        command = 'python ' + MODULE + 'gdb.execute("rsheap-watch " + next(iter(hg._session.model.objects)) + " 0 1")'
        history, _, _ = session('stale-id', ['rsheap-continue', command],
                                checkpoints=['lab_reused'], expected=1,
                                error_fragment='watch requires a live object identity')
        capture = load(history)
        require(len(capture['objects']) == 2 and not capture['coverage']['windows'], 'stale identity watch accepted')
    record('stale-id', stale_identity)

    def software_refused():
        history, text, _ = session('software-refused', ['rsheap-continue', 'set can-use-hw-watchpoints 0', WATCH],
                                    checkpoints=['lab_initialized'], expected=1,
                                    error_fragment='hardware watchpoint unavailable; software fallback refused')
        require('software fallback refused' in text, 'software fallback was not explicitly refused')
        require(not load(history)['coverage']['windows'], 'software watch claimed coverage')
    record('software-refused', software_refused)

    def hardware_exhaustion():
        commands = ['rsheap-continue', WATCH]
        commands += ['watch -location resource_slots[' + str(index) + ']' for index in range(4)]
        commands += ['rsheap-continue']
        history, text, _ = session('hardware-exhausted', commands,
                                    checkpoints=['lab_initialized'], expected=1)
        capture = load(history)
        require(capture['metadata']['acquisition_status'] == 'error', 'resource exhaustion not fail-closed')
        require(not any(event['kind'] == 'value_change' for event in capture['events']), 'failed insertion observed data')
        require(all('active_sequence' not in window for window in capture['coverage']['windows']),
                'failed hardware insertion declared active coverage')
        require('hardware' in text.lower() and 'insert' in text.lower(), 'actual hardware insertion failure missing')
    record('hardware-exhausted', hardware_exhaustion)

    def unreadable():
        history, text, _ = session('unreadable', ['rsheap-continue', WATCH], mode='unreadable',
                                    checkpoints=['lab_initialized'], expected=1,
                                    error_fragment='Cannot access memory at address')
        require(not load(history)['coverage']['windows'], 'unreadable region claimed data')
        require('Cannot access memory' in text, 'actual memory read failure absent')
    record('unreadable', unreadable)

    def unsupported(operation):
        history, text, _ = session('unsupported-' + operation,
            ['rsheap-continue', WATCH, 'rsheap-continue', 'rsheap-save'], mode=operation,
            checkpoints=['lab_initialized'])
        capture = load(history)
        require(capture['metadata']['acquisition_status'] == 'error', 'unsupported allocator continued')
        require('before execution: ' + operation in capture['metadata']['last_error'], 'guard reason missing')
        require(len(capture['objects']) == 1 and next(iter(capture['objects'].values()))['state'] == 'live',
                'unsupported allocator changed the observed lifetime')
        require(all(window['state'] == 'ended' for window in capture['coverage']['windows']), 'guard left coverage active')
    record('unsupported-realloc', lambda: unsupported('realloc'))
    record('unsupported-calloc', lambda: unsupported('calloc'))

    def second_run():
        history, _, _ = session('second-run', ['rsheap-continue', 'run', 'rsheap-continue'], expected=1)
        capture = load(history)
        lifecycle(capture)
        require(len(capture['events']) == 12, 'new run events were merged')
    record('second-run', second_run)

    def budget():
        history, _, _ = session('event-budget',
            ['rsheap-continue', 'rsheap-save'], limit=1)
        capture = load(history)
        require(len(capture['events']) == 1, 'event budget exceeded')
        require(capture['metadata']['acquisition_status'] == 'event_limit_reached', 'limit not visible')
    record('event-budget', budget)

    def watch_budget():
        history, _, _ = session('watch-budget', ['rsheap-continue', WATCH],
                                checkpoints=['lab_initialized'], expected=1, limit=2,
                                error_fragment='event budget reached; later observations are missing')
        capture = load(history)
        require(len(capture['events']) == 2, 'watch request exceeded event budget')
        require(capture['metadata']['acquisition_status'] == 'event_limit_reached', 'watch budget lost its status')
        require(not capture['coverage']['windows'], 'budget-exhausted watch claimed coverage')
    record('watch-budget', watch_budget)

    def independent_oracle():
        commands = ['printf "ORACLE loaded_glibc=%s\\n", __libc_version',
                    'break *__libc_malloc', 'commands', 'silent',
                    'printf "ORACLE malloc_size=%llu\\n", (unsigned long long)$rdi', 'continue', 'end',
                    'break *__libc_free', 'commands', 'silent',
                    'printf "ORACLE free_ptr=%llu\\n", (unsigned long long)$rdi', 'bt 5', 'continue', 'end', 'continue']
        _, text, _ = session('independent-allocator-oracle', commands, adapter=False)
        sizes = list(map(int, re.findall(r'ORACLE malloc_size=(\d+)', text)))
        pointers = list(map(int, re.findall(r'ORACLE free_ptr=(\d+)', text)))
        require(sizes == [32, 32, 2 ** 64 - 1], 'independent malloc arguments differ')
        loaded = re.findall(r'ORACLE loaded_glibc=([0-9.]+)', text)
        require(len(loaded) == 1 and loaded[0] in ('2.36', '2.43'), 'independent loaded libc unknown')
        # Preserve every physical invocation, including glibc 2.43 first-free reentry.
        expected_physical = 4 if loaded[0] == '2.43' else 3
        require(len(pointers) == expected_physical and pointers[-1] == 0 and
                pointers[0] != 0 and all(p == pointers[0] for p in pointers[:-1]),
                'independent physical free arguments/reuse differ')
        order = re.findall(r'ORACLE (malloc_size|free_ptr)=', text)
        require(order == (['malloc_size','free_ptr','free_ptr','malloc_size','free_ptr','free_ptr','malloc_size']
                if loaded[0] == '2.43' else ['malloc_size','free_ptr','malloc_size','free_ptr','free_ptr','malloc_size']),
                'independent allocator physical call order differs')
        evidence = dict(loaded_glibc=loaded[0], physical_free_arguments=pointers,
                        physical_malloc_sizes=sizes, physical_call_order=order,
                        source_user_free_calls=3, source_includes_free_null=True,
                        note='All physical hook entries retained; glibc 2.43 reenters free during lazy tcache initialization. Logical user calls follow the owned C source; physical entries are not silently deduplicated.')
        (output/'independent-allocator-oracle'/'physical-calls.json').write_text(json.dumps(evidence,indent=2)+'\n')
    record('independent-allocator-oracle', independent_oracle)

    def timings():
        for index in range(3):
            _, _, elapsed = session('baseline-gdb-' + str(index), ['continue'], adapter=False)
            report['timings'].append(dict(mode='gdb_no_hooks', seconds=elapsed))
            start = time.monotonic()
            result = subprocess.run([str(binary)], capture_output=True, timeout=30)
            require(result.returncode == 0, 'standalone baseline failed')
            report['timings'].append(dict(mode='standalone', seconds=time.monotonic() - start))
        report['timing_summary'] = {mode: statistics.median([row['seconds'] for row in report['timings']
            if row['mode'] == mode]) for mode in ('standalone', 'gdb_no_hooks', 'gdb_ledger', 'gdb_ledger_one_watch')}
        report['timing_limitations'] = 'Total subprocess wall time including GDB startup; emulated guest only, not native per-call overhead.'
    record('timing-controls', timings)

    report['host_glibc'] = os.confstr('CS_GNU_LIBC_VERSION')
    report['loaded_profile_versions'] = sorted({json.loads(p.read_text())['metadata'].get('glibc_version') for p in output.glob('*/history.json')})
    report['status'] = 'PASS' if all(test['result'] == 'PASS' for test in report['tests']) else 'FAIL'
    (output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
