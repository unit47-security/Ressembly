"""Unit tests with a fake GDB API. These are NOT Linux/debugger validation."""
import json
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class Registry:
    def __init__(self):
        self.handlers = []

    def connect(self, callback):
        self.handlers.append(callback)


class FakeGDB(types.ModuleType):
    class GdbError(Exception):
        pass

    class MemoryError(Exception):
        pass

    class SignalEvent:
        stop_signal = 'SIGUSR1'

    COMMAND_USER = 1
    VERSION = 'fake-offline-test'

    def __init__(self, target):
        super().__init__('gdb')
        self.commands, self.output = {}, []
        self.inferior = types.SimpleNamespace(num=1, pid=0, threads=lambda: [1],
                                              read_memory=lambda address, length: b'A' * length)
        self.progspace = types.SimpleNamespace(filename=str(target))
        self.events = types.SimpleNamespace(cont=Registry(), exited=Registry(), stop=Registry())
        owner = self

        class Command:
            def __init__(self, name, command_type):
                if name in owner.commands:
                    raise RuntimeError('duplicate command')
                owner.commands[name] = self

        class Breakpoint:
            pending = False

            def __init__(self, *args, **kwargs):
                self.valid = True

            def is_valid(self):
                return self.valid

            def delete(self):
                self.valid = False

        self.Command, self.Breakpoint = Command, Breakpoint
        self.values = dict(kind=1, ptr=4096, size=32)
        self.frame = types.SimpleNamespace(read_var=lambda key: self.values[key],
                                            pc=lambda: 0x401000, older=lambda: None)

    def selected_inferior(self):
        return self.inferior

    def current_progspace(self):
        return self.progspace

    def execute(self, command, to_string=False):
        if command != 'show architecture':
            raise RuntimeError('Fake test forbids execution mutations')
        return 'The target architecture is set to "auto" (currently "i386:x86-64").'

    def write(self, text):
        self.output.append(text)

    def newest_frame(self):
        return self.frame

    def selected_thread(self):
        return types.SimpleNamespace(global_num=1)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.target = self.directory / 'target'
        self.target.write_bytes(b'fake offline executable')
        self.output = self.directory / 'capture.json'
        self.gdb = FakeGDB(self.target)
        self.patchers = [patch.dict(sys.modules, {'gdb': self.gdb}),
                         patch('platform.system', return_value='Linux'),
                         patch('platform.machine', return_value='x86_64'),
                         patch('atexit.register')]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.api = runpy.run_path(str(ROOT / 'src/ressembly_gdb.py'))
        self.state = self.api['save'].__globals__

    def start(self, suffix=''):
        self.gdb.commands['rs-start'].invoke('"' + str(self.output) + '"' + suffix, False)
        self.gdb.inferior.pid = 123
        self.api['continued'](types.SimpleNamespace())

    def capture(self):
        return json.loads(self.output.read_text())

    def marker(self, kind, address=4096, size=32):
        self.gdb.values.update(kind=kind, ptr=address, size=size)
        return self.state['_breakpoint'].stop()

    def test_normal_event_persisted_and_followup_run_cannot_merge(self):
        self.start()
        self.assertFalse(self.marker(1))
        self.assertEqual(len(self.capture()['events']), 1)
        self.api['exited'](types.SimpleNamespace(inferior=self.gdb.inferior, exit_code=0))
        original = self.output.read_bytes()
        self.gdb.inferior.pid = 456
        self.api['continued'](types.SimpleNamespace())
        self.assertTrue(self.marker(1))
        self.api['exited'](types.SimpleNamespace(inferior=self.gdb.inferior, exit_code=0))
        self.assertEqual(self.output.read_bytes(), original)
        self.assertIn('REJECTED', ''.join(self.gdb.output))

    def test_target_build_changed_before_run_is_rejected(self):
        self.gdb.commands['rs-start'].invoke('"' + str(self.output) + '"', False)
        self.target.write_bytes(b'replaced offline fixture')
        self.gdb.inferior.pid = 123
        self.api['continued'](types.SimpleNamespace())
        self.assertEqual(self.capture()['metadata']['process_status'], 'context_changed')
        self.assertEqual(self.capture()['events'], [])
        self.assertTrue(self.marker(1))

    def test_read_failure_stops_without_inventing_bytes(self):
        self.start()
        self.marker(1)
        def unreadable(address, size):
            raise self.gdb.MemoryError('unmapped')
        self.gdb.inferior.read_memory = unreadable
        self.assertTrue(self.marker(3))
        capture = self.capture()
        self.assertEqual(capture['metadata']['acquisition_status'], 'error')
        self.assertEqual(capture['events'][-1]['kind'], 'acquisition_error')
        self.assertNotIn('bytes_hex', capture['events'][-1])

    def test_budget_exhaustion_is_bounded_and_preserved(self):
        self.start(' 1')
        self.marker(1)
        self.assertTrue(self.marker(3))
        capture = self.capture()
        self.assertEqual(len(capture['events']), 1)
        self.assertEqual(capture['metadata']['acquisition_status'], 'event_limit_reached')
        self.api['exited'](types.SimpleNamespace(inferior=self.gdb.inferior, exit_code=0))
        self.assertEqual(self.capture(), capture)

    def test_signal_stop_and_explicit_stop_are_partial(self):
        self.start()
        self.marker(1)
        self.api['stopped'](self.gdb.SignalEvent())
        self.assertEqual(self.capture()['metadata']['process_status'], 'signal_stop')
        self.gdb.commands['rs-stop'].invoke('', False)
        self.assertEqual(self.capture()['metadata']['acquisition_status'], 'interrupted')
        self.assertTrue(self.marker(3))
        self.assertEqual(len(self.capture()['events']), 1)

    def test_exit_without_code_is_not_normal_completion(self):
        self.start()
        self.api['exited'](types.SimpleNamespace(inferior=self.gdb.inferior))
        self.assertEqual(self.capture()['metadata']['process_status'], 'ended_without_exit_code')
        self.assertEqual(self.capture()['metadata']['acquisition_status'], 'interrupted')

    def test_context_change_or_new_thread_stops_collection(self):
        for change in ('pid', 'target', 'inferior', 'threads'):
            with self.subTest(change=change):
                # Each case uses a fresh acquisition in a freshly loaded fake session.
                self.setUp()
                self.start()
                if change == 'pid':
                    self.gdb.inferior.pid = 456
                elif change == 'target':
                    self.gdb.progspace.filename = str(self.directory / 'other')
                elif change == 'inferior':
                    self.gdb.inferior.num = 2
                else:
                    self.gdb.inferior.threads = lambda: [1, 2]
                self.assertTrue(self.marker(1))
                self.assertEqual(self.capture()['metadata']['acquisition_status'], 'error')

    def test_existing_capture_or_symlink_cannot_be_overwritten(self):
        self.output.write_text('preserve me')
        with self.assertRaises(self.gdb.GdbError):
            self.start()
        self.assertEqual(self.output.read_text(), 'preserve me')
        self.output.unlink()
        self.output.symlink_to(self.directory / 'missing')
        with self.assertRaises(self.gdb.GdbError):
            self.start()
        self.assertTrue(self.output.is_symlink())

    def test_already_running_target_and_invalid_limits_are_rejected(self):
        self.gdb.inferior.pid = 123
        with self.assertRaises(self.gdb.GdbError):
            self.start()
        self.gdb.inferior.pid = 0
        for limit in (' 0', ' 10001', ' bad'):
            with self.assertRaises(self.gdb.GdbError):
                self.start(limit)
        self.assertFalse(self.output.exists())

    def test_reload_guard_does_not_reset_active_capture(self):
        self.start()
        self.marker(1)
        with self.assertRaises(self.gdb.GdbError):
            runpy.run_path(str(ROOT / 'src/ressembly_gdb.py'))
        self.assertEqual(len(self.capture()['events']), 1)
        self.assertEqual(len(self.gdb.commands), 4)

    def test_debugger_exit_saves_partial_and_missing_marker_rolls_back(self):
        self.start()
        self.api['debugger_exit']()
        self.assertEqual(self.capture()['metadata']['process_status'], 'debugger_exit')
        self.assertEqual(self.capture()['metadata']['acquisition_status'], 'interrupted')
        self.setUp()
        self.gdb.Breakpoint.pending = True
        with self.assertRaises(self.gdb.GdbError):
            self.start()
        self.assertFalse(self.output.exists())
        self.assertIsNone(self.state['_history'])


if __name__ == '__main__':
    unittest.main()
