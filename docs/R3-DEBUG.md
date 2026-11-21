# R3a/R3b — Debugger context and memory inspection

This local implementation requires GDB with Python, Linux x86-64, a native local connection, and a single stopped thread. It has no GEF or Pwndbg dependency. Validation ran on Debian 12 x86-64 with GDB 13.1 under QEMU TCG on an ARM64 Mac. The results apply to that environment.

## Usage

Start a fresh `gdb -nx` session with your own program. Set a breakpoint, run the program, and enter these commands while it is stopped:

```gdb
source /path/to/Ressembly/src/ressembly_debug.py
rs-context
rs-context --json
rs-maps
rs-dump 0xADDRESS 64
rs-search 0xADDRESS 4096 616263
rs-chain 0xADDRESS 8
```

Replace `0xADDRESS` with a decimal or hexadecimal address obtained using standard GDB commands. Ressembly's commands accept numeric addresses and reject C expressions, function calls, and assignments. The context view reads the newest frame of the selected thread and preserves the user's frame and thread selection. It shows eight instructions **forward from the current PC**, AMD64 general-purpose registers and EFLAGS, and eight stack words from RSP. The breakpoint view shows each breakpoint's number, type, declared location, enabled and pending state, whether it is temporary, and hit count. The view does not reconstruct call frames or instructions before the PC.

## API and provenance

`ressembly.debug_gdb.context_snapshot()` returns a dictionary with JSON schema `ressembly.debug-context.v1`. Each call assigns a new `snapshot_id`. The `metadata.run_id` combines the Linux boot ID, PID, and process start tick. Ressembly computes `metadata.executable_sha256` from the running executable opened through `/proc/PID/exe`. The snapshot records GDB, architecture, PID, thread, operating system, and argument settings. Argument settings are declared configuration. They do not establish which input the program consumed.

Read failures for registers, assembly, or stack appear in `errors` and mark the view `partial`. Requests after exit or without an active process are rejected. Each call reads registers and frame state again. Callbacks leave execution untouched. The snapshot does not track writes or accesses between stops.

## Measurable limits

- Maps come from the current `/proc/PID/maps`, with a 2 MiB text limit. Reading the executable to compute its hash has a 256 MiB limit.
- Dumps cover 1 to 4,096 bytes in a fully mapped and readable range. Pages without `r` permission are rejected even if ptrace could read them.
- Search requires an explicit range of 1 to 65,536 bytes and a hexadecimal pattern of 1 to 256 bytes. It returns up to 256 matches, including overlaps, and stops at the first unreadable segment with an explicit report. `bytes_read` measures the prefix read. `scanned_bytes` is unknown (`null`) when the result limit ends the search.
- Pointer chains interpret eight-byte little-endian words and allow a depth of 1 to 32. Explicit stop reasons are `null`, `cycle`, `depth_limit`, and `unreadable`. A word interpreted as an address may not represent a valid pointer in the program.
- Remote processes, core dumps, other operating systems and architectures, and multiple threads are rejected. Certification covers only the tested matrix.
- Snapshot differences report values at the observed points. They cannot identify the writing instruction or establish a vulnerability or exploitability. The binary hash identifies bytes and does not authenticate who produced the dossier.

## Repeatable validation

```sh
python3 -m unittest discover -s tests -p test_debug_core.py -v
python3 scripts/validate-debug-linux.py work/r3-debug-NEW
```

The second command requires Linux x86-64 and a new directory. The validator builds the project's C fixture with symbols and creates a copy with `strip --strip-all`. It uses the original symbols only to prepare numeric breakpoints for the stripped copy and runs GDB with `-nx`. It retains commands, GDB exit status, logs, snapshots, raw maps, and hashes of source code and tools. Independent references include `info registers`, `x/8i`, `x/8gx`, `x/64bx`, `info breakpoints`, `/proc` maps, and `info proc mappings`.

Checks cover two stops in the same run with distinct snapshots, changed bytes and pointer chain after continuing, enabled and disabled breakpoints, pending breakpoints, complete search, result caps, and a PROT_NONE boundary. They also cover chain cycles, null pointers, depth limits, unreadable addresses, invalid inputs, and no changes to registers or target execution by the inspection commands. The validation fixture checks that an intentionally invalid RSP is reported as unavailable stack data and then restores the register. Requests without a process and after exit must fail.

The independent replay is retained at `work/r3-debug-independent-001`, with the same three cases and 117 + 117 assertions.

## API sources consulted

- [GDB Frames in Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Frames-In-Python.html) documents the newest frame and register reads.
- [GDB Architectures in Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Architectures-In-Python.html) documents bounded disassembly from an address.
- [GDB Inferiors in Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Inferiors-In-Python.html) documents the selected process, connection, and memory reads.

The APIs were verified on the lab's actual GDB version. The online sources were consulted on November 13, 2026.

## Implementation result

`work/r3-debug-002/validation.json` recorded **PASS**. It contains two real sessions with 117 assertions each, one with symbols and one stripped, plus a session without an inferior rejected with expected GDB exit code 1. These are checks within three sessions rather than 235 separate programs. Four offline core tests passed. The tests caught an intentional mutation of pointer-chain termination (`work/review-r3-debug-mutation/result.txt`).

The `work/r3-debug-001` attempt is retained. The session with symbols passed, but the stripped fixture lost its executable permission. The validator's file copy was corrected and the entire test was rerun in a new directory. The failed attempt was excluded from validation. The coordinator recorded independent replay and integration review separately.
