"""Compile-only checks for embedded owned corpus and GDB snippets (not Linux validation)."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('r6_validation', ROOT/'scripts/validate-r6-linux.py')
r6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r6)


class R6CorpusSyntax(unittest.TestCase):
    def test_embedded_raw_oracle_is_valid_python(self):
        compile(r6.RAW, '<raw-gdb-oracle>', 'exec')
        self.assertNotIn('ressembly', r6.RAW)



if __name__ == '__main__':
    unittest.main()
