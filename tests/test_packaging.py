import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packaging'))
import local_package as pkg


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve(); self.source=self.base/'source'; self.source.mkdir()
        for directory in ('src','scripts','examples','docs','packaging','work'):
            (self.source/directory).mkdir()
        for name in ('packaging/local_package.py','packaging/launcher.py','scripts/install-local.py'):
            shutil.copy2(ROOT/name,self.source/name)
        for name in ('ressembly-lab.py','ressembly-experiment.py','ressembly-plugins.py','ressembly-ghidra.py'):
            (self.source/'scripts'/name).write_text('import json,sys\nprint(json.dumps(sys.argv[1:]))\n')
        (self.source/'src/ressembly_suite.py').write_text('# owned fixture, not GDB validation\n')
        for name in ('README.md','LICENSE','NOTICE'):
            (self.source/name).write_text('owned fixture '+name+'\n')
        (self.source/'docs/guide.md').write_text('guide\n')
        (self.source/'work/private-key').write_text('must not ship\n')
        sample=self.source/'examples/plugins/summary'; sample.mkdir(parents=True)
        (sample/'plugin.json').write_text('{"id":"summary","version":"1.0.0","api_version":1}')
        (sample/'plugin.py').write_text('# owned fixture plugin\n')
        self.archive=self.base/'bundle.zip'; pkg.build(self.source,self.archive)
        self.prefix=self.base/'prefix with spaces'

    def rewrite(self,name,modify):
        path=self.base/name
        with zipfile.ZipFile(self.archive) as original, zipfile.ZipFile(path,'w') as result:
            entries=[(info,original.read(info.filename)) for info in original.infolist()]
            for info,data in modify(entries): result.writestr(info,data)
        return path

    def test_reproducible_allowlist_and_complete_install(self):
        second=self.base/'second.zip'; pkg.build(self.source,second)
        self.assertEqual(self.archive.read_bytes(),second.read_bytes())
        manifest,contents=pkg.read_package(self.archive)
        self.assertFalse(any('work/' in name or 'private-key' in name for name in contents))
        self.assertIn('lib/ressembly/LICENSE',contents)
        self.assertEqual(json.loads(contents['lib/ressembly/examples/plugins/summary/plugin.json'])['id'],'summary')
        pkg.install(self.archive,self.prefix)
        self.assertEqual(pkg.verify(self.prefix),manifest)
        launcher=self.prefix/'bin/ressembly'
        result=subprocess.run([sys.executable,str(launcher),'lab','literal $(ignored)','space value'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),['literal $(ignored)','space value'])
        self.assertFalse(list(self.prefix.rglob('__pycache__')))
        pkg.uninstall(self.prefix); self.assertFalse(self.prefix.exists())

    def test_existing_prefix_and_archive_never_overwritten(self):
        with self.assertRaises(FileExistsError): pkg.build(self.source,self.archive)
        self.prefix.mkdir(); marker=self.prefix/'keep'; marker.write_text('keep')
        with self.assertRaisesRegex(ValueError,'already exists'): pkg.install(self.archive,self.prefix)
        self.assertEqual(marker.read_text(),'keep')

    def test_corruption_and_extra_archive_entry_rejected(self):
        def corrupt(entries):
            return [(info,b'X'*len(data) if info.filename=='lib/ressembly/README.md' else data) for info,data in entries]
        bad=self.rewrite('corrupt.zip',corrupt)
        with self.assertRaisesRegex(ValueError,'integrity'): pkg.install(bad,self.prefix)
        self.assertFalse(self.prefix.exists())
        def extra(entries):
            info=zipfile.ZipInfo('lib/ressembly/extra.txt'); info.create_system=3
            info.external_attr=(stat.S_IFREG|0o644)<<16
            return entries+[(info,b'extra')]
        bad=self.rewrite('extra.zip',extra)
        with self.assertRaisesRegex(ValueError,'unlisted'): pkg.read_package(bad)

    def test_traversal_symlink_duplicate_and_compression_rejected(self):
        for name,entryname,mode in [('traversal','../escape',stat.S_IFREG|0o644),
                                   ('symlink','lib/ressembly/link',stat.S_IFLNK|0o777)]:
            def changed(entries):
                info=zipfile.ZipInfo(entryname); info.create_system=3; info.external_attr=mode<<16
                return entries+[(info,b'target')]
            bad=self.rewrite(name+'.zip',changed)
            with self.assertRaises(ValueError): pkg.read_package(bad)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            bad=self.rewrite('duplicate.zip',lambda entries:entries+[entries[0]])
        with self.assertRaisesRegex(ValueError,'duplicate'): pkg.read_package(bad)
        def compressed(entries):
            entries[0][0].compress_type=zipfile.ZIP_DEFLATED
            return entries
        bad=self.rewrite('compressed.zip',compressed)
        with self.assertRaisesRegex(ValueError,'compressed'): pkg.read_package(bad)

    def test_uninstall_refuses_modified_extra_and_symlink_without_deletion(self):
        pkg.install(self.archive,self.prefix)
        owned=self.prefix/'lib/ressembly/README.md'; original=owned.read_bytes()
        owned.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'): pkg.uninstall(self.prefix)
        self.assertTrue((self.prefix/'bin/ressembly').exists())
        owned.write_bytes(original)
        extra=self.prefix/'user-notes'; extra.write_text('preserve')
        with self.assertRaisesRegex(ValueError,'extra'): pkg.uninstall(self.prefix)
        self.assertEqual(extra.read_text(),'preserve'); extra.unlink()
        owned.unlink(); owned.symlink_to(self.source/'README.md')
        with self.assertRaisesRegex(ValueError,'symlink'): pkg.uninstall(self.prefix)
        self.assertTrue((self.source/'README.md').exists())

    def test_symlink_source_or_prefix_ancestor_refused(self):
        linked=self.base/'linked'; linked.symlink_to(self.base,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'): pkg.install(self.archive,linked/'install')
        (self.source/'docs/guide.md').unlink()
        (self.source/'docs/guide.md').symlink_to(self.source/'README.md')
        with self.assertRaisesRegex(ValueError,'symlink'): pkg.build(self.source,self.base/'bad-source.zip')

    def test_size_budget_and_manifest_incoherence(self):
        def invalid(entries):
            result=[]
            for info,content in entries:
                if info.filename=='PACKAGE.json':
                    data=json.loads(content); data['files']['bin/ressembly']['size']=pkg.MAX_FILE+1
                    content=json.dumps(data).encode()
                result.append((info,content))
            return result
        bad=self.rewrite('oversize.zip',invalid)
        with self.assertRaisesRegex(ValueError,'size'): pkg.read_package(bad)
        bad=self.base/'notzip'; bad.write_bytes(b'not zip')
        with self.assertRaises(ValueError): pkg.read_package(bad)


if __name__=='__main__': unittest.main()
