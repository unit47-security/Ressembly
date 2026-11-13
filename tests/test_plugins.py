"""Independent contract checks for explicit trusted local annotations."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ressembly import plugins

GOOD = "def analyze(snapshot):\n return {'api_version': 1, 'annotations': [{'message': 'analyst note', 'address': 16}]}\n"


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = self.root / 'owned-plugin'
        self.plugin.mkdir()
        self.manifest = {'id': 'owned', 'version': '1.0.0', 'api_version': 1}
        self.write(GOOD)
        self.snapshot = {'schema': 'ressembly.debug-context.v1', 'snapshot_id': 'offline-fixture',
                         'registers': {'rax': 10}, 'coverage': 'synthetic test, not GDB evidence'}

    def write(self, code, manifest=None):
        (self.plugin / 'plugin.json').write_text(json.dumps(manifest or self.manifest))
        (self.plugin / 'plugin.py').write_text(code)

    def run_plugin(self, **kwargs):
        return plugins.run(self.plugin, plugins.describe(self.plugin)['sha256'], self.snapshot, **kwargs)

    def test_inspection_never_executes_and_trust_binds_code(self):
        marker = self.root / 'executed'
        self.write('from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("ran")\n' + GOOD)
        description = plugins.describe(self.plugin)
        self.assertNotIn('code', description)
        self.assertFalse(marker.exists())
        with self.assertRaisesRegex(ValueError, 'trusted'):
            plugins.run(self.plugin, '0' * 64, self.snapshot)
        self.assertFalse(marker.exists())
        plugins.run(self.plugin, description['sha256'], self.snapshot)
        self.assertEqual(marker.read_text(), 'ran')
        with (self.plugin / 'plugin.py').open('a') as stream:
            stream.write('\n# changed\n')
        with self.assertRaisesRegex(ValueError, 'changed'):
            plugins.run(self.plugin, description['sha256'], self.snapshot)

    def test_trust_binds_manifest_and_api(self):
        checksum = plugins.describe(self.plugin)['sha256']
        self.write(GOOD, dict(self.manifest, version='1.0.1'))
        with self.assertRaisesRegex(ValueError, 'changed'):
            plugins.run(self.plugin, checksum, self.snapshot)
        for version in (2, True, '1'):
            self.write(GOOD, dict(self.manifest, api_version=version))
            with self.assertRaisesRegex(ValueError, 'API'):
                plugins.describe(self.plugin)

    def test_invalid_manifest_symlink_and_oversized_code(self):
        for manifest in (dict(self.manifest, id='../bad'), dict(self.manifest, version='latest'),
                         dict(self.manifest, extra='unrecognized')):
            self.write(GOOD, manifest)
            with self.assertRaises(ValueError):
                plugins.describe(self.plugin)
        self.write(GOOD)
        code = self.plugin / 'plugin.py'; code.unlink()
        target = self.root / 'other.py'; target.write_text(GOOD); code.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            plugins.describe(self.plugin)
        code.unlink(); self.write('#' * (plugins.MAX_PLUGIN + 1))
        with self.assertRaisesRegex(ValueError, 'budget'):
            plugins.describe(self.plugin)

    def test_annotations_remain_distinct_and_do_not_mutate_input(self):
        original = copy.deepcopy(self.snapshot)
        self.write("def analyze(snapshot):\n snapshot['registers']['rax']=99\n return {'api_version':1,'annotations':[{'message':'hypothesis'}]}\n")
        result = self.run_plugin()
        self.assertEqual(self.snapshot, original)
        self.assertEqual(result['evidence_status'], 'annotations_not_debugger_observations')
        self.assertEqual(result['provenance'], 'trusted_local_plugin_output')
        self.assertIn('not a security sandbox', result['isolation'])
        self.assertEqual(result['snapshot_id'], 'offline-fixture')
        self.assertEqual(len(result['snapshot_sha256']), 64)

    def test_output_cannot_promote_annotations_to_observations(self):
        bad = [ {'api_version':1,'annotations':[],'observations':[]},
                {'api_version':1,'annotations':[{'message':'x','provenance':'observed'}]},
                {'api_version':True,'annotations':[]},
                {'api_version':1,'annotations':[{'message':'x','address':True}]},
                {'api_version':1,'annotations':[{'message':'x','address':-1}]},
                {'api_version':1,'annotations':[{'message':'x' * 2049}]},
                {'api_version':1,'annotations':[{'message':'x'}] * 129} ]
        for output in bad:
            with self.subTest(output=str(output)[:60]):
                self.write('def analyze(snapshot):\n return ' + repr(output) + '\n')
                with self.assertRaises(ValueError):
                    self.run_plugin()

    def test_exception_and_bad_json_accept_no_annotations(self):
        for code in ("raise RuntimeError('owned failure')\n", "print('unexpected output')\n" + GOOD,
                     "def analyze(snapshot):\n return {'api_version':1,'annotations':[{'message':float('nan')}]}\n"):
            self.write(code)
            with self.assertRaises(ValueError):
                self.run_plugin()

    def test_timeout_and_output_limit(self):
        self.write('import time\ntime.sleep(2)\n' + GOOD)
        with self.assertRaisesRegex(ValueError, 'timeout'):
            self.run_plugin(timeout=0.1)
        self.write("import sys\nsys.stdout.write('x' * (2 * 1024 * 1024))\n" + GOOD)
        with self.assertRaises(ValueError):
            self.run_plugin()

    def test_input_budget_and_invalid_timeout(self):
        checksum = plugins.describe(self.plugin)['sha256']
        with self.assertRaisesRegex(ValueError, 'input exceeds'):
            plugins.run(self.plugin, checksum, {'data': 'x' * plugins.MAX_DATA})
        for timeout in (0, -1, 11, True, float('nan')):
            with self.assertRaisesRegex(ValueError, 'timeout'):
                self.run_plugin(timeout=timeout)

    def test_cli_requires_trust_and_preserves_existing_output(self):
        snapshot = self.root / 'snapshot.json'; snapshot.write_text(json.dumps(self.snapshot))
        command = [sys.executable, str(ROOT / 'scripts/ressembly-plugins.py')]
        missing = subprocess.run(command + ['run', str(self.plugin), str(snapshot)], capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        checksum = plugins.describe(self.plugin)['sha256']
        output = self.root / 'annotations.json'
        args = command + ['run', str(self.plugin), str(snapshot), '--trust-sha256', checksum, '--output', str(output)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        original = output.read_bytes()
        duplicate = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(duplicate.returncode, 1)
        self.assertEqual(output.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
