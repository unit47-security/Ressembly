# R0 technical comparison results

November 13, 2026. The experiments ran project-owned fixtures in a Linux x86-64 VM emulated locally with QEMU TCG on an ARM64 Mac. The results cover this technical test matrix. Native hardware performance, human usability, and competitive superiority remain unverified. See the [fixture scope](R0-LABS.md).

## Environment and identification

- Debian 12 with kernel `6.1.0-54-cloud-amd64` and glibc 2.36.
- All 30 selected sessions used `GNU gdb (GDB) 18.1` from the official Pwndbg portable package `2026.10.28`, with Python 3.13.11. The portable package provided GDB. The Pwndbg loader used the pinned checkout listed below.
- The provisioning record lists SHA-256 `17049a23ba8cbcf4780c4bc9b4aeb519f2801ceabe7304b55d3d622acca03b8c` for the portable package.
- GEF revision `809864d00442f9993298e33fd9cd282d687d2f45` and Pwndbg revision `9760ac8f1346d142857cffc933995cd6fca34dff`.
- Profile manifests record source and loader hashes, binary identities, compiler, GDB, host libc, verified HEAD, and the commands used. The checkouts were clean at startup. The comparison tools were in the lab's `work/` directory.

## Retained evidence

Directories under `work/validation/r0/`:

| Selected profile | Sessions |
|---|---:|
| `r0-gdb-manual-002` | 6 |
| `r0-gef-manual-002` | 6 |
| `r0-pwndbg-manual-003` | 6 |
| `r0-gef-helper-002` | 6 |
| `r0-pwndbg-helper-003` | 6 |

All 30 selected sessions observed exit code 0 from the inferior, the expected checkpoints, and none of the setup error signals checked by the runner. The matrix is in `summary.json`. `scripts/r0/verify-results.py` reported `consistent_30_raw_sessions`. It rejected a temporary negative-control copy with an altered trigger count. See `negative-control.txt`. These checks establish file consistency. The observed execution is recorded separately in the session logs.

## Independent repeat

A separate agent repeated 30 sessions using the same five profiles and fresh directories under `work/validation/r0-independent/`. The runner, verifier, and host and guest C source matched the recorded hashes. Verifiers in both the guest and host returned `consistent_30_raw_sessions`. Checkpoints, samples, and trigger counts matched the first matrix. The two runs total 60 valid sessions.

## Common manual comparison

All three tools used the same watchpoint scope. Samples and backtraces were retained before and after each case. The three columns count observations in the selected region and lifetime window.

| Case | GDB | GEF | Pwndbg | Verified observation |
|---|---:|---:|---:|---|
| Buffer control | 0 | 0 | 0 | The logical boundary sentinel stayed unchanged |
| Buffer variation | 1 | 1 | 1 | The logical boundary sentinel changed inside valid C storage |
| Pointer control | 0 | 0 | 0 | The slot retained its pointer to the first harmless function |
| Pointer variation | 1 | 1 | 1 | The slot held a pointer to the second harmless function afterward |
| Heap read control | 1 | 1 | 1 | The read occurred while the allocation was live |
| Heap read variation | 1 | 1 | 1 | The read was observed after the recorded free checkpoint |

The two heap cases produce the same trigger count. Their recorded lifecycle distinguishes them. The buffer variation crosses a logical boundary within a valid C array. The comparison therefore makes no claim about whether a heap helper should detect that change. The matrix verifier checked the recorded samples and pointer-slot changes. The post-free read value was outside the deterministic checks.

## Tool-specific helpers

The GEF heap analysis helper and Pwndbg heap tracker ran in separate profiles from the manual watchpoints. Both logged allocation and free events in the heap cases. Neither helper stopped on the particular read-only event after free, and each helper session reached the expected checkpoints and exit code 0. The pinned versions use value-change watchpoints. GEF and Pwndbg differed in the extent of the region they watched, so the GEF result does not isolate spatial coverage from read-only behavior. This finding applies only to the tested access and profiles. It neither establishes a tool bug nor demonstrates a new Ressembly technique.

Address reuse and object generations belong to the separate R2 validation gate. R0 did not measure complete allocator or write coverage.

## Recorded timing and command counts

The table covers the first matrix with one run per combination. The emulated lab may have been running other work at the same time. Independent repetition is recorded separately. Timings include startup, loader, debugger, and target.

| Profile | Batch median (seconds) | Range (seconds) | Nonempty command lines per case |
|---|---:|---:|---:|
| GDB manual | 1.294 | 1.266–1.409 | 40 or 43 |
| GEF manual | 2.747 | 2.692–2.795 | 42 or 45 |
| Pwndbg manual | 9.062 | 8.313–9.516 | 43 or 46 |
| GEF helper | 3.125 | 2.748–4.112 | 33 |
| Pwndbg helper | 9.767 | 9.005–11.866 | 34 |

Line counts include definitions and save commands. They do not measure an analyst's actions or time. Repeated timings, analysis of variability and ordering, and a human comparison would be needed to establish performance or usability gains.

## Excluded pilots and lab fixes

The `*-001` dossiers are pilots. GEF failed to load because of `source` quoting, and the initial manual GDB run left a watchpoint beyond the final checkpoint, observing later stack reuse. The results are retained and excluded from the corpus results.

The Pwndbg `*-002` profiles reached exit code 0 but reported `DEADLOCK DETECTED` and `SystemExit` with the GDB `commands`/`continue` flow. Those runs were classified as `setup-error` and excluded. The 003 profiles used Pwndbg's documented compatibility workaround, `disabled-deadlock` with resume through Python, and completed without those exceptions. Logs and scripts record the configuration difference. The portable runtime produced libthread_db warnings in some GDB and GEF sessions in this single-threaded lab. Multithreaded behavior remains outside the evidence.

## Decision and validation boundary

Existing workflows already observe the selected changes. The concrete R2 feasibility question is whether it can **retain a verifiable link between allocator events, allocation generations, and observations of a selected region**. A trigger by itself does not establish a diagnosis. Added usefulness, originality, and comparative advantage remain unproven. If R2 review shows no practical gain, revisit its priority or design before expanding.

R0 now has a repeatable technical matrix within the stated scope. Human benefits, native hardware, Kali, other allocators and versions, and general vulnerability detection remain outside this validation.
