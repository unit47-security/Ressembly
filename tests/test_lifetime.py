"""Offline core contract tests; no debugger/runtime claims."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ressembly.lifetime import Lifetime, EventBudget


class LifetimeTests(unittest.TestCase):
    def test_generations_failure_free_null_and_unknown(self):
        model = Lifetime({'run_id': 'synthetic'})
        first = model.allocate(4096, 32)['object_id']
        model.begin_free(4096)
        self.assertEqual(model.objects[first]['state'], 'free_pending')
        model.finish_free(4096)
        second = model.allocate(4096, 32)['object_id']
        self.assertNotEqual(first, second)
        self.assertEqual(model.objects[second]['generation'], 2)
        self.assertEqual(model.allocate(0, 2 ** 64 - 1)['kind'], 'allocation_failed')
        self.assertEqual(model.finish_free(0)['kind'], 'free_null')
        self.assertEqual(model.finish_free(8192)['kind'], 'unmatched_free')

    def test_watch_pending_active_changes_end_and_no_rebind(self):
        model = Lifetime({})
        oid = model.allocate(4096, 32)['object_id']
        model.request_watch(oid, 0, 1, b'\0')
        self.assertEqual(model.watch['state'], 'pending')
        with self.assertRaises(ValueError):
            model.value_change(b'A')
        model.activate_watch()
        self.assertEqual(model.value_change(b'A')['kind'], 'value_change')
        self.assertEqual(model.value_change(b'A')['kind'], 'watch_stop_without_value_change')
        model.end_watch('free_entry')
        model.begin_free(4096)
        model.finish_free(4096)
        model.allocate(4096, 32)
        self.assertIsNone(model.watch)
        self.assertEqual(model.windows[0]['end_reason'], 'free_entry')
        self.assertFalse(model.export()['coverage']['same_value_writes_observed'])

    def test_invalid_region_and_second_own_watch_rejected(self):
        model = Lifetime({})
        oid = model.allocate(4096, 8)['object_id']
        for offset, width in [(-1, 1), (8, 1), (1, 8), (0, 3), (True, 1)]:
            with self.assertRaises(ValueError):
                model.select_region(oid, offset, width)
        model.request_watch(oid, 0, 1, b'X')
        with self.assertRaises(ValueError):
            model.request_watch(oid, 1, 1, b'X')
        model.end_watch('test')
        model.begin_free(4096)
        with self.assertRaises(ValueError):
            model.select_region(oid, 0, 1)

    def test_budget_is_bounded_and_incomplete_free_is_unknown(self):
        model = Lifetime({}, event_limit=2)
        oid = model.allocate(4096, 8)['object_id']
        model.begin_free(4096)
        with self.assertRaises(EventBudget):
            model.finish_free(4096)
        model.close('event_limit_reached', 'budget')
        self.assertEqual(len(model.events), 2)
        self.assertEqual(model.objects[oid]['state'], 'unknown_after_incomplete_free')

    def test_export_immutable_and_overlapping_live_identity_rejected(self):
        model = Lifetime({})
        model.allocate(4096, 8)
        with self.assertRaises(ValueError):
            model.allocate(4096, 8)
        exported = model.export()
        exported['objects'].clear()
        self.assertEqual(len(model.objects), 1)


if __name__ == '__main__':
    unittest.main()
