"""Explicit trusted local plugins. Subprocess bounds are not a security sandbox."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from .experiments import encoded, read_bytes, read_json, require

API_VERSION = 1
MAX_PLUGIN = 128 * 1024
MAX_DATA = 1024 * 1024


def inspect(directory):
    directory = Path(directory).resolve()
    require(directory.is_dir(), 'plugin directory missing')
    manifest_path, code_path = directory / 'plugin.json', directory / 'plugin.py'
    require(not manifest_path.is_symlink() and not code_path.is_symlink(), 'plugin files cannot be symlinks')
    manifest = read_json(manifest_path, 8192)
    require(isinstance(manifest, dict) and set(manifest) == {'id', 'version', 'api_version'}, 'invalid plugin manifest')
    require(isinstance(manifest['id'], str) and re.fullmatch('[a-z][a-z0-9_-]{0,63}', manifest['id']), 'invalid plugin id')
    require(isinstance(manifest['version'], str) and re.fullmatch('[0-9]+\.[0-9]+\.[0-9]+', manifest['version']), 'invalid plugin version')
    require(type(manifest['api_version']) is int and manifest['api_version'] == API_VERSION, 'unsupported plugin API')
    code = read_bytes(code_path, MAX_PLUGIN)
    # Trust binds code AND metadata, not a mutable path or a friendly plugin name.
    digest = hashlib.sha256(encoded(manifest) + b'\0' + code).hexdigest()
    return dict(manifest, sha256=digest, path=str(directory), code=code.decode('utf-8'))


def describe(directory):
    return {key: value for key, value in inspect(directory).items() if key != 'code'}


def validate_output(result):
    require(isinstance(result, dict) and set(result) == {'api_version', 'annotations'}, 'invalid plugin output envelope')
    require(type(result['api_version']) is int and result['api_version'] == API_VERSION, 'plugin output API mismatch')
    annotations = result['annotations']
    require(isinstance(annotations, list) and len(annotations) <= 128, 'annotation budget exceeded')
    for item in annotations:
        require(isinstance(item, dict) and set(item) <= {'message', 'address'} and 'message' in item, 'invalid annotation')
        require(isinstance(item['message'], str) and 0 < len(item['message']) <= 2048, 'invalid annotation message')
        if 'address' in item:
            require(type(item['address']) is int and 0 <= item['address'] < 2**64, 'invalid annotation address')
    return result


def run(directory, trusted_sha256, snapshot, timeout=5):
    require(os.name == 'posix', 'plugin runner currently supports POSIX hosts only')
    require(type(timeout) in (int, float) and 0 < timeout <= 10, 'timeout must be 0..10 seconds')
    plugin = inspect(directory)
    require(isinstance(trusted_sha256, str) and trusted_sha256 == plugin['sha256'], 'plugin changed or hash not explicitly trusted')
    require(isinstance(snapshot, dict), 'snapshot must be a JSON object')
    request = encoded({'code': plugin['code'], 'snapshot': snapshot})
    require(len(request) <= MAX_DATA, 'plugin input exceeds 1 MiB budget')
    python = shutil.which('python3') if 'gdb' in sys.modules else sys.executable
    require(bool(python), 'Python 3 interpreter required')
    worker = str(Path(__file__).with_name('plugin_worker.py'))
    with tempfile.TemporaryDirectory(prefix='ressembly-plugin-') as temp:
        output, errors = Path(temp) / 'output', Path(temp) / 'errors'
        with output.open('wb') as stdout, errors.open('wb') as stderr:
            process = subprocess.Popen([python, '-I', '-S', worker], stdin=subprocess.PIPE,
                stdout=stdout, stderr=stderr, cwd=temp, start_new_session=True,
                env={'PATH': os.defpath, 'LANG': 'C.UTF-8'})
            try:
                process.communicate(request, timeout=timeout)
            except subprocess.TimeoutExpired as error:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise ValueError('plugin timeout; no annotations accepted') from error
            finally:
                # Clean up children remaining in this process group. Trusted code can escape
                # that group; this is resource hygiene, NOT confinement of hostile code.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        require(process.returncode == 0, 'plugin failed; no annotations accepted')
        result = validate_output(read_json(output, MAX_DATA))
    return dict(schema='ressembly.plugin-annotations.v1', plugin={k: plugin[k] for k in ('id', 'version', 'api_version', 'sha256')},
                snapshot_id=snapshot.get('snapshot_id'),
                snapshot_sha256=hashlib.sha256(encoded(snapshot)).hexdigest(),
                annotations=result['annotations'], provenance='trusted_local_plugin_output',
                evidence_status='annotations_not_debugger_observations',
                isolation='separate process with resource bounds; not a security sandbox')
