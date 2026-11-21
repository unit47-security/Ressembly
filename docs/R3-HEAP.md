# R3c — read-only structural heap view

R6 extended the profile to Kali glibc 2.43-4. See [R6](R6.md) for layout and return-handling differences and the test matrix. The 2.36 results below are historical.

The adapter lives in `src/ressembly_heap_view.py` and `src/ressembly/heap_view_gdb.py`, with an independent core in `src/ressembly/heap_view.py`. It runs independently of GEF, Pwndbg, and Daybreak.

## Scope

The historical 2.36 profile reads a stopped, local Linux x86-64 process with one thread and matching debug symbols. It describes a selected chunk header, main arena fields, and bounded allocator lists. It distinguishes declared counts from readable nodes and reports why a traversal stopped. Possible reasons include a null or sentinel link, an observation limit, a cycle, misalignment, or unavailable memory.

The adapter checks the version of the loaded libc and verifies that debug types come from the same mapped library. Reports include the libc hash and GDB version. Layout information comes from the matching debug types. Missing or incompatible versions, types, or layouts are rejected. Remote targets, core files, and multiple arenas were outside the original profile.

The lab ran Debian 12, kernel 6.1.0-54-cloud-amd64, Debian glibc 2.36, GDB 13.1, and GDB Python 3.11 under QEMU TCG on an ARM64 Mac. The version number alone does not validate another build.

## Read-only inspection

The project-owned lab fixture offers stopped states for comparing the arena view with the debugger's own readout. A chunk selection expects a numeric user address. The command does not evaluate GDB expressions. Compare the role and order of nodes across runs, since absolute addresses can vary.

The terminal view also supports JSON in `ressembly.heap-structure.v1` format. The view does not install breakpoints, change memory or registers, or resume the process. A Python view instance describes one stop and should be recreated after the next stop.

## Validation

The verifier uses a fresh output directory on Linux x86-64 and retains source hashes, build output, GDB invocations, transcripts, exit statuses, and JSON. The 13 sessions compare fields and header bytes with independent GDB reads and cover malformed lists, unsupported versions, missing symbols, no running process, invalid limits and addresses, rejected expressions, and preservation of debugger state.

The normal fixture verified small and large allocations, progression across allocator lists, and retained pointers for comparison. The version-rejection case changes a symbol in the stopped owned fixture. It tests the rejection path and supplies no evidence about a second distribution.

`work/r3-heap-002` passed 13 of 13 sessions with explicit local-connection validation. The first run is in `work/r3-heap-001`. Four offline core tests passed. The independent repeat passed 13 of 13 sessions in `work/r3-heap-independent-001`. Supplementary checks and the integrated report preserve their outcomes separately. A new revision requires new evidence with final source hashes.

## Interpretation limits

The view is structural and describes one stop. Chunk flags and plausible alignment do not authenticate an address as part of a live allocation. Bounded forward traversals do not verify every linked-list relationship. A cycle or mismatched count is an observation about the readout and does not establish exploitable corruption. An allocator state sampled mid-operation may be transitional.

The limit is 1 through 256 nodes per list and at most 201 lists in the historical profile. The view does not reconstruct every allocation. For an mmap chunk, it interprets only a supplied header.

## Primary sources

- [glibc 2.36 malloc.c](https://github.com/bminor/glibc/blob/glibc-2.36/malloc/malloc.c), reviewed November 13, 2026.
- [GDB Python types](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Types-In-Python.html).
- [GDB Python inferiors](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Inferiors-In-Python.html). These APIs were used with GDB 13.1 in the lab.
