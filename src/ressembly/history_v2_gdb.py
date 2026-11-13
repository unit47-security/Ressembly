"""Opt-in top-level transactions using the version-profiled base capture engine."""
import atexit
import os
import shlex
import gdb
from . import heap_gdb as base
from .history_v2 import History, EventBudget

_session = None


def reference(frame):
    if frame is None:
        return {'status': 'unavailable'}
    pc = int(frame.pc())
    result = {'address': hex(pc), 'function': frame.name(), 'source': None,
              'offset_semantics': 'file offset from current /proc mapping, not load-base RVA'}
    try:
        sal = gdb.find_pc_line(pc)
        if sal.symtab is not None and sal.line:
            result['source'] = {'file': sal.symtab.fullname(), 'line': sal.line}
        with open('/proc/%d/maps' % gdb.selected_inferior().pid) as stream:
            for line in stream:
                fields = line.rstrip().split(None, 5)
                lo, hi = (int(x, 16) for x in fields[0].split('-'))
                if lo <= pc < hi:
                    result.update(mapping_start=hex(lo), mapping_file_offset=int(fields[2], 16),
                                  offset_within_mapping=pc-lo,
                                  file_offset=(int(fields[2], 16)+pc-lo) if len(fields)>5 and fields[5].startswith('/') else None,
                                  module_path=fields[5] if len(fields)>5 else None)
                    break
    except (gdb.error, OSError, ValueError) as error:
        result['resolution_error'] = str(error)
    return result


def context(source):
    result = base.context(source)
    result['code'] = reference(gdb.newest_frame())
    return result


class Session(base.Session):
    def __init__(self, output, limit):
        inferior = gdb.selected_inferior()
        if inferior.connection is None or inferior.connection.type != 'native':
            raise ValueError('requires a local native GDB connection')
        if base._session is not None:
            raise ValueError('use a fresh GDB session; v1 collector has already started')
        self.regions = {}
        super().__init__(output, limit)
        try:
            self.model = History(dict(self.model.metadata,
                collector='top-level __libc_malloc/free/calloc/realloc entry and observed return',
                realloc_zero_policy='glibc_nonnull_zero_frees_and_returns_null',
                nested_calls='entry hooks disabled until outer return; nested/reentrant calls unobserved'), limit)
            self.save()
        except Exception:
            self.cleanup()
            os.unlink(self.output)
            raise

    def cleanup(self):
        for breakpoint in list(self.regions):
            if breakpoint.is_valid():
                breakpoint.delete()
        self.regions.clear()
        super().cleanup()

    def guard(self, allow_return=False, check_frames=True):
        super().guard(allow_return=allow_return, check_frames=False)
        if self.pending is not None and check_frames and not allow_return:
            frame, found = gdb.newest_frame(), False
            for _ in range(64):
                if frame is None:
                    break
                older = frame.older()
                if older is not None and int(older.pc()) == self.pending['caller_return_pc']:
                    found = True
                    break
                frame = older
            if not found:
                raise ValueError('allocator frame left before observed return; operation outcome unknown')

    def entry(self, breakpoint):
        if self.pending is not None:
            raise ValueError('unexpected allocator entry during pending transaction')
        frame = gdb.newest_frame()
        caller = frame.older()
        if caller is None:
            raise ValueError('allocator caller unavailable')
        arg1 = int(frame.read_register('rdi')) & ((1 << 64)-1)
        arg2 = int(frame.read_register('rsi')) & ((1 << 64)-1)
        ctx = context('glibc_entry_breakpoint')
        ctx['caller_return_site'] = reference(caller)
        op = breakpoint.operation
        self.pending = dict(operation=op, frame_name=frame.name(), entry_pc=ctx['pc'],
                            entry_code=ctx['code'], caller_return_site=ctx['caller_return_site'],
                            caller_return_pc=int(caller.pc()))
        if op in ('free', 'realloc'):
            self.pending['address'] = arg1
            oid = self.model.active.get(arg1)
            for wid in self.model.end_regions(oid, op+'_entry', ctx):
                for bp, identifier in list(self.regions.items()):
                    if identifier == wid:
                        bp.delete(); del self.regions[bp]
            if op == 'free':
                self.model.begin_free(arg1, ctx)
            else:
                self.pending['size'] = arg2
                self.model.begin_realloc(arg1, arg2, ctx)
        elif op == 'calloc':
            self.pending.update(count=arg1, element_size=arg2)
            self.model.emit('calloc_begin', ctx, count=arg1, element_size=arg2,
                            mathematical_size=arg1*arg2, size_t_overflow=arg1*arg2 >= 2**64)
        else:
            self.pending['size'] = arg1
            self.model.emit('malloc_begin', ctx, requested_size=arg1)
        self.return_bp = base.Return(self)
        # Only the outer transaction is represented. Internal realloc -> malloc/free
        # paths, and any reentrant calls while pending, are explicitly outside coverage.
        for hook in self.hooks:
            hook.enabled = False

    def returned(self):
        call = self.pending
        if call is None:
            raise ValueError('return stop without transaction')
        ctx = context('glibc_return_breakpoint')
        ctx.update(entry_pc=call['entry_pc'], entry_code=call['entry_code'],
                   caller_return_site=call['caller_return_site'])
        result = int(gdb.newest_frame().read_register('rax')) & ((1 << 64)-1)
        op = call['operation']
        if op == 'malloc':
            self.model.allocate(result, call['size'], dict(ctx, operation='malloc'))
        elif op == 'calloc':
            self.model.calloc(result, call['count'], call['element_size'], ctx)
        elif op == 'realloc':
            self.model.finish_realloc(call['address'], result, call['size'], ctx)
        else:
            self.model.finish_free(call['address'], ctx)
        if self.return_bp is not None and self.return_bp.is_valid():
            self.return_bp.delete()
        self.pending, self.return_bp = None, None
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
                self.model.metadata.update(process_status='signal_stop', stop_signal=event.stop_signal,
                                           acquisition_status='interrupted')
                self.save(); return
            owned = [bp for bp in breakpoints if bp in self.hooks or bp is self.return_bp or bp in self.regions]
            self.model.activate_regions(context('successful_resume_observed_at_stop'))
            for bp in owned:
                if bp in self.hooks:
                    self.entry(bp)
                elif bp is self.return_bp:
                    self.returned()
                elif bp in self.regions:
                    wid = self.regions[bp]
                    window = self.model.observing[wid]
                    data = bytes(gdb.selected_inferior().read_memory(window['address'], window['width']))
                    self.model.change(wid, data, context('gdb_hardware_value_watchpoint'))
            self.own_stop = bool(owned) and len(owned) == len(breakpoints)
            self.save()
        except Exception as error:
            self.failure(error)

    def watch(self, oid, offset, width):
        self.guard()
        address = self.model.select_region(oid, offset, width)
        initial = bytes(gdb.selected_inferior().read_memory(address, width))
        types = {1:'unsigned char', 2:'unsigned short', 4:'unsigned int', 8:'unsigned long long'}
        bp = gdb.Breakpoint('*({}*){}'.format(types[width], hex(address)),
                           type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE, internal=True)
        if bp.type != gdb.BP_HARDWARE_WATCHPOINT:
            bp.delete()
            raise ValueError('hardware watchpoint unavailable; software fallback refused')
        try:
            window = self.model.request_region(oid, offset, width, initial, context('explicit_region_selection'))
        except Exception:
            bp.delete(); raise
        self.regions[bp] = window['id']
        self.save()


