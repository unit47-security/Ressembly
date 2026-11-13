"""Reproducible local package and conservative user-prefix installation."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile

SCHEMA = 'ressembly.local-package.v1'
VERSION = '0.6.0-local'
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_TOTAL = 24 * 1024 * 1024
MAX_FILE = 2 * 1024 * 1024
MAX_FILES = 512
MANIFEST = '.ressembly-manifest.json'


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode() + b'\n'


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def parse(data):
    require(len(data) <= MAX_FILE, 'manifest exceeds budget')
    try:
        return json.loads(data, object_pairs_hook=pairs)
    except (UnicodeError, RecursionError, TypeError) as error:
        raise ValueError('invalid manifest') from error


def safe_path(name):
    require(isinstance(name, str) and 0 < len(name) <= 512, 'invalid package path')
    require(not any(ord(c) < 32 for c in name) and '\\' not in name, 'invalid package path characters')
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name and all(p not in ('.', '..') for p in path.parts),
            'unsafe package path')
    require(name == 'bin/ressembly' or name.startswith('lib/ressembly/'), 'path outside package layout')
    return path


def manifest_check(data):
    require(isinstance(data, dict) and set(data) == {'schema','version','files','scope'}, 'invalid manifest fields')
    require(data['schema'] == SCHEMA and data['version'] == VERSION, 'unsupported package format/version')
    require(data['scope'] == 'local-build; GPL-3.0-or-later; no publication performed', 'invalid package scope')
    require(isinstance(data['files'], dict) and 1 <= len(data['files']) <= MAX_FILES, 'invalid file budget')
    total = 0
    for name, entry in data['files'].items():
        safe_path(name)
        require(isinstance(entry, dict) and set(entry) == {'size','sha256','mode'}, 'invalid file record')
        require(type(entry['size']) is int and 0 <= entry['size'] <= MAX_FILE, 'invalid file size')
        require(entry['mode'] == (0o755 if name == 'bin/ressembly' else 0o644), 'unexpected file mode')
        require(isinstance(entry['sha256'], str) and len(entry['sha256']) == 64
                and all(c in '0123456789abcdef' for c in entry['sha256']), 'invalid file hash')
        total += entry['size']
    require(total <= MAX_TOTAL, 'package exceeds total budget')
    require('bin/ressembly' in data['files'] and 'lib/ressembly/src/ressembly_suite.py' in data['files'],
            'missing required launcher/suite')
    require({'lib/ressembly/LICENSE','lib/ressembly/NOTICE'} <= set(data['files']), 'missing license/notice')
    return data


def source_files(root):
    """Directory+suffix allowlist, never work/, third-party checkouts or caches."""
    root = Path(root)
    selected = {'bin/ressembly': root/'packaging/launcher.py',
                'lib/ressembly/packaging/local_package.py': root/'packaging/local_package.py',
                'lib/ressembly/LICENSE': root/'LICENSE',
                'lib/ressembly/NOTICE': root/'NOTICE',
                'lib/ressembly/README.md': root/'README.md'}
    for directory, pattern in [('src','*.py'), ('examples','*.c'), ('examples','*.py'), ('docs','*.md'),
                               ('integrations','*.py'), ('integrations','*.java'), ('integrations','*.md'), ('integrations','*.json')]:
        for path in sorted((root/directory).rglob(pattern)):
            require(not path.is_symlink() and not any(part.startswith('.') for part in path.relative_to(root).parts),
                    'source symlink/hidden path rejected')
            if '__pycache__' not in path.parts:
                selected['lib/ressembly/'+path.relative_to(root).as_posix()] = path
    for path in sorted((root/'examples/plugins').glob('*/plugin.json')):
        selected['lib/ressembly/'+path.relative_to(root).as_posix()] = path
    for name in ('ressembly-lab.py','ressembly-experiment.py','ressembly-plugins.py','ressembly-ghidra.py','install-local.py'):
        selected['lib/ressembly/scripts/'+name] = root/'scripts'/name
    return selected


def build(root, output):
    selected = source_files(root)
    files, contents = {}, {}
    total = 0
    for name, path in selected.items():
        require(path.is_file() and not path.is_symlink(), 'missing/nonregular source: '+str(path))
        for ancestor in path.parents:
            if ancestor == Path(root): break
            require(not ancestor.is_symlink(), 'source symlink ancestor rejected: '+str(ancestor))
        with path.open('rb') as stream:
            data = stream.read(MAX_FILE + 1)
        require(len(data) <= MAX_FILE, 'source exceeds budget: '+str(path))
        total += len(data)
        require(total <= MAX_TOTAL, 'source total exceeds budget')
        contents[name] = data
        files[name] = dict(size=len(data), sha256=digest(data), mode=0o755 if name == 'bin/ressembly' else 0o644)
    manifest = manifest_check(dict(schema=SCHEMA, version=VERSION, files=files,
                                   scope='local-build; GPL-3.0-or-later; no publication performed'))
    contents['PACKAGE.json'] = canonical(manifest)
    output = Path(output)
    # Exclusive creation: an existing bundle is never overwritten.
    with output.open('xb') as stream:
        try:
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
                for name in sorted(contents):
                    info = zipfile.ZipInfo(name, (1980,1,1,0,0,0))
                    info.create_system = 3
                    mode = 0o755 if name == 'bin/ressembly' else 0o644
                    info.external_attr = (stat.S_IFREG | mode) << 16
                    archive.writestr(info, contents[name])
        except Exception:
            stream.close(); output.unlink()
            raise
    return manifest


def read_package(archive_path):
    archive_path = Path(archive_path)
    require(archive_path.is_file() and archive_path.stat().st_size <= MAX_ARCHIVE, 'invalid archive or size budget')
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            require(2 <= len(infos) <= MAX_FILES + 1, 'archive entry budget')
            names = [info.filename for info in infos]
            require(len(names) == len(set(names)) and 'PACKAGE.json' in names, 'duplicate entries or missing manifest')
            total = 0
            for info in infos:
                if info.filename != 'PACKAGE.json':
                    safe_path(info.filename)
                require(info.create_system == 3 and stat.S_ISREG(info.external_attr >> 16), 'nonregular archive entry')
                require(info.compress_type == zipfile.ZIP_STORED and not info.flag_bits & 1,
                        'compressed/encrypted archives unsupported')
                require(info.file_size == info.compress_size and 0 <= info.file_size <= MAX_FILE, 'entry size budget')
                total += info.file_size
            require(total <= MAX_TOTAL + MAX_FILE, 'total archive budget')
            manifest = manifest_check(parse(archive.read('PACKAGE.json')))
            require(set(names) == set(manifest['files']) | {'PACKAGE.json'}, 'unlisted or missing archive files')
            content = {}
            for name, entry in manifest['files'].items():
                info = archive.getinfo(name)
                require(stat.S_IMODE(info.external_attr >> 16) == entry['mode'], 'archive mode mismatch')
                data = archive.read(name)
                require(len(data) == entry['size'] and digest(data) == entry['sha256'], 'archive integrity mismatch: '+name)
                content[name] = data
            return manifest, content
    except (zipfile.BadZipFile, RuntimeError, KeyError, EOFError) as error:
        raise ValueError('invalid local package: '+str(error)) from error


def prefix_path(prefix):
    require(os.geteuid() != 0, 'run as an ordinary user, not root')
    path = Path(os.path.abspath(os.fspath(prefix)))
    require(path.name not in ('', '.', '..'), 'invalid prefix')
    for ancestor in (path,) + tuple(path.parents):
        require(not ancestor.is_symlink(), 'symlink prefix/ancestor refused: '+str(ancestor))
    require(path.parent.is_dir() and path.parent.stat().st_uid == os.geteuid(),
            'prefix parent must already exist and belong to the current user')
    return path


def install(archive_path, prefix):
    manifest, content = read_package(archive_path)
    prefix = prefix_path(prefix)
    require(not prefix.exists(), 'prefix already exists; choose a new empty location')
    # Reserve the destination exclusively after validating the entire archive.
    prefix.mkdir(mode=0o700)
    created = []
    directories = set()
    try:
        for name, entry in manifest['files'].items():
            target = prefix/name
            missing = []
            parent = target.parent
            while parent != prefix and not parent.exists():
                missing.append(parent); parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir(mode=0o755); directories.add(directory)
            with target.open('xb') as stream:
                created.append(target)
                stream.write(content[name]); stream.flush(); os.fsync(stream.fileno())
            target.chmod(entry['mode'])
        marker = prefix/MANIFEST
        with marker.open('xb') as stream:
            created.append(marker); stream.write(canonical(manifest)); stream.flush(); os.fsync(stream.fileno())
        marker.chmod(0o644)
    except Exception:
        # Only paths created by this operation; never recursively delete the prefix.
        for target in reversed(created):
            if target.is_file() and not target.is_symlink():
                target.unlink()
        for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
            try: directory.rmdir()
            except OSError: pass
        try: prefix.rmdir()
        except OSError: pass
        raise
    return verify(prefix)


def verify(prefix):
    prefix = prefix_path(prefix)
    require(prefix.is_dir(), 'installation prefix does not exist')
    marker = prefix/MANIFEST
    require(marker.is_file() and not marker.is_symlink() and marker.stat().st_size <= MAX_FILE,
            'missing/nonregular install manifest')
    manifest = manifest_check(parse(marker.read_bytes()))
    expected_files = set(manifest['files']) | {MANIFEST}
    expected_dirs = set()
    for name in manifest['files']:
        parent = PurePosixPath(name).parent
        while str(parent) != '.':
            expected_dirs.add(str(parent)); parent = parent.parent
    seen_files, seen_dirs = set(), set()
    for directory, dirs, files in os.walk(prefix, followlinks=False):
        for name in dirs + files:
            target = Path(directory)/name
            require(not target.is_symlink(), 'installation contains a symlink: '+str(target.relative_to(prefix)))
            rel = target.relative_to(prefix).as_posix()
            if target.is_dir(): seen_dirs.add(rel)
            elif target.is_file(): seen_files.add(rel)
            else: raise ValueError('installation contains a nonregular entry: '+rel)
    require(seen_files == expected_files and seen_dirs == expected_dirs,
            'installation contains missing or extra files/directories; nothing removed')
    for name, entry in manifest['files'].items():
        path = prefix/name
        require(path.stat().st_size == entry['size'] and stat.S_IMODE(path.stat().st_mode) == entry['mode'],
                'installed size/mode changed: '+name)
        require(digest(path.read_bytes()) == entry['sha256'], 'installed content changed: '+name)
    return manifest


def uninstall(prefix):
    prefix = prefix_path(prefix)
    manifest = verify(prefix)
    directories = set()
    for name in manifest['files']:
        target = prefix/name
        parent = target.parent
        while parent != prefix:
            directories.add(parent); parent = parent.parent
        target.unlink()
    (prefix/MANIFEST).unlink()
    for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        directory.rmdir()
    prefix.rmdir()
    return {'status':'uninstalled', 'files_removed':len(manifest['files'])}
