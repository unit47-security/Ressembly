"""Bounded, self-contained local evidence dossiers. Never execute stored inputs."""
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
from datetime import datetime, timezone

SCHEMA = 'ressembly.experiment.v1'
MAX_FILE = 8 * 1024 * 1024
MAX_INPUT = 256 * 1024
MAX_SNAPSHOT = 1024 * 1024
MAX_RECORDS = 128


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(',', ':')).encode('utf-8')


def text(value, limit, field):
    require(isinstance(value, str) and 0 < len(value) <= limit,
            field + ' must be a nonempty bounded string')
    require(not any(ord(char) < 32 and char not in '\n\t' for char in value),
            field + ' contains control characters')
    return value


def sha(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'invalid SHA-256')


def now():
    return datetime.now(timezone.utc).isoformat()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def read_bytes(path, limit):
    require(Path(path).is_file(), 'input must be a regular file')
    with Path(path).open('rb') as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, 'file exceeds byte budget')
    return data


def read_json(path, limit=MAX_FILE):
    def invalid(_):
        raise ValueError('nonfinite JSON number')
    try:
        return json.loads(read_bytes(path, limit), object_pairs_hook=pairs,
                          parse_constant=invalid)
    except (UnicodeError, RecursionError) as error:
        raise ValueError('invalid or excessively nested JSON') from error


def validate(data):
    require(isinstance(data, dict) and data.get('schema') == SCHEMA, 'unsupported dossier schema')
    require(set(data) == {'schema', 'id', 'title', 'created', 'updated', 'build',
                         'inputs', 'snapshots', 'notes', 'limits'}, 'unexpected dossier fields')
    text(data['id'], 36, 'id')
    text(data['title'], 200, 'title')
    for field in ('created', 'updated'):
        text(data[field], 64, field)
    require(isinstance(data['build'], dict), 'invalid build')
    sha(data['build'].get('sha256'))
    text(data['build'].get('name'), 1024, 'build name')
    require(data['limits'] == {'authenticity': 'not_proven_by_file',
            'replay': 'not_implemented', 'coverage': 'selected_snapshots_only'}, 'invalid evidence limits')
    all_ids = set()
    snapshot_ids = set()
    for collection in ('inputs', 'snapshots', 'notes'):
        require(isinstance(data[collection], list) and len(data[collection]) <= MAX_RECORDS,
                'invalid collection or record budget exceeded')
        for record in data[collection]:
            require(isinstance(record, dict), 'invalid record')
            identifier = text(record.get('id'), 36, 'record id')
            require(identifier not in all_ids, 'duplicate record id')
            all_ids.add(identifier)
            text(record.get('created'), 64, 'record timestamp')
            if collection == 'inputs':
                text(record.get('label'), 200, 'input label')
                require(record.get('status') == 'recorded_not_proven_consumed', 'invalid input status')
                raw = record.get('base64')
                require(isinstance(raw, str) and len(raw) <= 4 * ((MAX_INPUT + 2) // 3), 'input budget')
                try:
                    content = base64.b64decode(raw, validate=True)
                except (ValueError, base64.binascii.Error) as error:
                    raise ValueError('invalid input base64') from error
                require(len(content) <= MAX_INPUT and type(record.get('size')) is int
                        and record['size'] == len(content)
                        and record.get('sha256') == digest(content), 'input integrity mismatch')
            elif collection == 'snapshots':
                snapshot_ids.add(identifier)
                text(record.get('label'), 200, 'snapshot label')
                text(record.get('run_id'), 128, 'run id')
                require(record.get('build_sha256') == data['build']['sha256'], 'incompatible build')
                require(record.get('provenance') in ('gdb_context', 'supplied_json'), 'invalid provenance')
                require(isinstance(record.get('payload'), dict), 'snapshot must be an object')
                context = record['payload'].get('schema') == 'ressembly.debug-context.v1'
                require(record['provenance'] != 'gdb_context' or context,
                        'GDB provenance requires a recognized context')
                identity_keys = {'ressembly.debug-context.v1': 'executable_sha256',
                                 'ressembly.object-history.v1': 'target_sha256',
                                 'ressembly.object-history.v2': 'target_sha256',
                                 'ressembly.marker-history.v1': 'target_sha256'}
                payload_schema = record['payload'].get('schema')
                require(payload_schema is None or isinstance(payload_schema, (str, int, float, bool)),
                        'snapshot schema must be a scalar JSON value')
                identity_key = identity_keys.get(payload_schema)
                if identity_key is not None:
                    metadata = record['payload'].get('metadata')
                    require(isinstance(metadata, dict)
                            and metadata.get(identity_key) == record['build_sha256']
                            and metadata.get('run_id') == record['run_id'],
                            'embedded build/run metadata contradicts record')
                payload = encoded(record['payload'])
                require(len(payload) <= MAX_SNAPSHOT and record.get('sha256') == digest(payload),
                        'snapshot integrity mismatch or budget exceeded')
            else:
                text(record.get('text'), 16384, 'note')
                require(record.get('snapshot_id') is None
                        or isinstance(record['snapshot_id'], str) and record['snapshot_id'] in snapshot_ids,
                        'note references missing snapshot')
    require(len(encoded(data)) <= MAX_FILE, 'dossier byte budget exceeded')
    return data


def load(path):
    return validate(read_json(path))


@contextmanager
def locked(path):
    path = Path(path).absolute()
    require(not path.is_symlink(), 'refusing symlink dossier')
    lock = path.with_name(path.name + '.lock')
    descriptor = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.close(descriptor)
        yield path
    finally:
        lock.unlink()


def write(path, data, *, replace=True):
    """Commit a complete temporary file; new destinations use an exclusive link."""
    content = encoded(validate(data)) + b'\n'
    require(len(content) <= MAX_FILE, 'dossier byte budget exceeded')
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=str(path.parent))
    committed = False
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, str(path))
        else:
            # Unlike an existence check followed by replace, link cannot overwrite
            # a destination created by another writer just before this commit.
            os.link(temporary, str(path))
        committed = True
    finally:
        if os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError as error:
                if committed:
                    raise OSError('dossier committed at %s; temporary cleanup failed: %s'
                                  % (path, temporary)) from error
                raise