class Command(gdb.Command):
    def __init__(self, action):
        super().__init__('rshist-'+action, gdb.COMMAND_USER)
        self.action = action

    def invoke(self, argument, from_tty):
        global _session
        self.dont_repeat()
        try:
            args = shlex.split(argument)
            if self.action == 'start':
                if _session is not None:
                    raise ValueError('one extended capture per GDB session')
                if len(args) not in (1,2):
                    raise ValueError('usage: rshist-start OUTPUT [EVENT_LIMIT]')
                _session = Session(args[0], int(args[1]) if len(args)==2 else 1000)
                gdb._ressembly_history_capture_started = True
            else:
                if _session is None:
                    raise ValueError('rshist-start required')
                if self.action == 'watch':
                    if len(args)!=3 or _session.closed:
                        raise ValueError('usage: rshist-watch LIVE_OBJECT_ID OFFSET WIDTH')
                    _session.watch(args[0],int(args[1]),int(args[2]))
                elif args:
                    raise ValueError('command takes no arguments')
                elif self.action == 'continue':
                    _session.resume()
                elif self.action == 'show':
                    gdb.write(_session.model.render()+'\n')
                elif self.action == 'save':
                    _session.save()
                elif self.action == 'stop':
                    _session.close('interrupted','explicit_stop')
        except EventBudget as error:
            if _session is not None and not _session.closed:
                _session.failure(error)
            raise gdb.GdbError(str(error))
        except (ValueError,OSError,gdb.error) as error:
            if _session is not None and self.action=='watch':
                _session.model.metadata['last_command_error']=str(error); _session.save()
            raise gdb.GdbError(str(error))


def stopped(event):
    if _session is not None:
        _session.stopped(event)


def continued(event):
    if _session is not None and not _session.closed:
        try:
            _session.guard(check_frames=False)
            _session.model.metadata['process_status']='running'
        except Exception as error:
            _session.failure(error)


def exited(event):
    if _session is None or _session.closed:
        return
    if event.inferior.num != _session.inferior_number:
        _session.failure(ValueError('unexpected inferior exit')); return
    code=getattr(event,'exit_code',None)
    _session.model.metadata['exit_code']=code
    _session.close('partial' if code is not None and _session.pending is None else 'interrupted',
                   'process_exit' if code is not None else 'exit_status_unavailable')


def register():
    for action in ('start','continue','watch','show','save','stop'):
        Command(action)
    gdb.events.stop.connect(stopped)
    gdb.events.cont.connect(continued)
    gdb.events.exited.connect(exited)
    def final_save():
        if _session is not None and not _session.closed:
            _session.close('interrupted','debugger_exit')
    atexit.register(final_save)
