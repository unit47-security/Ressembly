#!/usr/bin/env python3
"""Collect cooperative diagnostics from a built-in workload or import allocator statistics."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import multiprocessing as mp
from pathlib import Path
import sys
from threading import Barrier
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ressembly import diagnostics


def serve_viewer(port):
    """Serve only the four viewer assets on loopback. Imports stay in the browser."""
    viewer = Path(__file__).resolve().parents[1] / 'viewer'
    assets = {}
    for name, media in (('index.html', 'text/html'), ('style.css', 'text/css'),
                        ('model.js', 'text/javascript'), ('app.js', 'text/javascript')):
        assets['/' + name] = (media, (viewer / name).read_bytes())
    assets['/'] = assets['/index.html']

    class ViewerRequest(BaseHTTPRequestHandler):
        def reply(self, include_body):
            asset = assets.get(self.path)
            if asset is None:
                self.send_error(404)
                return
            media, body = asset
            self.send_response(200)
            self.send_header('Content-Type', media + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def do_GET(self):
            self.reply(True)

        def do_HEAD(self):
            self.reply(False)

        def log_message(self, format, *args):
            pass

    with ThreadingHTTPServer(('127.0.0.1', port), ViewerRequest) as server:
        print('http://127.0.0.1:%d/' % server.server_port, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def worker(label, parent_id, sender):
    with sender:
        log = diagnostics.ProcessLog(label, parent_id)
        barrier = Barrier(2, timeout=3)

        def phase(name):
            with log.thread(name):
                barrier.wait()

        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks = [pool.submit(phase, 'thread-' + str(index)) for index in (1, 2)]
            for task in tasks:
                task.result()
        sender.send(log.close())


def demo(method):
    context = mp.get_context(method)
    parent = diagnostics.ProcessLog('supervisor')
    children = []
    expires = time.monotonic() + 12
    records = []
    outcomes = []
    try:
        # Start every child before any application thread work.
        for index in (1, 2):
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(target=worker, args=('worker-' + str(index), parent.identity, sender))
            try:
                with sender:
                    process.start()
            except BaseException:
                receiver.close()
                raise
            children.append((process, receiver))
        for process, receiver in children:
            if not receiver.poll(max(0, expires - time.monotonic())):
                raise ValueError('worker report timed out')
            record = receiver.recv()
            process.join(max(0, expires - time.monotonic()))
            diagnostics.require(process.exitcode == 0 and record['pid'] == process.pid,
                                'worker did not exit cleanly with a matching report')
            records.append(record)
            outcomes.append({'id': record['id'], 'pid': process.pid, 'exit_code': process.exitcode})
    finally:
        remaining = []
        for process, receiver in children:
            receiver.close()
            if process.is_alive():
                process.terminate()
                process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            if process.is_alive():
                remaining.append(process.pid)
            else:
                process.close()
        if remaining:
            raise RuntimeError('owned workers could not be stopped: ' + str(remaining))
    return diagnostics.report(uuid4().hex, method, [parent.close(), *records], outcomes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    demo_parser = commands.add_parser('demo', help='run two owned workers with two threads each')
    demo_parser.add_argument('output', type=Path)
    demo_parser.add_argument('--method', choices=mp.get_all_start_methods(), default='spawn')
    jemalloc = commands.add_parser('jemalloc', help='import aggregate jemalloc JSON statistics')
    jemalloc.add_argument('input', type=Path)
    jemalloc.add_argument('output', type=Path)
    viewer = commands.add_parser('viewer', help='serve the viewer on loopback until Ctrl-C')
    viewer.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    try:
        if args.command == 'viewer':
            diagnostics.require(0 <= args.port <= 65535, 'port must be between 0 and 65535')
            return serve_viewer(args.port)
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError('output already exists: ' + str(args.output))
        result = demo(args.method) if args.command == 'demo' else diagnostics.jemalloc_summary(args.input)
        diagnostics.write_new(args.output, result)
        print(args.output)
        return 0
    except (ValueError, OSError, EOFError, RuntimeError, RecursionError) as error:
        print('Ressembly diagnostics: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
