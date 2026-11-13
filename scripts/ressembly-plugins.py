#!/usr/bin/env python3
"""Inspect or explicitly run a trusted local plugin; never auto-download plugins."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ressembly import plugins
from ressembly.experiments import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    inspect = sub.add_parser('inspect'); inspect.add_argument('directory')
    run = sub.add_parser('run'); run.add_argument('directory'); run.add_argument('snapshot')
    run.add_argument('--trust-sha256', required=True); run.add_argument('--output')
    args = parser.parse_args()
    try:
        result = plugins.describe(args.directory) if args.action == 'inspect' else plugins.run(
            args.directory, args.trust_sha256, read_json(args.snapshot, plugins.MAX_DATA))
        content = json.dumps(result, indent=2, ensure_ascii=True) + '\n'
        if args.action == 'run' and args.output:
            with open(args.output, 'x') as stream: stream.write(content)
        else:
            print(content, end='')
        return 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        print('Ressembly plugins: ' + str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
