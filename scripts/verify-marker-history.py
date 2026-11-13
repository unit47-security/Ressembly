"""Check this project's seven-marker lab only; JSON cannot attest acquisition origin.

Input budget: 2 MiB. No debugger is invoked and no input file is modified.
"""
import json
from pathlib import Path
import re
import sys

MAX_FILE_BYTES = 2 * 1024 * 1024
SUCCESS = ('PASS: file matches marker-lab expectations; '
           'acquisition provenance is not independently verified.')
KINDS = ('alloc', 'snapshot', 'snapshot', 'free_completed',
         'alloc', 'snapshot', 'free_completed')
MARKER_KINDS = {'alloc': 1, 'free_completed': 2, 'snapshot': 3}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, expected, label):
    require(type(value) is int and value == expected, label + ': unexpected integer')


def pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-finite JSON number: ' + value)


def load_capture(path):
    with Path(path).open('rb') as stream:
        payload = stream.read(MAX_FILE_BYTES + 1)
    require(len(payload) <= MAX_FILE_BYTES, 'marker-lab file exceeds 2 MiB budget')
    return json.loads(payload.decode('utf-8'), object_pairs_hook=pairs_without_duplicates,
                      parse_constant=reject_constant)


def verify_capture(result):
    require(type(result) is dict, 'capture must be an object')
    require(result.get('schema') == 'ressembly.marker-history.v1', 'unsupported capture schema')
    metadata, coverage = result.get('metadata'), result.get('coverage')
    require(type(metadata) is dict and type(coverage) is dict, 'missing metadata or coverage')
    require(metadata.get('process_status') == 'exited', 'lab process did not exit')
    integer(metadata.get('exit_code'), 0, 'exit_code')
    require(metadata.get('acquisition_status') == 'partial_marker_coverage',
            'lab acquisition must retain partial marker coverage')
    require(coverage.get('mode') == 'explicit_markers_only', 'unsupported coverage mode')
    require(coverage.get('writes_observed') is False, 'snapshots are not observed writes')
    require(coverage.get('all_allocator_calls') is False, 'markers do not cover all allocator calls')
    integer(coverage.get('snapshot_limit'), 64, 'snapshot_limit')
    integer(coverage.get('event_limit'), 10000, 'event_limit')
    events = result.get('events')
    require(type(events) is list and len(events) == 7, 'expected seven marker-lab events')
    objects, generations, active, thread = {}, {}, {}, None
    samples = {1: b'A' * 32, 2: b'AAAA' + b'B' + b'A' * 27, 5: b'C' * 32}
    for index, (event, kind) in enumerate(zip(events, KINDS)):
        label = 'event #' + str(index + 1)
        require(type(event) is dict, label + ': expected object')
        require(event.get('kind') == kind, label + ': unexpected marker kind')
        integer(event.get('sequence'), index + 1, label + ' sequence')
        integer(event.get('marker_kind'), MARKER_KINDS[kind], label + ' marker_kind')
        require(event.get('provenance') == 'explicit_target_marker' and
                event.get('source') == 'rs_event', label + ': missing marker provenance')
        require('error' not in event and 'read_error' not in event, label + ': contains acquisition error')
        current_thread, address = event.get('thread'), event.get('address')
        require(type(current_thread) is int and current_thread > 0, label + ': invalid thread')
        thread = current_thread if thread is None else thread
        require(current_thread == thread, 'lab requires a single observed thread')
        require(type(address) is int and 0 < address < 2 ** 64, label + ': invalid address')
        require(isinstance(event.get('pc'), str) and
                re.fullmatch(r'0x[0-9a-fA-F]{1,16}', event['pc']) is not None,
                label + ': missing or invalid PC')
        integer(event.get('size'), 0 if kind == 'free_completed' else 32, label + ' size')
        if kind == 'alloc':
            require(address not in active, label + ': address already live')
            generation = generations.get(address, 0) + 1
            generations[address] = generation
            oid = '%x:%d' % (address, generation)
            active[address] = oid
            objects[oid] = dict(address=address, size=32, generation=generation, state='live')
        else:
            require(address in active, label + ': unknown or freed address')
            oid = active[address]
        require(event.get('object_id') == oid, label + ': incorrect allocation identity')
        if kind == 'free_completed':
            objects[oid]['state'] = 'freed'
            del active[address]
        elif kind == 'snapshot':
            require(event.get('snapshot_provenance') == 'gdb_inferior_read_memory',
                    label + ': missing snapshot provenance declaration')
            require(event.get('bytes_hex') == samples[index].hex(), label + ': unexpected sample bytes')
            integer(event.get('requested_bytes'), 32, label + ' requested_bytes')
            integer(event.get('captured_bytes'), 32, label + ' captured_bytes')
            integer(event.get('compared_bytes'), 32 if index == 2 else 0, label + ' compared_bytes')
            require(event.get('truncated') is False, label + ': unexpected truncation')
            changed = event.get('changed_offsets')
            require((type(changed) is list and len(changed) == 1 and
                     type(changed[0]) is int and changed[0] == 4) if index == 2 else
                    'changed_offsets' in event and changed is None,
                    label + ': incorrect sample difference')
    require(type(result.get('objects')) is dict and result['objects'] == objects,
            'final object table does not match marker lifecycle')
    # Python considers True == 1; reject booleans in the persisted numeric object fields.
    for obj in result['objects'].values():
        require(all(type(obj[key]) is int for key in ('address', 'size', 'generation')),
                'object numeric fields must be integers')


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print('Usage: python3 scripts/verify-marker-history.py CAPTURE.json', file=sys.stderr)
        return 2
    try:
        verify_capture(load_capture(arguments[0]))
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        return 1
    print(SUCCESS)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
