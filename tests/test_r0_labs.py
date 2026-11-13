"""Native controls and source contract only; not a Linux debugger comparison."""
from pathlib import Path
import runpy
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HARNESS = runpy.run_path(str(ROOT / 'scripts/r0/run.py'))


class R0LabsTests(unittest.TestCase):
    def test_control_and_defined_fault_outcomes(self):
        if not shutil.which('cc'):
            self.fail('C compiler required for owned lab validation')
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'memory_cases'
            compile_result = subprocess.run(['cc', '-std=c11', '-O0', '-g', '-Wall', '-Wextra',
                str(ROOT / 'examples/r0/memory_cases.c'), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            for case, mode, expected in [
                ('buffer', 'good', 'logical_sentinel_changed=0'),
                ('buffer', 'bad', 'logical_sentinel_changed=1'),
                ('pointer', 'good', 'selected_benign_function=1'),
                ('pointer', 'bad', 'selected_benign_function=2'),
                ('uaf', 'good', 'uaf_attempted=0')]:
                with self.subTest(case=case, mode=mode):
                    result = subprocess.run([str(binary), case, mode], text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(expected, result.stdout)
            for arguments in [[], ['unknown', 'good'], ['buffer', 'unknown']]:
                result = subprocess.run([str(binary), *arguments], capture_output=True)
                self.assertEqual(result.returncode, 64)
        # Deliberately do not run UAF fault natively or assert its undefined value.

    def test_profiles_do_not_claim_identical_capture_or_hide_commands(self):
        for tool, setup in [('gdb', None), ('gef', 'heap-analysis-helper'),
                            ('pwndbg', 'track-heap enable')]:
            commands = HARNESS['commands'](tool, Path('/tmp/lab with spaces'), 'uaf', 'bad',
                                            'manual' if tool == 'gdb' else 'helper')
            self.assertIn('file "/tmp/lab with spaces"', commands)
            self.assertIn('R0_CHECKPOINT=', commands)
            self.assertIn('R0_EXIT_CODES=', commands)
            self.assertIn('rs_length', commands)
            if setup:
                self.assertIn(setup, commands)
            else:
                self.assertNotIn('track-heap', commands)
                self.assertNotIn('heap-analysis-helper', commands)

    def test_manual_profiles_share_exact_watchpoints(self):
        for tool in ('gdb', 'gef', 'pwndbg'):
            for case, expected in [('buffer', 'rs_address+8'), ('uaf', 'rs_address+16'),
                                   ('pointer', 'unsigned long')]:
                script = HARNESS['commands'](tool, Path('/tmp/lab'), case, 'bad')
                self.assertIn(expected, script)
                self.assertIn('R0_WATCH_TRIGGER', script)
                self.assertIn('disable %d', script)
                self.assertNotIn('track-heap enable', script)
                self.assertNotIn('heap-analysis-helper', script)
        pwndbg_script = HARNESS['commands']('pwndbg', Path('/tmp/lab'), 'uaf', 'bad')
        self.assertIn('set gdb-workaround-stop-event disabled-deadlock', pwndbg_script)
        self.assertIn('pi gdb.execute("continue")', pwndbg_script)
        bad = HARNESS['commands']('gdb', Path('/tmp/lab'), 'uaf', 'bad')
        self.assertEqual(bad.count('tbreak rs_checkpoint'), 2)

    def test_runner_rejects_non_linux_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'must-not-exist'
            with mock.patch.object(HARNESS['platform'], 'system', return_value='Darwin'), \
                    mock.patch('sys.argv', ['run.py', '--out', str(output)]), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    HARNESS['main']()
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse(output.exists())

    def test_gdb_path_quoting_rejects_newlines(self):
        with self.assertRaises(ValueError):
            HARNESS['quoted']('/tmp/path\nrun')
        self.assertEqual(HARNESS['quoted']('/tmp/a"b'), '"/tmp/a\\"b"')


if __name__ == '__main__':
    unittest.main()
