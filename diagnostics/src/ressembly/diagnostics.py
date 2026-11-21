"""Application-owned lifecycle records and aggregate allocator statistics."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import tempfile
from threading import Lock, get_native_id
import time
from uuid import uuid4

from .experiments import encoded, pairs, read_bytes, require, text


class ProcessLog:
    """Create one log in each participating process, after spawn or fork."""

    def __init__(self, label, parent_id=None):
        self.label = text(label, 100, 'process label')
        require(parent_id is None or isinstance(parent_id, str) and
                re.fullmatch(r'[0-9a-f]{32}', parent_id), 'invalid parent identity')
        self.identity = uuid4().hex
        self.parent_id = parent_id
        self.pid = os.getpid()
        self._lock = Lock()
        self._events = []
        self._started = time.monotonic_ns()
        self._open_threads = 0
        self._closed = False
        self._record('recording_started', self.label)

    def _record(self, kind, label, thread_id=None):
        self._events.append({
            'sequence': len(self._events) + 1,
            'elapsed_ns': time.monotonic_ns() - self._started,
            'kind': kind,
            'label': label,
            'os_thread_id': get_native_id(),
            'thread_id': thread_id,
        })

    @contextmanager
    def thread(self, label):
        label = text(label, 100, 'thread label')
        require(self.pid == os.getpid(), 'create a new log after fork')
        thread_id = uuid4().hex
        with self._lock:
            require(not self._closed, 'process log already closed')
            require(len(self._events) + self._open_threads + 3 <= 128,
                    'process log event budget exceeded')
            self._open_threads += 1
            self._record('thread_enter', label, thread_id)
        try:
            yield
        finally:
            with self._lock:
                self._record('thread_leave', label, thread_id)
                self._open_threads -= 1

    def close(self):
        require(self.pid == os.getpid(), 'create a new log after fork')
        with self._lock:
            require(not self._closed and self._open_threads == 0,
                    'finish thread scopes before closing the process log')
            self._record('recording_finished', self.label)
            self._closed = True
            return {
                'id': self.identity, 'parent_id': self.parent_id,
                'label': self.label, 'pid': self.pid, 'events': list(self._events),
            }


def report(run_id, start_method, processes, children):
    return {
        'schema': 'ressembly.process-diagnostics.v1',
        'metadata': {'run_id': run_id, 'architecture': platform.machine(),
                     'os': platform.system(), 'start_method': start_method},
        'coverage': ('Application-declared lifecycle scopes; sequence and clock are local to '
                     'each process; child exit status comes from the demo supervisor.'),
        'processes': processes,
        'children': children,
    }


def jemalloc_summary(path):
    raw = read_bytes(path, 1024 * 1024)
    data = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs)
    source = data.get('jemalloc') if isinstance(data, dict) else None
    require(isinstance(source, dict), 'expected an exported jemalloc JSON report')
    stats = source.get('stats')
    require(isinstance(stats, dict), 'jemalloc aggregate stats missing')
    names = ('allocated', 'active', 'metadata', 'resident', 'mapped', 'retained')
    metrics = {name: stats[name] for name in names if name in stats}
    require('allocated' in metrics and all(type(value) is int and 0 <= value < 2**64
                                            for value in metrics.values()),
            'missing or invalid jemalloc byte counts')
    version = source.get('version')
    if version is not None:
        text(version, 128, 'jemalloc version')
    return {
        'schema': 'ressembly.allocator-summary.v1',
        'metadata': {'allocator': 'jemalloc', 'version': version,
                     'source_sha256': hashlib.sha256(raw).hexdigest()},
        'coverage': 'Supplied aggregate statistics, in bytes. A point sample can lag thread caches.',
        'bytes': metrics,
        'unavailable': [name for name in names if name not in metrics],
    }


def write_new(path, data):
    """Publish the full report once, without replacing any existing destination."""
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix='.ressembly-')
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(encoded(data) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        Path(temporary).unlink()
