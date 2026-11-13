"""Explicit markers describe allocator operations; snapshots never imply writes."""
import copy


class History:
    def __init__(self, metadata=None, snapshot_limit=64, event_limit=10000):
        if not isinstance(snapshot_limit, int) or snapshot_limit <= 0:
            raise ValueError('positive snapshot limit required')
        if not isinstance(event_limit, int) or event_limit <= 0:
            raise ValueError('positive event limit required')
        self.event_limit = event_limit
        self.limit = snapshot_limit
        self.metadata = dict(metadata or {})
        self.objects = {}
        self.active = {}
        self.generations = {}
        self.events = []
        self.samples = {}

    def record(self, kind, address, size=0, context=None, data=None):
        if len(self.events) >= self.event_limit:
            self.metadata['acquisition_status'] = 'event_limit_reached'
            raise ValueError('event limit reached; later events were not captured')
        if not isinstance(address, int) or address < 0 or not isinstance(size, int) or size < 0:
            raise ValueError('nonnegative integer address and size required')
        event = dict(context or {})
        event.update(sequence=len(self.events) + 1, kind=kind, address=address, size=size,
                     provenance='explicit_target_marker', object_id=None)
        oid = self.active.get(address)
        if kind == 'alloc':
            if address == 0:
                event['kind'] = 'allocation_failed'
            elif oid:
                event.update(kind='acquisition_error', error='allocation overlaps active identity')
            else:
                generation = self.generations.get(address, 0) + 1
                self.generations[address] = generation
                oid = '%x:%d' % (address, generation)
                self.active[address] = oid
                self.objects[oid] = dict(address=address, size=size, generation=generation, state='live')
                event['object_id'] = oid
        elif kind == 'free_completed':
            event['object_id'] = oid
            if address == 0:
                event['kind'] = 'free_null'
            elif not oid:
                event.update(kind='acquisition_error', error='free of unknown address')
            else:
                self.objects[oid]['state'] = 'freed'
                del self.active[address]
        elif kind == 'snapshot':
            event['object_id'] = oid
            if not oid:
                event.update(kind='acquisition_error', error='snapshot of unknown or freed address')
            else:
                expected = min(size, self.objects[oid]['size'], self.limit)
                event.update(requested_bytes=size, captured_bytes=0, truncated=expected < size)
                if data is None or len(data) != expected:
                    event.update(kind='acquisition_error', error='snapshot read failed or length mismatch')
                else:
                    previous = self.samples.get(oid)
                    event.update(bytes_hex=bytes(data).hex(), captured_bytes=expected,
                                 changed_offsets=None if previous is None else
                                 [i for i in range(min(len(previous), len(data))) if previous[i] != data[i]],
                                 compared_bytes=0 if previous is None else min(len(previous), len(data)))
                    self.samples[oid] = bytes(data)
        else:
            event.update(kind='acquisition_error', error='unsupported marker kind')
        self.events.append(event)
        return copy.deepcopy(event)

    def export(self):
        return copy.deepcopy(dict(schema='ressembly.marker-history.v1', metadata=self.metadata,
            coverage=dict(mode='explicit_markers_only', event_limit=self.event_limit, all_allocator_calls=False,
                          writes_observed=False, snapshot_limit=self.limit,
                          limitations=['Allocator events are target declarations, not independent hooks.',
                                       'Unmarked operations are absent.',
                                       'Byte differences only describe two samples; intervening writes are unknown.',
                                       'realloc, threads, custom allocators and arbitrary targets are unsupported.']),
            objects=self.objects, events=self.events))

    def render(self):
        lines = ['Ressembly: explicit markers; partial coverage; snapshots are not write events.']
        for e in self.events:
            lines.append('#{} {} address={} object={}'.format(e['sequence'], e['kind'],
                         hex(e['address']) if 'address' in e else '?', e.get('object_id')) +
                         (' changed=' + str(e['changed_offsets']) if 'changed_offsets' in e else '') +
                         (' error=' + e['error'] if 'error' in e else ''))
        return '\n'.join(lines)
