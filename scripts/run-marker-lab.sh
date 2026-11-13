#!/bin/sh
# One local acquisition. No dependencies beyond cc, GDB with Python, Python 3.
set -eu
if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
    echo 'Live acquisition requires Linux x86-64; no live result was produced.' >&2
    exit 2
fi
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${1:-"$ROOT/work/marker-lab"}
if [ -e "$OUT" ]; then
    echo 'Output directory exists; choose a new directory to preserve captures.' >&2
    exit 2
fi
mkdir -p "$OUT"
OUT=$(CDPATH= cd -- "$OUT" && pwd)
# Keep shell/GDB filename quoting unambiguous. GDB source consumes its raw path.
case "$ROOT$OUT" in *'"'*|*'\'* ) echo 'Unsupported quote or backslash in path' >&2; exit 2;; esac
uname -a >"$OUT/platform.txt"
cc --version >"$OUT/compiler.txt"
gdb --version >"$OUT/gdb.txt"
getconf GNU_LIBC_VERSION >"$OUT/libc.txt"
gdb -nx -q -batch -ex "python import sys; print(sys.version)" >"$OUT/gdb-python.txt"
cc -std=c11 -g3 -O0 -fno-omit-frame-pointer -Wall -Wextra -Werror \
    "$ROOT/examples/marker_lab.c" -o "$OUT/marker_lab"
gdb -nx -q -batch "$OUT/marker_lab" \
    -ex "source $ROOT/src/ressembly_gdb.py" \
    -ex "rs-start \"$OUT/history.json\"" -ex run -ex rs-show -ex rs-save >"$OUT/session.txt" 2>&1
python3 "$ROOT/scripts/verify-marker-history.py" "$OUT/history.json"
cat "$OUT/session.txt"
