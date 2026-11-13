#!/usr/bin/env python3
"""Build an exclusive, deterministic local ZIP from the allowlisted project files."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packaging'))
import local_package


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',help='new ZIP file; existing files are refused')
    args=parser.parse_args()
    try:
        manifest=local_package.build(ROOT,args.output)
        print(json.dumps({'status':'built','version':manifest['version'],
                          'file_count':len(manifest['files']),'output':str(Path(args.output).absolute())},indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError) as error:
        print('Ressembly package: '+str(error),file=sys.stderr); return 1

if __name__=='__main__': sys.exit(main())
