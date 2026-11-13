import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ressembly.allocator_profiles import banner_version, occupied_count, profile


class AllocatorProfiles(unittest.TestCase):
    def test_exact_releases_and_abi(self):
        for version in ('2.36', '2.43'):
            self.assertEqual(banner_version('GNU C Library, release version '+version+'.\n'), version)
        for version in ('2.430', '2.43.1', '2.43..', '2.37'):
            with self.assertRaises(ValueError):
                banner_version('GNU C Library, release version '+version+'.\n')
        with self.assertRaises(ValueError): banner_version('not a libc banner')
        for args in [('2.43', 'aarch64', 8), ('2.43','i386:x86-64',4)]:
            with self.assertRaises(ValueError): profile(*args)

    def test_layouts_are_distinct(self):
        old, new = profile('2.36'), profile('2.43')
        self.assertEqual((old['tcache_bins'], old['tcache_counter'], old['tcache_entries_offset']), (64, 'counts',128))
        self.assertTrue(old['fastbins_present'])
        self.assertFalse(new['fastbins_present'])
        self.assertEqual((new['tcache_bins'], new['tcache_counter'], new['tcache_entries_offset']), (76, 'num_slots',152))

    def test_countdown_tunable_and_zero_capacity(self):
        self.assertEqual(occupied_count('2.43', 16, 16), 0)
        self.assertEqual(occupied_count('2.43', 14, 16), 2)
        self.assertEqual(occupied_count('2.43', 1, 3), 2)
        self.assertEqual(occupied_count('2.43', 0, 0), 0)
        self.assertEqual(occupied_count('2.36', 3), 3)
        for raw,capacity in ((4,3),(-1,3),(True,3),(3,None),(0,65536)):
            with self.assertRaises(ValueError): occupied_count('2.43',raw,capacity)
