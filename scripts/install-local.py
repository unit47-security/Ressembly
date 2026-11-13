#!/usr/bin/env python3
"""Install, verify or uninstall a local Ressembly bundle in an explicit user prefix."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packaging'))
import local_package


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    install=sub.add_parser('install'); install.add_argument('archive'); install.add_argument('prefix')
    for name in ('verify','uninstall'):
        sub.add_parser(name).add_argument('prefix')
    args=parser.parse_args()
    try:
        if args.action=='install': result=local_package.install(args.archive,args.prefix)
        elif args.action=='verify': result=local_package.verify(args.prefix)
        else: result=local_package.uninstall(args.prefix)
        print(json.dumps({'status':args.action+' complete','result':result},indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError) as error:
        print('Ressembly package: '+str(error),file=sys.stderr); return 1

if __name__=='__main__': sys.exit(main())
