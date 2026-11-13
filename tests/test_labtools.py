import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ressembly.labtools import cyclic, cyclic_offset, inspect_elf, ELFError


def fixture(stack_flags=6, stack_type=0x6474e551):
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<HHIQQQIHHHHHH', 2, 62, 1, 0, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    phdr = struct.pack('<IIQQQQQQ', stack_type, stack_flags, 0, 0, 0, 0, 0, 16)
    return ident + header + phdr


class PatternTests(unittest.TestCase):
    def test_known_vectors(self):
        self.assertEqual(cyclic(40), b'aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaa')
        self.assertEqual(cyclic(16, 4, b'ab'), b'aaaabaabbababbbb')
        self.assertEqual(cyclic(9, 2, b'abc'), b'aabacbbcc')

    def test_complete_cycle_unique_windows(self):
        for width in (2, 3, 4, 8):
            pattern = cyclic(2 ** width, width, b'ab')
            ring = pattern + pattern[:width - 1]
            self.assertEqual(len({ring[i:i + width] for i in range(len(pattern))}), 2 ** width)

    def test_exact_integer_endian(self):
        self.assertEqual(cyclic_offset(0x61616162, 100)['offsets'], [4])
        self.assertEqual(cyclic_offset(0x62616161, 100, endian='big')['offsets'], [4])
        self.assertEqual(cyclic_offset(b'baaa', 100)['offsets'], [4])

    def test_ambiguous_missing_and_search_bounds(self):
        self.assertEqual(cyclic_offset(b'a', 100)['status'], 'ambiguous')
        self.assertEqual(cyclic_offset(b'ZZZZ', 100)['status'], 'not_found')
        self.assertEqual(cyclic_offset(b'baaa', 7)['status'], 'not_found')
        self.assertTrue(cyclic_offset(b'a', 5000)['offsets_truncated'])

    def test_invalid_parameters_not_silently_truncated(self):
        for args in [(-1,), (1048577,), (10, 1), (10, 9), (5, 2, b'ab'), (2, 4, b'aa')]:
            with self.assertRaises(ValueError):
                cyclic(*args)
        for value in (-1, 2 ** 32, b'', b'abcde', True):
            with self.assertRaises(ValueError):
                cyclic_offset(value, 100)
        with self.assertRaises(ValueError):
            cyclic_offset(b'a', 100, endian='middle')
        self.assertEqual(cyclic(0), b'')


class ELFTests(unittest.TestCase):
    def test_stack_and_unknown_symbol_coverage(self):
        result = inspect_elf(fixture())
        self.assertEqual(result['nx_stack'], 'yes')
        self.assertEqual(result['pie'], 'no')
        self.assertEqual(result['canary_indicator'], 'unknown_no_symbol_tables')
        self.assertEqual(inspect_elf(fixture(7))['nx_stack'], 'no')
        self.assertEqual(inspect_elf(fixture(stack_type=0))['nx_stack'], 'unknown')

    def test_truncation_and_architecture(self):
        original = fixture()
        for size in (0, 4, 63, 64, 119):
            with self.assertRaises(ELFError):
                inspect_elf(original[:size])
        for offset, value in ((4, 1), (5, 2), (18, 183)):
            data = bytearray(original)
            data[offset] = value
            with self.assertRaises(ELFError):
                inspect_elf(bytes(data))

    def test_excessive_and_invalid_tables(self):
        for offset, fmt, value in ((56, '<H', 1025), (32, '<Q', 2 ** 63), (58, '<H', 64), (40, '<Q', 64)):
            data = bytearray(fixture())
            struct.pack_into(fmt, data, offset, value)
            if offset == 58:  # nonzero section count needs a real table
                struct.pack_into('<H', data, 60, 1)
            with self.assertRaises(ELFError):
                inspect_elf(bytes(data))

    def test_dyn_without_pie_flag_is_undetermined(self):
        data = bytearray(fixture())
        struct.pack_into('<H', data, 16, 3)
        self.assertEqual(inspect_elf(bytes(data))['pie'], 'undetermined')


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/ressembly-lab.py'), *args], capture_output=True)

    def test_pattern_and_offset(self):
        self.assertEqual(self.run_cli('pattern', '8').stdout, b'aaaabaaa')
        process = self.run_cli('offset', '--integer', '0x61616162', '--length', '100')
        self.assertEqual(process.returncode, 0)
        self.assertEqual(json.loads(process.stdout)['offsets'], [4])

    def test_errors(self):
        for args in [('elf', '/no/such/elf'), ('offset', '--hex', 'ZZ', '--length', '10'),
                     ('pattern', '-1'), ('offset', '--integer', '0x100000000', '--length', '100')]:
            process = self.run_cli(*args)
            self.assertEqual(process.returncode, 2)
            self.assertNotIn(b'Traceback', process.stderr)


if __name__ == '__main__':
    unittest.main()
