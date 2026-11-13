"""Narrow GDB/SysV AMD64 profiled glibc adapter; no debugger plugins required."""
import atexit
import hashlib
import json
import os
import platform
import shlex
import subprocess
import tempfile
import uuid
import gdb
from .lifetime import Lifetime, EventBudget
from .allocator_profiles import banner_version, profile

_session = None


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def loaded_version(libc_path):
    """Prefer the loaded module version; executing it may select another loader."""
    symbol = gdb.lookup_static_symbol('__libc_version')
    if symbol is not None:
        if symbol.symtab is None:
            raise ValueError('libc version symbol has no verifiable module ownership')
        owner = symbol.symtab.objfile
        while owner.owner is not None:
            owner = owner.owner
        if os.path.realpath(owner.filename) != os.path.realpath(libc_path):
            raise ValueError('libc version debug symbol belongs to another module')
        value = symbol.value()
        if not 1 <= value.type.sizeof <= 32:
            raise ValueError('unsupported libc version debug array size')
        version = value.string(length=value.type.sizeof).split('\x00', 1)[0]
        profile(version)
        return version, 'loaded __libc_version='+version, 'matching_debug_symbol'
    banner = subprocess.run([libc_path], capture_output=True, text=True, timeout=10, check=True).stdout
    return banner_version(banner), banner.splitlines()[0], 'executed_loaded_libc_banner'


def context(source):
    thread = gdb.selected_thread()
    return dict(thread=thread.global_num if thread is not None else None,
                pc=hex(int(gdb.parse_and_eval('$pc'))), provenance=source, abi='sysv-amd64')


def available_context(source):
    try:
        return context(source)
    except gdb.error:
        return dict(provenance=source, thread=None, pc=None, context_unavailable=True)


class Entry(gdb.Breakpoint):
    def __init__(self, address, operation):
        super().__init__('*' + hex(address), internal=True)
        self.operation = operation

    def stop(self):
        return True


class FinishReturn(gdb.FinishBreakpoint):
    def __init__(self, session):
        super().__init__(gdb.newest_frame(), internal=True)
        self.session = session

    def stop(self):
        return True

    def out_of_scope(self):
        # No breakpoint/execution mutations inside this callback.
        self.session.lost_return = True


class LogicalReturn(gdb.Breakpoint):
    """2.43 allocator tail calls can remove the original GDB finish frame."""
    def __init__(self, session):
        frame = gdb.newest_frame()
        caller = frame.older()
        if caller is None:
            raise ValueError('allocator caller return site is unavailable')
        address = int(caller.pc())
        self.expected_rsp = int(frame.read_register('rsp')) + 8
        session.pending['caller_return_pc'] = address
        super().__init__('*'+hex(address), internal=True)

    def stop(self):
        # Observe the matching ABI return, not a recursive use of the same PC.
        return int(gdb.newest_frame().read_register('rsp')) == self.expected_rsp


def Return(session):
    return LogicalReturn(session) if session.top_level_only else FinishReturn(session)