def create(path, binary, title):
    # Hash in chunks; do not load arbitrary binaries into memory.
    require(Path(binary).is_file(), 'binary must be a regular file')
    require(Path(binary).stat().st_size <= 256 * 1024 * 1024, 'binary exceeds 256 MiB budget')
    total = 0
    checksum = hashlib.sha256()
    with Path(binary).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            total += len(block)
            require(total <= 256 * 1024 * 1024, 'binary exceeds 256 MiB budget')
            checksum.update(block)
    stamp = now()
    data = dict(schema=SCHEMA, id=str(uuid.uuid4()), title=title, created=stamp, updated=stamp,
                build={'name': Path(binary).name, 'sha256': checksum.hexdigest()}, inputs=[],
                snapshots=[], notes=[], limits={'authenticity': 'not_proven_by_file',
                'replay': 'not_implemented', 'coverage': 'selected_snapshots_only'})
    with locked(path) as destination:
        require(not destination.exists(), 'dossier already exists')
        write(destination, data, replace=False)
    return data


def append(path, collection, record):
    record = dict(record, id=str(uuid.uuid4()), created=now())
    with locked(path) as destination:
        data = load(destination)
        data[collection].append(record)
        data['updated'] = now()
        write(destination, data)
    return record['id']


def add_input(path, source, label):
    content = read_bytes(source, MAX_INPUT)
    return append(path, 'inputs', dict(label=label, base64=base64.b64encode(content).decode('ascii'),
                 sha256=digest(content), size=len(content), status='recorded_not_proven_consumed'))


def add_snapshot(path, payload, build_sha256, run_id, label, provenance='supplied_json'):
    return append(path, 'snapshots', dict(payload=payload, build_sha256=build_sha256,
                  run_id=run_id, label=label, provenance=provenance, sha256=digest(encoded(payload))))


def add_note(path, note, snapshot_id=None):
    return append(path, 'notes', dict(text=note, snapshot_id=snapshot_id))


def compare(left_path, left_id, right_path, right_id):
    left, right = load(left_path), load(right_path)
    require(left['build']['sha256'] == right['build']['sha256'], 'cannot compare incompatible builds')
    def select(data, identifier):
        matches = [item for item in data['snapshots'] if item['id'] == identifier]
        require(len(matches) == 1, 'snapshot not found')
        return matches[0]
    a, b = select(left, left_id), select(right, right_id)
    scopes = {'ressembly.debug-context.v1': 'linux_process_boot_pid_start',
              'ressembly.object-history.v1': 'object_history_capture_uuid',
              'ressembly.object-history.v2': 'extended_history_capture_uuid',
              'ressembly.marker-history.v1': 'marker_history_capture_uuid'}
    left_scope = scopes.get(a['payload'].get('schema'), 'caller_declared')
    right_scope = scopes.get(b['payload'].get('schema'), 'caller_declared')
    comparable = left_scope == right_scope
    keys = sorted(set(a['payload']) | set(b['payload']))
    differences = [{'section': key, 'left_present': key in a['payload'],
                    'right_present': key in b['payload'], 'left': a['payload'].get(key),
                    'right': b['payload'].get(key)} for key in keys
                   if (key in a['payload']) != (key in b['payload'])
                   or a['payload'].get(key) != b['payload'].get(key)]
    return dict(schema='ressembly.snapshot-comparison.v1', left_id=left_id, right_id=right_id,
                same_run=(a['run_id'] == b['run_id']) if comparable else None,
                left_run_scope=left_scope, right_run_scope=right_scope,
                run_identity_relation='comparable' if comparable else 'different_identity_domains',
                differences=differences,
                interpretation='raw values only; addresses are not object identities; '
                'snapshot differences do not reconstruct intermediate writes; '
                'capture UUIDs are not process identities')


def export(path, destination):
    data = load(path)
    with locked(destination) as target:
        require(not target.exists(), 'export destination already exists')
        write(target, data, replace=False)
    return data
