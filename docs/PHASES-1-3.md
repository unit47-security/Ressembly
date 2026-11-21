# Ressembly: completion through R3

November 13, 2026. Working copy: `/Users/user/Documents/ChatGPT/Ressembly`.

**R0, R1, R2, and all R3a–R3e modules were implemented and validated within the stated lab scope.** R4, the local alpha package, was outside that scope. The earlier “phases 1–3” label incorrectly referred to R1/R0/R2 and omitted R3. This report supersedes that label and retains the earlier results.

## Verified results

| Module | Delivery | Final tests |
|---|---|---|
| R0 | Practical comparison of GDB, GEF, and Pwndbg across three lab cases and their controls | 30 selected sessions and 30 independent repeats, all retained |
| R1a/R1b | Marker collector, JSON and terminal output, error and interruption handling, and separation of runs | 16 original and 16 independent tests, plus 16 regression tests after R3 |
| R2a/R2b | Selected malloc/free collection without allocator markers, object generations, and a hardware observation region | 22 original and 22 independent tests, a separate oracle, and three width spot checks, plus 22 regression tests after R3 |
| R3a/R3b | Assembly, breakpoints, registers, stack, maps, memory dumps, searches, and chains | Three sessions and three independent repeats. Each run checked 117 assertions on the symbolized target and 117 on the stripped target, plus rejection with no target loaded |
| R3c | Structural views of chunks, main_arena, fastbins, bins, and tcache | 13 original and 13 independent sessions, plus four additional Linux tests |
| R3d | Pattern utilities, offsets, and ELF properties | 44 original and 44 independent checks, plus 18 additional independent checks |
| R3e | Inputs, snapshots, notes, comparisons, export, and reopening | 14 original and 14 independent checks on the final code. A second reviewer reopened the data in a separate process and performed 10 checks |
| R2/R3 integration | One loader, simultaneous use of collector and views, and a combined dossier | Two sessions with 20 GDB checks each, plus two independent repeats with 20 checks each. Each session also verified exit, generations, free events, export, and rejection of a conflict with the historical marker collector |

Assertions, unit tests, and sessions count different things. The second reopening check was performed by a separate agent. A human usability study was considered for R4.

**Final local tests: 67 Python and 14 JavaScript, all passed.** These offline checks complement the GDB/Linux runs. Deliberate mutations in separate copies showed that the tests detected errors in object generations, chain termination, PIE classification, and build consistency. The tests did not measure a full mutation score. The 1,000 ELF mutations exercised a limited parser check.

## Environment and boundaries

- ARM64 Mac host with a locally extracted QEMU 11.1.3 full-system TCG runtime.
- Debian 12 x86-64 guest with kernel 6.1.0-54-cloud-amd64, glibc 2.36, GCC 12.2.0, and binutils 2.40.
- R1/R2/R3 used GDB 13.1 with embedded Python 3.11.2. R0 used a shared GDB 18.1/Python 3.13.11 runtime with comparison tool revisions pinned in the dossiers.
- One process and one thread. The initial heap view covers one arena with glibc 2.36 and matching debug symbols.

The tests ran actual Linux and GDB inside an emulated x86-64 guest. **Kali, native hardware, physical performance, multithreading, and other allocators or debuggers remain outside this validation scope.** GEF and Pwndbg were comparison tools. The results establish no competitive advantage or novelty.

The offline HTML prototype retains its synthetic data. The GDB/Python implementation is separate. This milestone covers the initial modules through R3. A mature suite with the breadth of GEF or Pwndbg and a distributed installable release remained future work at this point.

## Interpreting the evidence

Allocator events record allocation and free. Observed value changes cover only the selected hardware region. A write that leaves the same value may be absent. Coverage ends before free and does not carry over automatically when an address is reused. The next object has a new generation. A program counter sampled after an instruction does not by itself identify the instruction responsible for the change.

The heap view is a structural snapshot. `PREV_INUSE` describes the preceding chunk. Forward chains have limits, and backward and nextsize links are unverified. Memory reads, searches, and pointer walks have explicit budgets and report missing data.

Static ELF properties describe the file. A canary symbol does not prove coverage of every function. Individual findings cannot establish a vulnerability or exploitability.

Reopening an experiment loads its dossier. Recorded inputs may not have been consumed by a process. Imports reject incompatible builds and contradictory internal identities. Process IDs and capture UUIDs belong to different identity domains. A comparison reports `same_run: null` when they cannot be compared directly. Hashes and consistent JSON establish internal consistency only.

## Defects found and fixed

Earlier validation fixed `source` quoting, run merging, validator exit codes, unsigned register handling, missing returns, unsupported calloc/realloc handling, and watchpoint budgets. R3 fixed a fixture that lost permissions on its stripped copy, a dossier import that accepted contradictory inner and outer metadata for context and R1/R2 histories, and the comparison label used for different identity domains. Each fix was checked afterward. Intermediate and failed attempts remain available as historical records.

## Final local dossiers

| Group | Author run | Independent run |
|---|---|---|
| Debugger and memory | `work/r3-debug-002` | `work/r3-debug-independent-001` |
| Structural heap | `work/r3-heap-002` | `work/r3-heap-independent-001` |
| Lab utilities | `work/r3-labtools-001` | `work/r3-labtools-independent-001` |
| Experiments | `work/r3-experiments-004` | `work/r3-experiments-independent-003` |
| Integrated suite | `work/r3-suite-003` | `work/r3-suite-independent-002` |

Additional dossiers: `work/r3-heap-review-probes-002`, `work/r3-labtools-review-probes-001`, `work/review-r3-experiments`, and `work/r3-integration-review-002`. Regression dossiers: `work/r3-r1-regression-001` and `work/r3-r2-regression-001`. Summary and hashes: `work/r3-gates/`.

Retained earlier dossiers under `work/validation/` include `r1-validation-005`, `r1-independent-001`, `r0/`, `r0-independent/`, `r2-validation-003`, `r2-independent-001`, `r2-primitive-oracle-001`, and `r2-widths/`. The earlier `work/gates/acceptance.json` covered R0/R1/R2.

Usage and reproduction guide: [R3.md](R3.md). Detailed records: [R1](R1-VALIDATION.md), [R0](R0-RESULTS.md), [R2](R2.md), [debugger and memory](R3-DEBUG.md), [heap](R3-HEAP.md), [lab utilities](R3-LABTOOLS.md), and [experiments](R3-EXPERIMENTS.md).

## Retention and next milestone

The original at `/Users/user/Documents/Codex/Projects/Ressembly`, the prototype, and the historical files were retained. This milestone introduced no Daybreak dependency, paid service, mandatory AI, publication, push, or global Mac configuration change. The local VM shut down cleanly. Its process exited, and the serial log confirms this in `work/r3-gates/lab-final-state.json`. `work/` contains lab-only credentials and images and is excluded from distribution.

**The next milestone was R4.** It covered a local alpha package, clean installation and removal, a Kali compatibility matrix, a guide, and a license decision. It was a separate milestone requiring its own validation and publication approval.
