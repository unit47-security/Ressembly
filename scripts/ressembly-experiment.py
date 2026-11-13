#!/usr/bin/env python3
"""Manage a local evidence dossier without executing stored inputs or commands."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ressembly import experiments as ex


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create')
    create.add_argument('dossier'); create.add_argument('binary'); create.add_argument('title')
    show = commands.add_parser('show')
    show.add_argument('dossier')
    inputs = commands.add_parser('input')
    inputs.add_argument('dossier'); inputs.add_argument('file'); inputs.add_argument('label')
    snapshot = commands.add_parser('import-snapshot')
    snapshot.add_argument('dossier'); snapshot.add_argument('file')
    snapshot.add_argument('build_sha256'); snapshot.add_argument('run_id'); snapshot.add_argument('label')
    note = commands.add_parser('note')
    note.add_argument('dossier'); note.add_argument('text'); note.add_argument('--snapshot')
    compare = commands.add_parser('compare')
    compare.add_argument('left'); compare.add_argument('left_id')
    compare.add_argument('right'); compare.add_argument('right_id')
    export = commands.add_parser('export')
    export.add_argument('dossier'); export.add_argument('destination')
    args = parser.parse_args()
    try:
        if args.command == 'create':
            result = ex.create(args.dossier, args.binary, args.title)
        elif args.command == 'show':
            result = ex.load(args.dossier)
        elif args.command == 'input':
            result = {'input_id': ex.add_input(args.dossier, args.file, args.label)}
        elif args.command == 'import-snapshot':
            result = {'snapshot_id': ex.add_snapshot(args.dossier, ex.read_json(args.file, ex.MAX_SNAPSHOT),
                      args.build_sha256, args.run_id, args.label)}
        elif args.command == 'note':
            result = {'note_id': ex.add_note(args.dossier, args.text, args.snapshot)}
        elif args.command == 'compare':
            result = ex.compare(args.left, args.left_id, args.right, args.right_id)
        else:
            result = ex.export(args.dossier, args.destination)
        print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
        print('Ressembly experiment: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
