"""Run six owned R0 cases under GDB; captures observations, never vulnerability verdicts."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quoted(path):
    text = str(path)
    if '\n' in text or '\r' in text:
        raise ValueError('newline in path is unsupported')
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def commands(tool, binary, case, mode, profile='manual'):
    resume = 'pi gdb.execute("continue")' if tool == 'pwndbg' else 'continue'
    lines = [
        'set pagination off', 'set confirm off', 'set width 0',
        'set debuginfod enabled off', 'file ' + quoted(binary),
        'set args ' + case + ' ' + mode,
        'python import gdb, json', 'python _r0_exit=[]',
        'python gdb.events.exited.connect(lambda e: _r0_exit.append(getattr(e,"exit_code",None)))',
        'define r0sample', 'printf "R0_CHECKPOINT=%s\\n", label',
        'printf "R0_ADDRESS=%p R0_LENGTH=%lu\\n", rs_address, rs_length',
        'python print("R0_BYTES="+bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval("rs_address")),int(gdb.parse_and_eval("rs_length")))).hex())',
        'bt 3', 'info registers rip rax rdi', 'end']
    if tool == 'gef':
        lines += ['help gef', 'gef config context.enable False']
    elif tool == 'pwndbg':
        lines += ['help pwndbg', 'set context-sections',
                  'set gdb-workaround-stop-event disabled-deadlock']
    lines += ['echo R0_PLUGIN_READY\\n', 'break main', 'run']
    if profile == 'helper':
        lines += [{'gef': 'heap-analysis-helper', 'pwndbg': 'track-heap enable'}[tool]]
    lines += ['tbreak rs_checkpoint', resume, 'r0sample']
    if profile == 'manual':
        if case == 'uaf' and mode == 'bad':
            lines += ['tbreak rs_checkpoint', resume, 'r0sample']
        watch = {'buffer': 'watch -l *(unsigned char *)(rs_address+8)',
                 'pointer': 'watch -l *(unsigned long *)rs_address',
                 'uaf': 'rwatch -l *(unsigned char *)(rs_address+16)'}[case]
        lines += [watch, 'set $r0_watch = $bpnum', 'commands', 'silent', 'echo R0_WATCH_TRIGGER\\n',
                  'x/i $pc', 'bt 3', resume, 'end']
    lines += ['break rs_checkpoint', 'commands', 'silent', 'r0sample']
    if profile == 'manual':
        lines += ['python if gdb.parse_and_eval("label").string() in ("buffer-after","pointer-after","heap-live-after-access","heap-freed-after-access"): gdb.execute("disable %d" % int(gdb.parse_and_eval("$r0_watch")))']
    lines += [resume, 'end', resume,
              'python print("R0_EXIT_CODES="+json.dumps(_r0_exit))', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', choices=('gdb', 'gef', 'pwndbg'), default='gdb')
    parser.add_argument('--profile', choices=('manual', 'helper'), default='manual')
    parser.add_argument('--entry', type=Path, help='explicit local GEF/Pwndbg loader')
    parser.add_argument('--revision', help='full Git revision of extension checkout')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('live comparison requires Linux x86-64')
    revision = None
    if args.tool == 'gdb' and args.profile == 'helper':
        parser.error('helper profile requires GEF or Pwndbg')
    if args.tool == 'gdb' and (args.entry or args.revision):
        parser.error('plain GDB profile does not load an extension')
    if args.tool != 'gdb':
        if not args.entry or not args.revision:
            parser.error('extension requires --entry and --revision')
        args.entry = args.entry.resolve(strict=True)
        quoted(args.entry)  # Reject control newlines; source consumes the unquoted remainder.
        revision = subprocess.check_output(['git', '-C', str(args.entry.parent),
                                           'rev-parse', 'HEAD'], text=True).strip()
        if args.revision != revision:
            parser.error('extension checkout HEAD differs from --revision')
        if subprocess.check_output(['git', '-C', str(args.entry.parent), 'status', '--porcelain'], text=True).strip():
            parser.error('extension checkout is not clean')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'examples/r0/memory_cases.c'
    binary = out / 'memory_cases'
    compile_command = ['cc', '-std=c11', '-g3', '-O0', '-fno-omit-frame-pointer',
                       '-Wall', '-Wextra', str(source), '-o', str(binary)]
    compiled = subprocess.run(compile_command, text=True, capture_output=True)
    (out / 'compile.txt').write_text(compiled.stdout + compiled.stderr)
    compiled.check_returncode()
    metadata = dict(tool=args.tool, profile=args.profile, revision=revision,
                    entry=str(args.entry) if args.entry else None,
                    entry_sha256=digest(args.entry) if args.entry else None,
                    source_sha256=digest(source), binary_sha256=digest(binary),
                    platform=platform.platform(), libc_host=platform.libc_ver(),
                    gdb=subprocess.check_output(['gdb', '--version'], text=True),
                    compiler=subprocess.check_output(['cc', '--version'], text=True),
                    compile_command=compile_command, measurements='batch wall time, not human task time',
                    limitations=['No exploitability verdict; logical buffer case is not C out-of-bounds.',
                                 'UAF value/crash unspecified; a tool stop may prevent completion.'])
    rows = []
    for case in ('buffer', 'uaf', 'pointer'):
        for mode in ('good', 'bad'):
            name = case + '-' + mode
            script = out / (name + '.gdb')
            script.write_text(commands(args.tool, binary, case, mode, args.profile))
            invocation = ['gdb', '-nx', '-q', '-batch']
            if args.entry:
                invocation += ['-ex', 'source ' + str(args.entry)]
            invocation += ['-x', str(script)]
            started = time.monotonic()
            try:
                result = subprocess.run(invocation, text=True, capture_output=True, timeout=90)
                log, exit_code = result.stdout + result.stderr, result.returncode
            except subprocess.TimeoutExpired as exc:
                raw = (exc.stdout or b'') + (exc.stderr or b'')
                log = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw
                exit_code = None
            (out / (name + '.txt')).write_text(log)
            setup_failed = ('R0_PLUGIN_READY' not in log or any(marker in log for marker in
                ('Undefined command', 'Python Exception', 'DEADLOCK DETECTED', 'Traceback (most recent call last)',
                 'Error in sourced command file', 'ModuleNotFoundError')))
            rows.append(dict(case=case, control=mode == 'good', command=invocation,
                             setup_status='setup-error' if setup_failed else 'commands-observed',
                             watchpoint_triggers=log.count('R0_WATCH_TRIGGER'),
                             debugger_exit=exit_code, wall_seconds=time.monotonic()-started,
                             checkpoints=log.count('R0_CHECKPOINT='),
                             inferior_exit_observed='R0_EXIT_CODES=[0]' in log,
                             command_lines=sum(bool(line) for line in script.read_text().splitlines()),
                             verdict='raw_observation_requires_review'))
    (out / 'manifest.json').write_text(json.dumps(dict(metadata=metadata, runs=rows), indent=2)+'\n')
    print('Saved six raw sessions; inspect logs before comparing capabilities or correctness.')


if __name__ == '__main__':
    main()