class Session:
    def __init__(self, output, limit):
        if platform.system() != 'Linux' or platform.machine() != 'x86_64':
            raise ValueError('requires Linux x86-64')
        inferior = gdb.selected_inferior()
        if not inferior.pid or inferior.was_attached or len(inferior.threads()) != 1:
            raise ValueError('requires one launched single-thread inferior stopped in the owned lab')
        if gdb.newest_frame().architecture().name() != 'i386:x86-64':
            raise ValueError('requires SysV AMD64 architecture')
        self.pid, self.inferior_number = inferior.pid, inferior.num
        self.target = os.path.realpath(gdb.current_progspace().filename)
        self.addresses = {op: int(gdb.parse_and_eval('&__libc_' + op)) for op in ('malloc', 'free', 'calloc', 'realloc')}
        libc_path = gdb.solib_name(self.addresses['malloc'])
        if not libc_path:
            raise ValueError('cannot identify the loaded libc module')
        version, banner, version_probe = loaded_version(libc_path)
        allocator_profile = profile(version)
        self.top_level_only = version == '2.43'
        if any(os.path.realpath(gdb.solib_name(address) or '') != os.path.realpath(libc_path)
               for address in self.addresses.values()):
            raise ValueError('allocator entry points do not belong to the same loaded libc')
        self.output = os.path.abspath(output)
        self.model = Lifetime(dict(run_id=str(uuid.uuid4()), target=self.target,
            target_sha256=digest(self.target), host=platform.platform(), gdb_version=gdb.VERSION,
            glibc_version=version, allocator_profile=allocator_profile['id'], libc_path=libc_path, libc_sha256=digest(libc_path),
            libc_banner=banner, version_probe=version_probe,
            return_observation='caller_pc_and_sysv_rsp' if self.top_level_only else 'gdb_finish_breakpoint', process_id=self.pid, inferior_number=self.inferior_number,
            collector='selected __libc_malloc/__libc_free entry and return', process_status='stopped'), limit)
        if self.top_level_only:
            self.model.metadata.update(collector='top-level selected __libc_malloc/__libc_free entry and return',
                nested_calls='entry hooks disabled until outer return; nested/reentrant calls unobserved')
        self.hooks, self.return_bp, self.watch_bp = [], None, None
        self.pending, self.lost_return, self.closed, self.own_stop = None, False, False, False
        descriptor = os.open(self.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            self.hooks = [Entry(address, op) for op, address in self.addresses.items()]
            self.save()
        except Exception:
            self.cleanup()
            os.unlink(self.output)
            raise

    def save(self):
        descriptor, temporary = tempfile.mkstemp(prefix='.ressembly-heap-', dir=os.path.dirname(self.output))
        try:
            with os.fdopen(descriptor, 'w') as stream:
                json.dump(self.model.export(), stream, indent=2)
                stream.write('\n')
            os.replace(temporary, self.output)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def cleanup(self):
        for breakpoint in self.hooks + [self.return_bp, self.watch_bp]:
            if breakpoint is not None and breakpoint.is_valid():
                breakpoint.delete()
        self.return_bp, self.watch_bp = None, None

    def guard(self, allow_return=False, check_frames=True):
        inferior = gdb.selected_inferior()
        if inferior.num != self.inferior_number or inferior.pid != self.pid:
            raise ValueError('inferior/process changed; captures cannot span runs')
        if len(inferior.threads()) != 1:
            raise ValueError('multi-thread acquisition unsupported')
        target = gdb.current_progspace().filename
        if not target or os.path.realpath(target) != self.target:
            raise ValueError('target changed')
        if self.lost_return:
            raise ValueError('allocator return went out of scope; operation outcome unknown')
        if self.pending is not None and check_frames and not allow_return:
            frame, found = gdb.newest_frame(), False
            for _ in range(64):
                if frame is None:
                    break
                older = frame.older()
                if ((self.top_level_only and older is not None
                     and int(older.pc()) == self.pending['caller_return_pc'])
                        or (not self.top_level_only and frame.name() == self.pending['frame_name'])):
                    found = True
                    break
                frame = frame.older()
            if not found:
                raise ValueError('allocator frame left before observed return; operation outcome unknown')

    def close(self, status, reason, process_status=None):
        if self.closed:
            return
        if self.pending is not None:
            try:
                self.model.emit('call_incomplete', available_context('gdb_finish_scope'),
                                operation=self.pending['operation'], address=self.pending.get('address'))
            except EventBudget:
                status = 'event_limit_reached'
        self.model.close(status, reason)
        if process_status is not None:
            self.model.metadata['process_status'] = process_status
        self.closed = True
        self.cleanup()
        self.save()

    def failure(self, error):
        status = 'event_limit_reached' if isinstance(error, EventBudget) else 'error'
        self.model.metadata['last_error'] = str(error)
        try:
            self.model.emit('acquisition_error', available_context('gdb_adapter'), error=str(error))
        except EventBudget:
            status = 'event_limit_reached'
        self.close(status, str(error))
        gdb.write('Ressembly heap collection stopped: ' + str(error) + '\n')

    def entry(self, breakpoint):
        if breakpoint.operation in ('calloc', 'realloc'):
            raise ValueError('unsupported allocator call rejected before execution: ' + breakpoint.operation)
        if self.pending is not None:
            raise ValueError('nested allocator call unsupported')
        value = int(gdb.parse_and_eval('$rdi')) & ((1 << 64) - 1)
        ctx = context('glibc_entry_breakpoint')
        self.pending = dict(operation=breakpoint.operation, entry_pc=ctx['pc'],
                            frame_name=gdb.newest_frame().name())
        if breakpoint.operation == 'malloc':
            self.pending['size'] = value
            self.model.emit('malloc_begin', ctx, requested_size=value)
        else:
            self.pending['address'] = value
            oid = self.model.active.get(value)
            if self.model.watch is not None and self.model.watch['object_id'] == oid:
                self.model.end_watch('free_entry', ctx)
                self.watch_bp.delete()
                self.watch_bp = None
            self.model.begin_free(value, ctx)
        # This method is called from events.stop, never from Breakpoint.stop.
        self.return_bp = Return(self)
        if self.top_level_only:
            # 2.43 lazy tcache initialization recursively enters __libc_free.
            # Represent the outer operation once, with explicit nested coverage gaps.
            for hook in self.hooks:
                hook.enabled = False

    def returned(self):
        call = self.pending
        if call is None:
            raise ValueError('return stop without an allocator call')
        ctx = context('glibc_return_breakpoint')
        ctx['entry_pc'] = call['entry_pc']
        if call['operation'] == 'malloc':
            self.model.allocate(int(gdb.parse_and_eval('$rax')) & ((1 << 64) - 1), call['size'], ctx)
        else:
            self.model.finish_free(call['address'], ctx)
        if self.return_bp is not None and self.return_bp.is_valid():
            self.return_bp.delete()
        self.pending, self.return_bp = None, None
        if self.top_level_only:
            for hook in self.hooks:
                hook.enabled = True

    def stopped(self, event):
        self.own_stop = False
        if self.closed:
            return
        try:
            breakpoints = list(getattr(event, 'breakpoints', ()))
            self.guard(allow_return=self.return_bp is not None and self.return_bp in breakpoints)
            self.model.metadata['process_status'] = 'stopped'
            if isinstance(event, gdb.SignalEvent):
                self.model.metadata.update(process_status='signal_stop', stop_signal=event.stop_signal)
                self.model.metadata['acquisition_status'] = 'interrupted'
                self.save()
                return
            owned = [bp for bp in breakpoints if bp in self.hooks or bp is self.return_bp or bp is self.watch_bp]
            # A successfully reached stop establishes that hardware insertion did
            # not fail. Never claim activation merely from construction/.type.
            self.model.activate_watch(context('successful_resume_observed_at_stop'))
            for breakpoint in owned:
                if breakpoint in self.hooks:
                    self.entry(breakpoint)
                elif breakpoint is self.return_bp:
                    self.returned()
                elif breakpoint is self.watch_bp:
                    window = self.model.watch
                    data = bytes(gdb.selected_inferior().read_memory(window['address'], window['width']))
                    self.model.value_change(data, context('gdb_hardware_value_watchpoint'))
            self.own_stop = bool(owned) and len(owned) == len(breakpoints)
            self.save()
        except Exception as exc:
            self.failure(exc)

    def watch(self, oid, offset, width):
        self.guard()
        address = self.model.select_region(oid, offset, width)
        initial = bytes(gdb.selected_inferior().read_memory(address, width))
        types = {1: 'unsigned char', 2: 'unsigned short', 4: 'unsigned int', 8: 'unsigned long long'}
        breakpoint = gdb.Breakpoint('*({}*){}'.format(types[width], hex(address)),
                                    type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE, internal=True)
        if breakpoint.type != gdb.BP_HARDWARE_WATCHPOINT:
            breakpoint.delete()
            raise ValueError('hardware watchpoint unavailable; software fallback refused')
        try:
            self.model.request_watch(oid, offset, width, initial, context('explicit_region_selection'))
        except Exception:
            breakpoint.delete()
            raise
        self.watch_bp = breakpoint
        self.save()

    def resume(self):
        if self.closed:
            raise ValueError('capture closed; start a new GDB session')
        try:
            self.guard()
            if digest(self.target) != self.model.metadata['target_sha256']:
                raise ValueError('target build changed')
            self.model.metadata['acquisition_status'] = 'collecting'
            while not self.closed:
                self.own_stop = False
                gdb.execute('continue')
                if not self.own_stop:
                    break
        except Exception as exc:
            self.failure(exc)
            raise gdb.GdbError(str(exc))


class Command(gdb.Command):
    def __init__(self, name, action):
        super().__init__(name, gdb.COMMAND_USER)
        self.action = action

    def invoke(self, argument, from_tty):
        global _session
        try:
            args = shlex.split(argument)
            if self.action == 'start':
                if getattr(gdb, '_ressembly_history_capture_started', False):
                    raise ValueError('use a fresh GDB session; extended history has already started')
                if _session is not None:
                    raise ValueError('one capture per GDB session')
                if len(args) not in (1, 2):
                    raise ValueError('Usage: rsheap-start OUTPUT.json [EVENT_LIMIT]')
                limit = int(args[1]) if len(args) == 2 else 1000
                _session = Session(args[0], limit)
            else:
                if _session is None:
                    raise ValueError('rsheap-start is required')
                if self.action == 'watch':
                    if len(args) != 3:
                        raise ValueError('Usage: rsheap-watch OBJECT_ID OFFSET WIDTH')
                    if _session.closed:
                        raise ValueError('capture is closed')
                    _session.watch(args[0], int(args[1]), int(args[2]))
                elif args:
                    raise ValueError('this command takes no arguments')
                elif self.action == 'continue':
                    _session.resume()
                elif self.action == 'show':
                    gdb.write(_session.model.render() + '\n')
                elif self.action == 'save':
                    _session.save()
                elif self.action == 'stop':
                    _session.close('interrupted', 'explicit_stop')
        except EventBudget as exc:
            if _session is not None and not _session.closed:
                _session.failure(exc)
            raise gdb.GdbError(str(exc))
        except (ValueError, OSError, gdb.error) as exc:
            if self.action == 'watch' and _session is not None:
                _session.model.metadata['last_command_error'] = str(exc)
                _session.save()
            raise gdb.GdbError(str(exc))


def stopped(event):
    if _session is not None:
        _session.stopped(event)


def continued(event):
    if _session is not None and not _session.closed:
        try:
            _session.guard(check_frames=False)
            _session.model.metadata['process_status'] = 'running'
        except Exception as exc:
            _session.failure(exc)


def exited(event):
    if _session is None or _session.closed:
        return
    if event.inferior.num != _session.inferior_number:
        _session.failure(ValueError('unexpected inferior exit'))
        return
    code = getattr(event, 'exit_code', None)
    _session.model.metadata['exit_code'] = code
    status = 'partial' if code is not None and _session.pending is None else 'interrupted'
    _session.close(status, 'process_exit' if code is not None else 'exit_status_unavailable',
                   process_status='exited' if code is not None else 'ended_without_exit_code')


def debugger_exit():
    if _session is not None and not _session.closed:
        try:
            _session.close('interrupted', 'debugger_exit', process_status='debugger_exit')
        except Exception as exc:
            gdb.write('Ressembly heap final save failed: ' + str(exc) + '\n')


def register():
    if __import__('sys').version_info < (3, 9):
        raise gdb.GdbError('Python 3.9+ required')
    for action in ('start', 'continue', 'watch', 'show', 'save', 'stop'):
        Command('rsheap-' + action, action)
    gdb.events.stop.connect(stopped)
    gdb.events.cont.connect(continued)
    gdb.events.exited.connect(exited)
    atexit.register(debugger_exit)
