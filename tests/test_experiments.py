import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ressembly import experiments as ex


class Experiments(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / 'owned-bin'
        self.binary.write_bytes(b'owned build')
        self.path = self.root / 'experiment.json'
        self.data = ex.create(self.path, self.binary, 'owned experiment')
        self.sha = self.data['build']['sha256']

    def snap(self, value=1, run='run-1'):
        return ex.add_snapshot(self.path, {'registers': {'rax': value}, 'partial': True},
                               self.sha, run, 'selected stop')

    def test_reopen_export_input_notes_partial_and_compare(self):
        raw = self.root / 'input.bin'; raw.write_bytes(b'\x00\xffowned\n')
        ex.add_input(self.path, raw, 'stdin candidate')
        a = self.snap(1); b = self.snap(2)
        note = ex.add_note(self.path, 'Partial capture; remaining memory unknown', b)
        exported = self.root / 'export.json'
        ex.export(self.path, exported)
        self.assertEqual(ex.load(exported), ex.load(self.path))
        self.assertEqual(ex.load(exported)['notes'][0]['id'], note)
        difference = ex.compare(self.path, a, exported, b)
        self.assertTrue(difference['same_run'])
        self.assertEqual(difference['differences'][0]['section'], 'registers')
        # A fresh process reads the self-contained export, with no target or GDB.
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/ressembly-experiment.py'),
                                 'show', str(exported)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['snapshots'][1]['payload']['partial'], True)

    def test_incompatible_build_rejected_without_modification(self):
        old = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'incompatible build'):
            ex.add_snapshot(self.path, {}, '0' * 64, 'run', 'wrong build')
        self.assertEqual(self.path.read_bytes(), old)
        self.binary.write_bytes(b'different build')
        other = self.root / 'other.json'
        ex.create(other, self.binary, 'different')
        with self.assertRaisesRegex(ValueError, 'incompatible builds'):
            ex.compare(self.path, 'missing', other, 'missing')

    def test_missing_reference_and_integrity_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing snapshot'):
            ex.add_note(self.path, 'bad reference', 'missing')
        self.snap()
        data = ex.load(self.path)
        data['snapshots'][0]['payload']['registers']['rax'] = 9
        with self.assertRaisesRegex(ValueError, 'integrity'):
            ex.validate(data)

    def test_contradictory_context_identity_rejected_without_modification(self):
        original = self.path.read_bytes()
        for provenance in ('gdb_context', 'supplied_json'):
            for metadata in ({'executable_sha256': '0' * 64, 'run_id': 'run'},
                             {'executable_sha256': self.sha, 'run_id': 'different'}):
                with self.assertRaisesRegex(ValueError, 'contradicts'):
                    ex.add_snapshot(self.path, {'schema': 'ressembly.debug-context.v1',
                        'metadata': metadata}, self.sha, 'run', 'contradictory', provenance)
                self.assertEqual(self.path.read_bytes(), original)
        with self.assertRaisesRegex(ValueError, 'recognized context'):
            ex.add_snapshot(self.path, {}, self.sha, 'run', 'not a context', 'gdb_context')
        self.assertEqual(self.path.read_bytes(), original)

    def test_known_histories_cannot_bypass_build_or_run_checks(self):
        original = self.path.read_bytes()
        for schema in ('ressembly.object-history.v1', 'ressembly.object-history.v2', 'ressembly.marker-history.v1'):
            for metadata in ({'target_sha256': '0' * 64, 'run_id': 'run'},
                             {'target_sha256': self.sha, 'run_id': 'different'}, {}):
                with self.assertRaisesRegex(ValueError, 'contradicts'):
                    ex.add_snapshot(self.path, {'schema': schema, 'metadata': metadata},
                                    self.sha, 'run', 'wrong history')
                self.assertEqual(self.path.read_bytes(), original)
        ex.add_snapshot(self.path, {'schema': 'ressembly.object-history.v1', 'metadata': {
            'target_sha256': self.sha, 'run_id': 'run', 'acquisition_status': 'interrupted'}},
            self.sha, 'run', 'consistent partial history')
        self.assertEqual(ex.load(self.path)['snapshots'][0]['payload']['metadata']['acquisition_status'], 'interrupted')

    def test_no_overwrite_and_lock(self):
        with self.assertRaisesRegex(ValueError, 'already exists'):
            ex.create(self.path, self.binary, 'overwrite')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            ex.export(self.path, self.path)
        lock = self.path.with_name(self.path.name + '.lock'); lock.touch()
        with self.assertRaises(FileExistsError):
            self.snap()
        lock.unlink()
        link = self.root / 'link.json'; link.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            ex.add_note(link, 'overwrite')

    def test_limits_and_malformed_json(self):
        with self.assertRaisesRegex(ValueError, 'note'):
            ex.add_note(self.path, 'x' * 16385)
        with self.assertRaisesRegex(ValueError, 'budget'):
            ex.add_snapshot(self.path, {'blob': 'x' * ex.MAX_SNAPSHOT}, self.sha, 'run', 'too big')
        for content in ('{"schema":1,"schema":2}', '{"x":NaN}'):
            bad = self.root / 'bad.json'; bad.write_text(content)
            with self.assertRaises(ValueError):
                ex.read_json(bad)
        data = ex.load(self.path)
        data['inputs'] = [None] * (ex.MAX_RECORDS + 1)
        with self.assertRaisesRegex(ValueError, 'budget'):
            ex.validate(data)

    def test_different_runs_and_absent_vs_null(self):
        a = ex.add_snapshot(self.path, {'item': None}, self.sha, 'r1', 'one')
        b = ex.add_snapshot(self.path, {}, self.sha, 'r2', 'two')
        result = ex.compare(self.path, a, self.path, b)
        self.assertFalse(result['same_run'])
        self.assertTrue(result['differences'][0]['left_present'])
        self.assertFalse(result['differences'][0]['right_present'])

    def test_process_identity_and_capture_identity_are_incomparable(self):
        a = ex.add_snapshot(self.path, {'schema': 'ressembly.debug-context.v1', 'metadata': {
            'executable_sha256': self.sha, 'run_id': 'boot:pid:start'}},
            self.sha, 'boot:pid:start', 'context')
        b = ex.add_snapshot(self.path, {'schema': 'ressembly.object-history.v1', 'metadata': {
            'target_sha256': self.sha, 'run_id': 'capture-uuid'}},
            self.sha, 'capture-uuid', 'history')
        result = ex.compare(self.path, a, self.path, b)
        self.assertIsNone(result['same_run'])
        self.assertEqual(result['run_identity_relation'], 'different_identity_domains')


if __name__ == '__main__':
    unittest.main()
