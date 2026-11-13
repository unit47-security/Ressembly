#!/usr/bin/env python3
"""Real GDB acquisition -> persistent dossier -> fresh-process reopen validation."""
import base64
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ressembly import experiments as ex


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'Linux x86-64 required')
    require(len(sys.argv) == 2, 'usage: validate-experiments-linux.py NEW_DIRECTORY')
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=False)
    report = {'scope': 'real Linux x86-64 GDB; host virtualization declared separately', 'checks': []}
    def check(name, value):
        require(value, name)
        report['checks'].append({'name': name, 'status': 'PASS'})
    def run(name, argv, expected=0):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        (out / (name + '.stdout')).write_text(result.stdout)
        (out / (name + '.stderr')).write_text(result.stderr)
        (out / (name + '.process.json')).write_text(json.dumps({'argv': argv, 'returncode': result.returncode}))
        require(result.returncode == expected, name + ': ' + result.stderr[-2000:])
        return result
    binary = out / 'experiments_lab'
    run('compile', ['cc', '-g3', '-O0', '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror',
                    str(ROOT / 'examples/experiments_lab.c'), '-o', str(binary)])
    for label, command in [('gdb-version', ['gdb', '--version']), ('kernel', ['uname', '-a']),
                           ('libc', ['getconf', 'GNU_LIBC_VERSION']), ('compiler', ['cc', '--version'])]:
        run(label, command)
    source_files = ['src/ressembly/experiments.py', 'src/ressembly/experiment_gdb.py',
                    'src/ressembly_experiment.py', 'src/ressembly/debug_gdb.py', 'src/ressembly/debug_core.py',
                    'scripts/ressembly-experiment.py', 'scripts/validate-experiments-linux.py',
                    'examples/experiments_lab.c']
    report['sources'] = {name: ex.digest((ROOT / name).read_bytes()) for name in source_files}
    report['target_sha256'] = ex.digest(binary.read_bytes())
    input_file = out / 'input.bin'; input_file.write_bytes(b'owned\x00\xffinput\n')
    dossier = out / 'experiment.json'
    cli = [sys.executable, str(ROOT / 'scripts/ressembly-experiment.py')]
    run('create', cli + ['create', str(dossier), str(binary), 'Owned persistent experiment'])
    run('input', cli + ['input', str(dossier), str(input_file), 'stdin candidate'])
    oracle = out / 'oracle.py'
    oracle.write_text('''import gdb, json
from pathlib import Path
records = []
def primitive():
    records.append(dict(pc=int(gdb.parse_and_eval('$pc')), rsp=int(gdb.parse_and_eval('$rsp')),
        stack=bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval('$rsp')),64)).hex(),
        stage=int(gdb.parse_and_eval('experiment_stage')),
        input=bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval('&experiment_input')),16)).hex(),
        count=int(gdb.parse_and_eval('experiment_count'))))
    Path(''' + repr(str(out / 'oracle.json')) + ''').write_text(json.dumps(records))
''')
    commands = ['set pagination off', 'set confirm off', 'file ' + json.dumps(str(binary)),
                'source ' + str(ROOT / 'src/ressembly_experiment.py'), 'source ' + str(oracle),
                'break experiment_checkpoint', 'run < ' + str(input_file), 'python primitive()',
                'python gdb.execute("rs-experiment-snapshot ' + str(dossier) +
                ' first %d 4" % int(gdb.parse_and_eval("&experiment_stage")))',
                'continue', 'python primitive()',
                'python gdb.execute("rs-experiment-snapshot ' + str(dossier) +
                ' second %d 4" % int(gdb.parse_and_eval("&experiment_stage")))',
                'rs-experiment-snapshot ' + str(dossier) + ' unreadable 1 4',
                'continue', 'run < ' + str(input_file),
                'rs-experiment-snapshot ' + str(dossier) + ' second-run', 'kill']
    script = out / 'capture.gdb'; script.write_text('\n'.join(commands) + '\n')
    run('capture', ['gdb', '-nx', '-q', '-batch', '-x', str(script)])
    data = ex.load(dossier); snapshots = data['snapshots']
    raw = json.loads((out / 'oracle.json').read_text())
    check('four real snapshots persisted', len(snapshots) == 4)
    check('two stops match independent registers and stack', len(raw) == 2 and all(
        item['payload']['registers']['rip'] == actual['pc']
        and item['payload']['registers']['rsp'] == actual['rsp']
        and item['payload']['stack']['hex'] == actual['stack']
        and int.from_bytes(bytes.fromhex(item['payload']['memory']['hex']), 'little') == actual['stage']
        for item, actual in zip(snapshots[:2], raw)))
    check('input actually read in owned lab against primitive oracle', all(
        actual['count'] == len(input_file.read_bytes()) and
        bytes.fromhex(actual['input'])[:actual['count']] == input_file.read_bytes() for actual in raw))
    check('unreadable region preserved as partial', snapshots[2]['payload']['status'] == 'partial'
          and snapshots[2]['payload']['memory']['status'] == 'unavailable')
    check('new execution has distinct run identity', snapshots[0]['run_id'] == snapshots[1]['run_id']
          and snapshots[3]['run_id'] != snapshots[0]['run_id'])
    for item in snapshots:
        check('build and provenance ' + item['label'], item['build_sha256'] == report['target_sha256']
              and item['provenance'] == 'gdb_context')
    run('note', cli + ['note', str(dossier), 'Unreadable region remains unknown',
                       '--snapshot', snapshots[2]['id']])
    compared = run('compare', cli + ['compare', str(dossier), snapshots[0]['id'],
                                    str(dossier), snapshots[1]['id']])
    check('comparison exposes observed memory change', any(
        item['section'] == 'memory' and item['left']['hex'] != item['right']['hex']
        for item in json.loads(compared.stdout)['differences']))
    exported = out / 'export.json'
    run('export', cli + ['export', str(dossier), str(exported)])
    reopened = json.loads(run('reopen-fresh-process', cli + ['show', str(exported)]).stdout)
    check('export reopens with identical notes inputs and snapshots', reopened == ex.load(dossier)
          and reopened['notes'][0]['snapshot_id'] == snapshots[2]['id']
          and base64.b64decode(reopened['inputs'][0]['base64']) == input_file.read_bytes())
    before = dossier.read_bytes()
    no_target = out / 'no-target.gdb'
    no_target.write_text('source ' + str(ROOT / 'src/ressembly_experiment.py') + '\n'
                        'rs-experiment-snapshot ' + str(dossier) + ' no-target\n')
    run('no-target', ['gdb', '-nx', '-q', '-batch', '-x', str(no_target)], 1)
    check('no target cannot append stale snapshot', dossier.read_bytes() == before)
    wrong = out / 'other-build'; wrong.write_bytes(b'not the target build')
    incompatible = out / 'incompatible.json'
    run('other-build', cli + ['create', str(incompatible), str(wrong), 'Other build'])
    wrong_script = out / 'wrong-build.gdb'
    wrong_script.write_text('\n'.join(commands[:7] + ['rs-experiment-snapshot ' + str(incompatible) + ' wrong'])+'\n')
    run('reject-build', ['gdb', '-nx', '-q', '-batch', '-x', str(wrong_script)], 1)
    check('live mismatched build rejected', not ex.load(incompatible)['snapshots'])
    run('reject-overwrite', cli + ['export', str(dossier), str(exported)], 1)
    check('existing export unchanged', ex.load(exported) == reopened)
    report['status'] = 'PASS'
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
