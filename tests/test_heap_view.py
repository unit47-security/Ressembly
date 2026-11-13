import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ressembly.heap_view import decode_header, require_profile, walk_chain


class HeapViewTests(unittest.TestCase):
    def test_profile_rejects_unknown(self):
        require_profile('2.36', 'i386:x86-64', 8)
        for profile in [('2.37', 'i386:x86-64', 8), ('2.36', 'aarch64', 8), ('2.36', 'i386:x86-64', 4)]:
            with self.assertRaises(ValueError): require_profile(*profile)

    def test_header_flags_are_not_lifetime(self):
        result = decode_header(0, 0x37)
        self.assertEqual(result['chunk_size'], 0x30)
        self.assertTrue(result['prev_inuse'] and result['is_mmapped'] and result['non_main_arena'])
        self.assertEqual(result['allocation_state'], 'unknown_from_header')
        self.assertFalse(decode_header(0, 0x18)['size_plausible'])

    def test_chain_cycle_and_limit(self):
        nodes = {0x1000: 0x2000, 0x2000: 0x1000}
        self.assertEqual(walk_chain(0x1000, nodes.__getitem__, 8)['end'], 'cycle')
        self.assertEqual(walk_chain(0x1000, nodes.__getitem__, 1)['end'], 'limit')
        for invalid in (0, 257, True):
            with self.assertRaises(ValueError): walk_chain(0, nodes.__getitem__, invalid)

    def test_chain_empty_sentinel_unreadable(self):
        self.assertEqual(walk_chain(0, lambda _: 0, 8)['nodes'], [])
        self.assertEqual(walk_chain(0x1000, lambda _: 0x2000, 8, 0x2000)['end'], 'sentinel')
        self.assertEqual(walk_chain(0x1001, lambda _: 0, 8)['end'], 'unaligned_or_invalid')
        def fail(_): raise MemoryError('missing page')
        self.assertEqual(walk_chain(0x1000, fail, 8)['end'], 'unreadable')


if __name__ == '__main__': unittest.main()
