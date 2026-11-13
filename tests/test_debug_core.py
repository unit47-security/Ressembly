import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))
from ressembly.debug_core import checked_range, parse_maps, readable_prefix, find_matches, walk_pointers

class DebugCoreTests(unittest.TestCase):
    def test_range_limits(self):
        checked_range((1 << 64) - 1, 1, 1)
        for address, size in [(-1, 1), ((1 << 64) - 1, 2), (0, 0), (0, 4097), (True, 1)]:
            with self.assertRaises(ValueError): checked_range(address, size, 4096)

    def test_maps_paths_and_permissions(self):
        regions = parse_maps('1000-2000 rw-p 00000000 00:00 0 /a path\n2000-3000 r--p 0 00:00 0\n3000-4000 ---p 0 00:00 0')
        self.assertEqual(regions[0]['path'], '/a path')
        self.assertEqual(readable_prefix(regions, 0x1800, 0x2000), 0x1800)
        self.assertEqual(readable_prefix(regions, 0, 1), 0)
        for value in ['oops', '0-1 xxxx 0 00:00 0', '2-1 rw-p 0 00:00 0']:
            with self.assertRaises(ValueError): parse_maps(value)

    def test_search_overlap_and_match_limit(self):
        self.assertEqual(find_matches(b'aaaa', b'aa'), ([0, 1, 2], False))
        self.assertEqual(find_matches(b'aaaa', b'aa', 2), ([0, 1], True))
        for pattern in [b'', b'a' * 257]:
            with self.assertRaises(ValueError): find_matches(b'', pattern)

    def test_pointer_terminations(self):
        memory = {8: 16, 16: 8, 24: 0}
        def read(address, length):
            if address not in memory: raise ValueError('missing')
            return memory[address].to_bytes(length, 'little')
        self.assertEqual(walk_pointers(8, read, 8)['termination'], 'cycle')
        self.assertEqual(len(walk_pointers(8, read, 8)['nodes']), 2)
        self.assertEqual(walk_pointers(24, read, 1)['termination'], 'null')
        self.assertEqual(walk_pointers(8, read, 1)['termination'], 'depth_limit')
        self.assertEqual(walk_pointers(32, read, 1)['termination'], 'unreadable')
        self.assertEqual(walk_pointers(0, read, 1)['nodes'], [])

if __name__ == '__main__': unittest.main()
