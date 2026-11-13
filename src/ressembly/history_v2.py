"""Opt-in allocator transactions and bounded independent observation windows."""
import copy
from .lifetime import Lifetime, EventBudget


class History(Lifetime):
    def __init__(self, metadata, event_limit=1000, region_limit=4):
        super().__init__(metadata, event_limit)
        if type(region_limit) is not int or not 1 <= region_limit <= 4:
            raise ValueError('region limit must be 1..4')
        self.region_limit = region_limit
        self.observing = {}

    def calloc(self, address, count, element_size, context=None):
        if any(type(value) is not int or not 0 <= value < 2**64 for value in (address, count, element_size)):
            raise ValueError('calloc arguments must be uint64')
        total = count * element_size
        ctx = dict(context or {}, operation='calloc', count=count, element_size=element_size,
                   mathematical_size=total, size_t_overflow=total >= 2 ** 64)
        if address == 0:
            return self.emit('allocation_failed', ctx, address=0, requested_size=total, object_id=None)
        if total >= 2 ** 64:
            raise ValueError('non-null calloc return for overflowing size is inconsistent')
        return self.allocate(address, total, ctx)

    def begin_realloc(self, address, size, context=None):
        if any(type(value) is not int or not 0 <= value < 2**64 for value in (address, size)):
            raise ValueError('realloc arguments must be uint64')
        oid = self.active.get(address)
        event = self.emit('realloc_begin', context, address=address, requested_size=size, object_id=oid)
        if oid:
            self.objects[oid]['state'] = 'realloc_pending'
        return event

    def finish_realloc(self, old_address, result, size, context=None):
        if any(type(value) is not int or not 0 <= value < 2**64 for value in (old_address, result, size)):
            raise ValueError('realloc arguments must be uint64')
        oid = self.active.get(old_address)
        if old_address == 0:
            return self.allocate(result, size, dict(context or {}, operation='realloc_null'))
        if result == 0 and size != 0:
            event = self.emit('realloc_failed', context, address=old_address, requested_size=size, object_id=oid)
            if oid:
                self.objects[oid]['state'] = 'live'
            return event
        # Explicit glibc policy: realloc(nonnull, 0) frees and returns NULL.
        if size == 0 and result != 0:
            raise ValueError('unexpected zero-size realloc result for glibc profile')
        if result and result in self.active and result != old_address:
            raise ValueError('realloc result overlaps another live allocation')
        if result:
            # Reserve both events before mutating identity state.
            if len(self.events) + 2 > self.limit:
                self.metadata['acquisition_status'] = 'event_limit_reached'
                raise EventBudget('event budget reached before realloc transaction commit')
        event = self.emit('realloc_zero_free' if size == 0 else 'realloc_replaced', context,
                          address=old_address, result_address=result, requested_size=size, object_id=oid)
        if oid:
            self.objects[oid].update(state='freed' if size == 0 else 'replaced',
                                     end_sequence=event['sequence'])
            del self.active[old_address]
        if result:
            new = self.allocate(result, size, dict(context or {}, operation='realloc', predecessor=oid))
            self.objects[new['object_id']]['predecessor'] = oid
            if oid:
                self.objects[oid]['successor'] = new['object_id']
            event['successor'] = new['object_id']
        return event

    def select_region(self, oid, offset, width):
        # Reuse the established bounds/alignment checks; v1's sole watch stays None.
        address = super().select_region(oid, offset, width)
        if len(self.observing) >= self.region_limit:
            raise ValueError('selected region limit reached')
        if any(address < w['address'] + w['width'] and w['address'] < address + width
               for w in self.observing.values()):
            raise ValueError('overlapping observation regions are not supported')
        return address

    def request_region(self, oid, offset, width, initial, context=None):
        address = self.select_region(oid, offset, width)
        if len(initial) != width:
            raise ValueError('initial region read failed or has wrong length')
        wid = 'window-' + str(len(self.windows) + 1)
        event = self.emit('watch_requested', context, window_id=wid, object_id=oid,
                          address=address, width=width, baseline_hex=bytes(initial).hex())
        window = dict(id=wid, object_id=oid, address=address, width=width, state='pending',
                      requested_sequence=event['sequence'], last_hex=bytes(initial).hex())
        self.windows.append(window)
        self.observing[wid] = window
        return window

    def activate_regions(self, context=None):
        for window in self.observing.values():
            if window['state'] == 'pending':
                event = self.emit('watch_active', context, window_id=window['id'],
                                  object_id=window['object_id'], address=window['address'])
                window.update(state='active', active_sequence=event['sequence'])

    def change(self, wid, data, context=None):
        window = self.observing.get(wid)
        if window is None or window['state'] != 'active' or len(data) != window['width']:
            raise ValueError('invalid or inactive observation window')
        current = bytes(data).hex()
        event = self.emit('value_change' if current != window['last_hex'] else 'watch_stop_without_value_change',
            context, window_id=wid, object_id=window['object_id'], address=window['address'],
            width=window['width'], previous_hex=window['last_hex'], observed_hex=current,
            pc_semantics='stop_pc_after_instruction; writer_instruction_unknown')
        window['last_hex'] = current
        return event

    def end_regions(self, oid, reason, context=None):
        ended = []
        for wid, window in list(self.observing.items()):
            if window['object_id'] != oid:
                continue
            event = self.emit('watch_end', context, window_id=wid, object_id=oid,
                              address=window['address'], reason=reason)
            window.update(state='ended', end_sequence=event['sequence'], end_reason=reason)
            del self.observing[wid]
            ended.append(wid)
        return ended

    def close(self, status, reason):
        super().close(status, reason)
        for window in self.observing.values():
            window.update(state='ended', end_reason=reason, end_sequence=None)
        self.observing.clear()
        for obj in self.objects.values():
            if obj['state'] == 'realloc_pending':
                obj['state'] = 'unknown_after_incomplete_realloc'

    def export(self):
        return copy.deepcopy(dict(schema='ressembly.object-history.v2', metadata=self.metadata,
            coverage=dict(mode='top_level_selected_glibc_calls_and_regions', event_limit=self.limit,
                          region_limit=self.region_limit, all_allocator_calls=False, all_writes=False,
                          same_value_writes_observed=False, watched_value_changes_only=True,
                          nested_allocator_calls_observed=False, windows=self.windows,
                          unsupported=['threads', 'fork', 'attach', 'other_allocators', 'reallocarray',
                                       'aligned_alloc', 'nested_or_reentrant_allocator_calls']),
            objects=self.objects, events=self.events))
