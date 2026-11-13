"""Explicit-marker collector: one owned, single-thread Linux x86-64 run per GDB.

Callbacks read the inferior; they never change frames, execution or breakpoints.
"""
import atexit
import hashlib
import json
import os
import platform
import shlex
import sys
import tempfile
import uuid
import gdb

# Check before resetting module state when `source` is issued twice.
if getattr(gdb, '_ressembly_marker_loaded', False):
    raise gdb.GdbError('Ressembly is already loaded; use a new GDB session')
if sys.version_info < (3, 9):
    raise gdb.GdbError('Ressembly requires GDB Python 3.9 or newer')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ressembly.history import History

_history = None
_output = None
_breakpoint = None
_inferior_number = None
_pid = None
_closed = False


def save():
    if _history is None:
        raise gdb.GdbError('Run rs-start OUTPUT.json [EVENT_LIMIT] first')
    descriptor, temporary = tempfile.mkstemp(prefix='.ressembly-', suffix='.tmp',
                                            dir=os.path.dirname(_output))
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(_history.export(), stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, _output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def close_capture(status, process_status, error=None):
    global _closed
    _closed = True
    _history.metadata.update(acquisition_status=status, process_status=process_status)
    if error is not None:
        _history.metadata['last_error'] = str(error)
    save()


def scope_error():
    inferior = gdb.selected_inferior()
    target = gdb.current_progspace().filename
    if inferior.num != _inferior_number:
        return 'inferior changed; only one inferior is supported'
    if not target or os.path.realpath(target) != _history.metadata['target']:
        return 'target changed during acquisition'
    if _pid is not None and inferior.pid != _pid:
        return 'process changed; a new run requires a new GDB session'
    if len(inferior.threads()) != 1:
        return 'only a single-thread target is supported'
    return None


class Marker(gdb.Breakpoint):
    def stop(self):
        if _closed:
            gdb.write('Ressembly REJECTED follow-up run: capture is closed; start a new GDB session.\n')
            return True
        try:
            error = scope_error()
            if error:
                raise ValueError(error)
            frame = gdb.newest_frame()
            kind = int(frame.read_var('kind'))
            address = int(frame.read_var('ptr'))
            size = int(frame.read_var('size'))
            older = frame.older()
            context = dict(thread=gdb.selected_thread().global_num, pc=hex(frame.pc()),
                           source='rs_event', marker_kind=kind,
                           caller_pc=hex(older.pc()) if older is not None else None)
            data = None
            if kind == 3 and address in _history.active:
                oid = _history.active[address]
                length = min(size, _history.objects[oid]['size'], _history.limit)
                try:
                    data = bytes(gdb.selected_inferior().read_memory(address, length))
                    context['snapshot_provenance'] = 'gdb_inferior_read_memory'
                except gdb.MemoryError as exc:
                    context['read_error'] = str(exc)
            event = _history.record({1: 'alloc', 2: 'free_completed', 3: 'snapshot'}.get(kind, 'unknown'),
                                    address, size, context=context, data=data)
            if event['kind'] == 'acquisition_error':
                close_capture('error', 'collector_stopped', event['error'])
                return True
            save()
        except Exception as exc:
            if len(_history.events) < _history.event_limit:
                _history.events.append(dict(sequence=len(_history.events) + 1, kind='acquisition_error',
                                            error=str(exc), provenance='gdb_adapter'))
            status = ('event_limit_reached' if
                      _history.metadata.get('acquisition_status') == 'event_limit_reached' else 'error')
            close_capture(status, 'collector_stopped', exc)
            gdb.write('Ressembly collection stopped: ' + str(exc) + '\n')
            return True
        return False


class Start(gdb.Command):
    def __init__(self):
        super().__init__('rs-start', gdb.COMMAND_USER)

    def invoke(self, argument, from_tty):
        global _history, _output, _breakpoint, _inferior_number
        try:
            args = shlex.split(argument)
            if len(args) not in (1, 2):
                raise ValueError('Usage: rs-start OUTPUT.json [EVENT_LIMIT]')
            limit = int(args[1]) if len(args) == 2 else 10000
            if not 1 <= limit <= 10000:
                raise ValueError('EVENT_LIMIT must be between 1 and 10000')
            if _history is not None:
                raise ValueError('One acquisition per GDB session; start a new GDB session')
            inferior = gdb.selected_inferior()
            target = gdb.current_progspace().filename
            if not target or platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
                raise ValueError('Requires target loaded on Linux x86-64')
            if inferior.pid:
                raise ValueError('Start capture before run; attach and already running inferiors are unsupported')
            arch = gdb.execute('show architecture', to_string=True)
            if 'i386:x86-64' not in arch:
                raise ValueError('Target must be x86-64')
            target = os.path.realpath(target)
            with open(target, 'rb') as stream:
                digest = hashlib.sha256(stream.read()).hexdigest()
            output = os.path.abspath(args[0])
            # Exclusive reservation also rejects an existing symlink, including broken links.
            descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
        except (OSError, ValueError) as exc:
            raise gdb.GdbError(str(exc))
        try:
            _history = History(dict(run_id=str(uuid.uuid4()), target=target,
                target_sha256=digest, gdb_version=gdb.VERSION, host=platform.platform(),
                libc_host=platform.libc_ver(), architecture=arch.strip(),
                acquisition_status='collecting', process_status='not_started',
                inferior_number=inferior.num), event_limit=limit)
            _output, _inferior_number = output, inferior.num
            _breakpoint = Marker('rs_event', internal=True)
            if _breakpoint.pending:
                raise ValueError('rs_event marker is not resolved in this target')
            save()
        except Exception as exc:
            if _breakpoint is not None and _breakpoint.is_valid():
                _breakpoint.delete()
            _history, _output, _breakpoint = None, None, None
            os.unlink(output)
            raise gdb.GdbError('Cannot start capture: ' + str(exc))


class Show(gdb.Command):
    def __init__(self):
        super().__init__('rs-show', gdb.COMMAND_USER)

    def invoke(self, argument, from_tty):
        if _history is None:
            raise gdb.GdbError('Run rs-start first')
        gdb.write(_history.render() + '\n')


class Save(gdb.Command):
    def __init__(self):
        super().__init__('rs-save', gdb.COMMAND_USER)

    def invoke(self, argument, from_tty):
        save()


class Stop(gdb.Command):
    def __init__(self):
        super().__init__('rs-stop', gdb.COMMAND_USER)

    def invoke(self, argument, from_tty):
        if _history is None:
            raise gdb.GdbError('Run rs-start first')
        if not _closed:
            close_capture('interrupted', 'stopped_by_user')
        gdb.write('Ressembly capture closed; use a new GDB session for another acquisition.\n')


def continued(event):
    global _pid
    if _history is None:
        return
    if _closed:
        gdb.write('Ressembly REJECTED follow-up collection: closed capture is preserved.\n')
        return
    inferior = gdb.selected_inferior()
    if _pid is None and inferior.num == _inferior_number and inferior.pid:
        try:
            with open(_history.metadata['target'], 'rb') as stream:
                current_digest = hashlib.sha256(stream.read()).hexdigest()
            if current_digest != _history.metadata['target_sha256']:
                raise ValueError('target build changed after rs-start')
        except (OSError, ValueError) as exc:
            close_capture('error', 'context_changed', exc)
            return
        _pid = inferior.pid
        _history.metadata['process_id'] = _pid
    error = scope_error()
    if error:
        close_capture('error', 'context_changed', error)
    else:
        if _history.metadata['process_status'] == 'signal_stop':
            _history.metadata['acquisition_status'] = 'collecting'
        _history.metadata['process_status'] = 'running'


def exited(event):
    if _history is None or _closed or event.inferior.num != _inferior_number:
        return
    code = getattr(event, 'exit_code', None)
    _history.metadata['exit_code'] = code
    if code is None:
        close_capture('interrupted', 'ended_without_exit_code')
    else:
        close_capture('partial_marker_coverage', 'exited')


def stopped(event):
    if _history is None or _closed:
        return
    if isinstance(event, gdb.SignalEvent):
        _history.metadata.update(process_status='signal_stop', stop_signal=event.stop_signal,
                                 acquisition_status='interrupted')
    else:
        _history.metadata['process_status'] = 'stopped'
    save()


def debugger_exit():
    if _history is None:
        return
    try:
        if not _closed:
            close_capture('interrupted', 'debugger_exit')
        else:
            save()
    except Exception as exc:
        sys.stderr.write('Ressembly final save failed: ' + str(exc) + '\n')


Start()
Show()
Save()
Stop()
gdb.events.cont.connect(continued)
gdb.events.exited.connect(exited)
gdb.events.stop.connect(stopped)
atexit.register(debugger_exit)
gdb._ressembly_marker_loaded = True
