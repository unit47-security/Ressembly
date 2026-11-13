import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))
from ressembly.history import History


class HistoryTests(unittest.TestCase):
    def test_reuse_has_new_identity_and_no_cross_generation_diff(self):
        h = History()
        first = h.record('alloc', 4096, 4)['object_id']
        h.record('snapshot', 4096, 4, data=b'AAAA')
        h.record('free_completed', 4096)
        second = h.record('alloc', 4096, 4)['object_id']
        sample = h.record('snapshot', 4096, 4, data=b'BBBB')
        self.assertNotEqual(first, second)
        self.assertEqual(h.objects[first]['state'], 'freed')
        self.assertIsNone(sample['changed_offsets'])

    def test_failed_allocation_and_unknown_free_do_not_create_objects(self):
        h = History()
        self.assertEqual(h.record('alloc', 0, 99)['kind'], 'allocation_failed')
        self.assertEqual(h.record('free_completed', 13)['kind'], 'acquisition_error')
        self.assertEqual(h.record('free_completed', 0)['kind'], 'free_null')
        self.assertEqual(h.objects, {})

    def test_snapshot_limits_and_diff_are_samples_not_write_events(self):
        h = History(snapshot_limit=3)
        h.record('alloc', 5, 8)
        sample = bytearray(b'abc')
        h.record('snapshot', 5, 8, data=sample)
        sample[0] = 0
        e = h.record('snapshot', 5, 8, data=b'axc')
        self.assertEqual(e['changed_offsets'], [1])
        self.assertTrue(e['truncated'])
        self.assertEqual(e['captured_bytes'], 3)
        self.assertFalse(h.export()['coverage']['writes_observed'])
        self.assertEqual(h.events[1]['bytes_hex'], '616263')

    def test_failed_read_keeps_previous_valid_sample(self):
        h = History()
        h.record('alloc', 1, 2)
        h.record('snapshot', 1, 2, data=b'ab')
        self.assertEqual(h.record('snapshot', 1, 2)['kind'], 'acquisition_error')
        self.assertEqual(h.record('snapshot', 1, 2, data=b'ac')['changed_offsets'], [1])
        h.record('free_completed', 1)
        self.assertEqual(h.record('snapshot', 1, 2, data=b'ac')['kind'], 'acquisition_error')

    def test_duplicate_allocation_cannot_replace_live_object(self):
        h = History()
        oid = h.record('alloc', 1, 4)['object_id']
        self.assertEqual(h.record('alloc', 1, 8)['kind'], 'acquisition_error')
        self.assertEqual(h.active[1], oid)
        self.assertEqual(h.objects[oid]['size'], 4)

    def test_export_and_returned_events_cannot_mutate_history(self):
        h = History()
        e = h.record('alloc', 1, 4)
        e['kind'] = 'bad'
        exported = h.export()
        exported['objects']['1:1']['state'] = 'bad'
        self.assertEqual(h.events[0]['kind'], 'alloc')
        self.assertEqual(h.objects['1:1']['state'], 'live')

    def test_event_limit_is_explicit_and_bounded(self):
        h = History(event_limit=1)
        h.record('alloc', 1, 4)
        with self.assertRaises(ValueError):
            h.record('free_completed', 1)
        self.assertEqual(len(h.events), 1)
        self.assertEqual(h.metadata['acquisition_status'], 'event_limit_reached')

    def test_adapter_error_with_missing_context_renders(self):
        h = History()
        h.events.append(dict(sequence=1, kind='acquisition_error', error='missing frame'))
        self.assertIn('missing frame', h.render())

    def test_invalid_input_rejected_without_event(self):
        h = History()
        for address, size in [(-1, 4), (1, -1), ('1', 4)]:
            with self.assertRaises(ValueError):
                h.record('alloc', address, size)
        self.assertEqual(h.events, [])


if __name__ == '__main__':
    unittest.main()
