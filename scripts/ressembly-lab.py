#!/usr/bin/env python3
"""Local bounded lab utilities. No target execution."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ressembly.labtools import cyclic, cyclic_offset, elf_properties


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    pattern = sub.add_parser('pattern')
    pattern.add_argument('length', type=int)
    pattern.add_argument('--output', type=Path, help='new file, never overwrite')
    offset = sub.add_parser('offset')
    query = offset.add_mutually_exclusive_group(required=True)
    query.add_argument('--hex', help='exact observed bytes, not an integer')
    query.add_argument('--integer', type=lambda x: int(x, 0))
    offset.add_argument('--length', type=int, required=True, help='length of the generated prefix to search')
    offset.add_argument('--endian', choices=['little', 'big'], default='little')
    for command in (pattern, offset):
        command.add_argument('--width', type=int, default=4)
        command.add_argument('--alphabet', default='abcdefghijklmnopqrstuvwxyz', help='distinct ASCII bytes')
    elf = sub.add_parser('elf')
    elf.add_argument('path', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'elf':
            result = elf_properties(args.path)
        elif args.command == 'pattern':
            result = cyclic(args.length, args.width, args.alphabet.encode('ascii'))
            if args.output:
                with args.output.open('xb') as stream:
                    stream.write(result)
            else:
                sys.stdout.buffer.write(result)
            return 0
        else:
            value = bytes.fromhex(args.hex) if args.hex is not None else args.integer
            result = cyclic_offset(value, args.length, args.width, args.endian, args.alphabet.encode('ascii'))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError) as error:
        print('ressembly-lab: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
