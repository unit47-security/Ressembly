"""Offline contracts; actual GDB is tested separately."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from ressembly.history_v2 import History,EventBudget

class HistoryTests(unittest.TestCase):
    def test_realloc_failed_inplace_moved_zero(self):
        m=History({}); oid=m.allocate(4096,32)['object_id']
        m.begin_realloc(4096,64); m.finish_realloc(4096,0,64)
        self.assertEqual(m.active[4096],oid); self.assertEqual(m.objects[oid]['size'],32)
        m.begin_realloc(4096,16); m.finish_realloc(4096,4096,16)
        second=m.active[4096]; self.assertNotEqual(oid,second); self.assertEqual(m.objects[oid]['state'],'replaced')
        m.begin_realloc(4096,128); m.finish_realloc(4096,8192,128)
        third=m.active[8192]; self.assertEqual(m.objects[third]['predecessor'],second)
        m.begin_realloc(8192,0); m.finish_realloc(8192,0,0)
        self.assertFalse(m.active); self.assertEqual(m.objects[third]['state'],'freed')

    def test_null_zero_calloc_overflow(self):
        m=History({})
        m.finish_realloc(0,4096,0)
        oid=m.active[4096]
        with self.assertRaises(ValueError): m.select_region(oid,0,1)
        event=m.calloc(0,2**64-1,2)
        self.assertEqual(event['kind'],'allocation_failed'); self.assertTrue(event['size_t_overflow'])
        with self.assertRaises(ValueError): m.calloc(8192,2**64-1,2)
        self.assertEqual(m.calloc(8192,4,8)['requested_size'],32)

    def test_four_windows_overlap_and_per_object_end(self):
        m=History({}); a=m.allocate(4096,32)['object_id']; b=m.allocate(8192,32)['object_id']
        ids=[m.request_region(a,i,1,b'\0')['id'] for i in (0,8)]
        ids += [m.request_region(b,i,1,b'\0')['id'] for i in (0,8)]
        with self.assertRaises(ValueError): m.request_region(b,16,1,b'\0')
        m.activate_regions(); m.change(ids[0],b'A'); m.change(ids[1],b'B')
        m.end_regions(a,'realloc_entry'); self.assertEqual(len(m.observing),2)
        m.begin_realloc(4096,64); m.finish_realloc(4096,0,64)
        self.assertEqual(len(m.observing),2)
        with self.assertRaises(ValueError): m.request_region(b,0,1,b'\0')
        m.request_region(a,0,1,b'A'); self.assertEqual(len(m.observing),3)

    def test_incomplete_and_budget_are_unknown(self):
        m=History({},event_limit=3); oid=m.allocate(4096,32)['object_id']; m.begin_realloc(4096,64)
        with self.assertRaises(EventBudget): m.finish_realloc(4096,8192,64)
        m.close('event_limit_reached','budget')
        self.assertEqual(m.objects[oid]['state'],'unknown_after_incomplete_realloc')
        self.assertNotIn(8192,m.active)

    def test_pending_not_active_and_snapshot_immutable(self):
        m=History({}); oid=m.allocate(4096,32)['object_id']; wid=m.request_region(oid,0,1,b'\0')['id']
        with self.assertRaises(ValueError): m.change(wid,b'A')
        m.close('error','hardware unavailable')
        self.assertNotIn('active_sequence',m.windows[0]); self.assertFalse(m.observing)
        export=m.export(); export['events'].clear(); self.assertTrue(m.events)
        self.assertEqual(export['schema'],'ressembly.object-history.v2')

if __name__=='__main__': unittest.main()
