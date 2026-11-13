"""Verify the five explicit R0 profiles, not tool superiority or exploitability."""
import json
from pathlib import Path
import re
import sys

EXPECTED = {('gdb', 'manual'), ('gef', 'manual'), ('gef', 'helper'),
            ('pwndbg', 'manual'), ('pwndbg', 'helper')}
LABELS = {'buffer': ['buffer-before', 'buffer-after'],
          'pointer': ['pointer-before', 'pointer-after'],
          'uaf-good': ['heap-live', 'heap-live-after-access'],
          'uaf-bad': ['heap-live', 'heap-freed-before-access', 'heap-freed-after-access']}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(directories):
    profiles, rows, sources, runtimes = set(), [], set(), set()
    for directory in directories:
        directory = Path(directory)
        manifest = json.loads((directory / 'manifest.json').read_text())
        metadata = manifest['metadata']
        key = metadata['tool'], metadata['profile']
        require(key in EXPECTED and key not in profiles, 'unexpected/duplicate profile')
        profiles.add(key)
        sources.add(metadata['source_sha256'])
        runtimes.add(metadata['gdb'])
        seen = set()
        for run in manifest['runs']:
            case, mode = run['case'], 'good' if run['control'] else 'bad'
            require((case, mode) not in seen, 'duplicate case')
            seen.add((case, mode))
            name = case + '-' + mode
            log = (directory / (name + '.txt')).read_text()
            require(run['setup_status'] == 'commands-observed' and run['debugger_exit'] == 0,
                    name + ': debugger/setup error')
            require(run['inferior_exit_observed'] and 'R0_EXIT_CODES=[0]' in log,
                    name + ': missing inferior exit')
            labels = re.findall(r'^R0_CHECKPOINT=([^\r\n]+)', log, re.MULTILINE)
            require(labels == LABELS.get(name, LABELS.get(case)), name + ': wrong checkpoints')
            count = log.count('R0_WATCH_TRIGGER')
            expected = (int(mode == 'bad') if case != 'uaf' else 1) if key[1] == 'manual' else 0
            require(count == expected == run['watchpoint_triggers'], name + ': wrong manual trigger count')
            samples = re.findall(r'^R0_BYTES=([a-f0-9]+)', log, re.MULTILINE)
            if case == 'buffer':
                require(samples == ['41' * 16, '42' * (12 if mode == 'bad' else 8) +
                                     '41' * (4 if mode == 'bad' else 8)], name + ': buffer sample mismatch')
            elif case == 'pointer':
                require(len(samples) == 2 and (samples[0] != samples[1]) == (mode == 'bad'),
                        name + ': pointer sample mismatch')
            rows.append(dict(tool=key[0], profile=key[1], case=case, mode=mode,
                             checkpoints=len(labels), manual_watch_triggers=count,
                             wall_seconds=run['wall_seconds']))
        require(seen == {(case, mode) for case in ('buffer', 'uaf', 'pointer')
                         for mode in ('good', 'bad')}, 'missing cases')
    require(profiles == EXPECTED and len(sources) == len(runtimes) == 1,
            'five profiles must use one source and GDB runtime')
    return dict(status='consistent_30_raw_sessions',
                limitations='No authenticated origin, human timing, superiority, or exploitability claim.',
                rows=rows)


if __name__ == '__main__':
    try:
        print(json.dumps(verify(sys.argv[1:]), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit('FAIL: ' + str(exc))
