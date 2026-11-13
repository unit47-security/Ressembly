"""Synthetic offline fixtures test lab-file consistency, never real GDB acquisition."""
import copy
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ressembly.history import History

SCRIPT = ROOT / 'scripts/verify-marker-history.py'
VERIFIER = runpy.run_path(str(SCRIPT))


def fixture(reuse=True):
    history = History(dict(process_status='exited', exit_code=0,
                           acquisition_status='partial_marker_coverage',
                           fixture_only=True, run_id='synthetic-offline-test'))
    second_address = 4096 if reuse else 8192
    for kind, address, data in [('alloc', 4096, None), ('snapshot', 4096, b'A' * 32),
                                ('snapshot', 4096, b'AAAA' + b'B' + b'A' * 27),
                                ('free_completed', 4096, None),
                                ('alloc', second_address, None),
                                ('snapshot', second_address, b'C' * 32),
                                ('free_completed', second_address, None)]:
        context = dict(thread=1, pc='0x401000', caller_pc='0x402000', source='rs_event',
                       marker_kind={'alloc': 1, 'free_completed': 2, 'snapshot': 3}[kind])
        if kind == 'snapshot':
            context['snapshot_provenance'] = 'gdb_inferior_read_memory'
        history.record(kind, address, 0 if kind == 'free_completed' else 32,
                       context=context, data=data)
    return history.export()


class MarkerVerifierTests(unittest.TestCase):
    def test_reused_and_distinct_addresses_are_both_valid(self):
        for reuse in (True, False):
            capture = fixture(reuse)
            before = copy.deepcopy(capture)
            VERIFIER['verify_capture'](capture)
            self.assertEqual(capture, before)

    def test_inconsistent_event_fields_are_rejected(self):
        alterations = [(0, 'sequence', True), (1, 'sequence', 1), (0, 'address', 0),
                       (0, 'size', 31), (0, 'marker_kind', True), (1, 'thread', 2),
                       (1, 'provenance', 'synthetic'), (1, 'source', 'other'),
                       (1, 'snapshot_provenance', 'unknown'), (1, 'pc', None),
                       (1, 'requested_bytes', 31), (1, 'captured_bytes', 0),
                       (1, 'compared_bytes', 32), (1, 'truncated', True),
                       (1, 'changed_offsets', []), (2, 'changed_offsets', []),
                       (2, 'bytes_hex', '41' * 32), (2, 'address', 8192),
                       (3, 'kind', 'alloc'), (4, 'object_id', '1000:1'),
                       (5, 'changed_offsets', [4]), (6, 'object_id', '1000:1')]
        for index, field, value in alterations:
            with self.subTest(index=index, field=field):
                capture = fixture()
                capture['events'][index][field] = value
                with self.assertRaises(ValueError):
                    VERIFIER['verify_capture'](capture)

    def test_missing_fields_and_acquisition_errors_are_rejected(self):
        for field in ('changed_offsets', 'bytes_hex', 'snapshot_provenance', 'thread', 'pc'):
            with self.subTest(field=field):
                capture = fixture()
                del capture['events'][1][field]
                with self.assertRaises(ValueError):
                    VERIFIER['verify_capture'](capture)
        for field in ('error', 'read_error'):
            capture = fixture()
            capture['events'][1][field] = 'failed'
            with self.assertRaises(ValueError):
                VERIFIER['verify_capture'](capture)

    def test_final_object_table_cannot_be_empty_forged_or_extended(self):
        for change in ('empty', 'state', 'size', 'generation', 'boolean', 'extra'):
            with self.subTest(change=change):
                capture = fixture()
                objects = capture['objects']
                if change == 'empty':
                    objects.clear()
                elif change == 'extra':
                    objects['forged'] = copy.deepcopy(objects['1000:1'])
                else:
                    field, value = {'state': ('state', 'live'), 'size': ('size', 33),
                                    'generation': ('generation', 7),
                                    'boolean': ('generation', True)}[change]
                    objects['1000:1'][field] = value
                with self.assertRaises(ValueError):
                    VERIFIER['verify_capture'](capture)

    def test_missing_events_schema_and_coverage_are_rejected(self):
        for field, value in [('schema', 'future'), ('events', []), ('metadata', None),
                             ('coverage', None), ('objects', [])]:
            capture = fixture()
            capture[field] = value
            with self.assertRaises(ValueError):
                VERIFIER['verify_capture'](capture)
        for field, value in [('writes_observed', True), ('all_allocator_calls', True),
                             ('mode', 'full_trace'), ('snapshot_limit', 32), ('event_limit', True)]:
            capture = fixture()
            capture['coverage'][field] = value
            with self.assertRaises(ValueError):
                VERIFIER['verify_capture'](capture)

    def test_incomplete_or_failed_process_is_rejected(self):
        for field, value in [('exit_code', False), ('exit_code', 1),
                             ('process_status', 'signal_stop'),
                             ('acquisition_status', 'collecting')]:
            capture = fixture()
            capture['metadata'][field] = value
            with self.assertRaises(ValueError):
                VERIFIER['verify_capture'](capture)

    def run_cli(self, path=None, optimized=False):
        command = [sys.executable] + (['-O'] if optimized else []) + [str(SCRIPT)]
        if path is not None:
            command.append(str(path))
        return subprocess.run(command, text=True, capture_output=True)

    def test_cli_rejects_invalid_file_even_when_optimized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.json'
            for optimized in (False, True):
                for payload in ('{"events":[]}', '{invalid', '[]', '{"a":1,"a":2}',
                                '{"value":NaN}'):
                    path.write_text(payload)
                    result = self.run_cli(path, optimized)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn('FAIL:', result.stderr)
                    self.assertNotIn('PASS:', result.stdout)

    def test_cli_success_does_not_attest_real_acquisition(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-fixture.json'
            path.write_text(json.dumps(fixture()))
            for optimized in (False, True):
                result = self.run_cli(path, optimized)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('provenance is not independently verified', result.stdout)
                self.assertNotIn('real marker acquisition', result.stdout)

    def test_cli_usage_missing_file_size_and_encoding(self):
        self.assertEqual(self.run_cli().returncode, 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            self.assertEqual(self.run_cli(path).returncode, 1)
            for payload in (b'\xff', b' ' * (VERIFIER['MAX_FILE_BYTES'] + 1)):
                path.write_bytes(payload)
                result = self.run_cli(path)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
