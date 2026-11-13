"""Bounded allocation generations and explicit, partial observation windows."""
import copy


class EventBudget(ValueError):
    pass


class Lifetime:
    def __init__(self, metadata, event_limit=1000):
        if type(event_limit) is not int or not 1 <= event_limit <= 10000:
            raise ValueError('event limit must be 1..10000')
        self.metadata = dict(metadata, acquisition_status='collecting')
        self.limit = event_limit
        self.events, self.objects, self.active, self.generations = [], {}, {}, {}
        self.windows, self.watch = [], None

    def emit(self, kind, context=None, **fields):
        if len(self.events) >= self.limit:
            self.metadata['acquisition_status'] = 'event_limit_reached'
            raise EventBudget('event budget reached; later observations are missing')
        event = dict(context or {})
        event.update(fields, sequence=len(self.events) + 1, kind=kind)
        self.events.append(event)
        return event

    def allocate(self, address, size, context=None):
        if type(address) is not int or not 0 <= address < 2 ** 64:
            raise ValueError('invalid allocation address')
        if type(size) is not int or not 0 <= size < 2 ** 64:
            raise ValueError('invalid allocation size')
        if address == 0:
            return self.emit('allocation_failed', context, address=0, requested_size=size, object_id=None)
        if address in self.active:
            raise ValueError('allocation address is already live; missing or unsupported allocator operation')
        generation = self.generations.get(address, 0) + 1
        oid = '%x:%d' % (address, generation)
        event = self.emit('allocation', context, address=address, requested_size=size, object_id=oid)
        self.generations[address] = generation
        self.active[address] = oid
        self.objects[oid] = dict(address=address, size=size, generation=generation, state='live',
                                 allocation_sequence=event['sequence'])
        return event

    def begin_free(self, address, context=None):
        oid = self.active.get(address)
        if oid:
            self.objects[oid]['state'] = 'free_pending'
        return self.emit('free_begin', context, address=address, object_id=oid)

    def finish_free(self, address, context=None):
        oid = self.active.get(address)
        kind = 'free_null' if address == 0 else 'free_return' if oid else 'unmatched_free'
        event = self.emit(kind, context, address=address, object_id=oid)
        if oid:
            self.objects[oid]['state'] = 'freed'
            self.objects[oid]['free_sequence'] = event['sequence']
            del self.active[address]
        return event

    def select_region(self, oid, offset, width):
        if oid not in self.objects or self.objects[oid]['state'] != 'live':
            raise ValueError('watch requires a live object identity')
        if type(offset) is not int or offset < 0 or type(width) is not int or width not in (1, 2, 4, 8):
            raise ValueError('offset >=0 and width in 1,2,4,8 required')
        obj = self.objects[oid]
        if offset + width > obj['size']:
            raise ValueError('selected region exceeds the requested allocation')
        address = obj['address'] + offset
        if address % width:
            raise ValueError('region must be naturally aligned')
        if self.watch is not None:
            raise ValueError('only one own observation region is allowed')
        return address

    def request_watch(self, oid, offset, width, initial, context=None):
        address = self.select_region(oid, offset, width)
        if len(initial) != width:
            raise ValueError('initial region read failed or has wrong length')
        event = self.emit('watch_requested', context, object_id=oid, address=address, width=width,
                          baseline_hex=bytes(initial).hex())
        window = dict(id='window-' + str(len(self.windows) + 1), object_id=oid, address=address,
                      width=width, state='pending', requested_sequence=event['sequence'],
                      last_hex=bytes(initial).hex())
        self.windows.append(window)
        self.watch = window
        return window

    def activate_watch(self, context=None):
        if self.watch is not None and self.watch['state'] == 'pending':
            event = self.emit('watch_active', context, window_id=self.watch['id'],
                              object_id=self.watch['object_id'], address=self.watch['address'])
            self.watch.update(state='active', active_sequence=event['sequence'])

    def value_change(self, data, context=None):
        window = self.watch
        if window is None or window['state'] != 'active':
            raise ValueError('watch stop without an active observation window')
        if len(data) != window['width']:
            raise ValueError('watch region read failed or has wrong length')
        current = bytes(data).hex()
        changed = current != window['last_hex']
        event = self.emit('value_change' if changed else 'watch_stop_without_value_change', context,
                          window_id=window['id'], object_id=window['object_id'],
                          address=window['address'], width=window['width'],
                          previous_hex=window['last_hex'], observed_hex=current,
                          pc_semantics='stop_pc_after_instruction; writer_instruction_unknown')
        window['last_hex'] = current
        return event

    def end_watch(self, reason, context=None):
        if self.watch is not None:
            window = self.watch
            event = self.emit('watch_end', context, window_id=window['id'],
                              object_id=window['object_id'], address=window['address'], reason=reason)
            window.update(state='ended', end_sequence=event['sequence'], end_reason=reason)
            self.watch = None

    def close(self, status, reason):
        self.metadata.update(acquisition_status=status, end_reason=reason)
        if self.watch is not None:
            self.watch.update(state='ended', end_reason=reason, end_sequence=None)
            self.watch = None
        for obj in self.objects.values():
            if obj['state'] == 'free_pending':
                obj['state'] = 'unknown_after_incomplete_free'

    def export(self):
        return copy.deepcopy(dict(schema='ressembly.object-history.v1', metadata=self.metadata,
            coverage=dict(mode='selected_glibc_malloc_free_and_one_region', event_limit=self.limit,
                          all_allocator_calls=False, all_writes=False, same_value_writes_observed=False,
                          watched_value_changes_only=True, windows=self.windows,
                          unsupported=['calloc', 'realloc', 'threads', 'fork', 'attach', 'other_allocators']),
            objects=self.objects, events=self.events))

    def render(self):
        lines = ['Ressembly object history: selected calls and partial value-change coverage.']
        for event in self.events:
            lines.append('#{} {} object={} address={} stop_pc={}'.format(
                event['sequence'], event['kind'], event.get('object_id'),
                hex(event['address']) if type(event.get('address')) is int else '?', event.get('pc', '?')))
        return '\n'.join(lines)
