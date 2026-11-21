# Ressembly current and historical validation

## Completion through R3 on November 13, 2026

R3a–R3e were completed and validated in the Debian 12 x86-64 lab under QEMU TCG on the ARM64 Mac, with GDB 13.1 and glibc 2.36. R4 had yet to begin at this point. The previous informal “phases 1–3” label covered R1/R0/R2 only. This report corrects the stated scope.

| Module | Final and independent tests |
|---|---|
| R3a/b | Three original and three independent sessions, with 117 assertions each on the symbolized and stripped targets per run |
| R3c | 13 original and 13 independent sessions, plus four additional tests |
| R3d | 44 original and 44 independent checks, plus 18 independent follow-up checks |
| R3e | 14 original and 14 independent checks, plus reopening by a separate reviewer |
| Integration | Two workflows with 20 GDB checks each, repeated independently, plus history and export checks |
| Regression | R1 passed 16/16 and R2 passed 22/22 after integration |
| Local tests | 67 Python and 14 JavaScript tests passed |

Final dossiers and boundaries are in [PHASES-1-3.md](PHASES-1-3.md). The aggregate record is `work/r3-gates/acceptance.json`. See [R3.md](R3.md) for the guides. The integration fixed contradictions between build and run metadata and corrected comparisons across different identity domains. Final regression and repeat runs were retained. A pass establishes only the scope of the corresponding test. Authenticity, exploitability, native performance, and tool superiority require separate evidence.

The earlier records below retain their original test counts and historical scope.

## Earlier R0, R1, and R2 validation on November 13, 2026

**Validated in the Debian 12 x86-64 lab emulated with QEMU TCG on the ARM64 Mac.** Native hardware and Kali were outside this validation. See the [combined report](PHASES-1-3.md).

| Milestone | Observed result | Local evidence |
|---|---|---|
| R1a/R1b | 16/16 live tests passed, followed by 16/16 independent repeats | `work/validation/r1-validation-005`, `r1-independent-001` |
| Practical R0 comparison | 30 selected sessions and 30 independent repeats | `work/validation/r0`, `r0-independent` |
| R2a/R2b | 22/22 live tests and 22/22 independent repeats | `work/validation/r2-validation-003`, `r2-independent-001` |
| R2 region oracle | GDB without Ressembly recorded two A/B value changes. Rewriting the same value did not produce a value-change event | `work/validation/r2-primitive-oracle-001` |
| Additional widths | 2, 4, and 8 bytes, checking offset 0 and the first changed byte. Other offsets and bytes were outside the spot checks | `work/validation/r2-widths` |
| Final offline tests | 39 Python and 14 JavaScript tests passed. Python and shell syntax checks passed | `work/gates/python-tests-final.txt`, `javascript-tests-final.txt` |

R1/R2 used GDB 13.1, Python 3.11.2, and glibc 2.36. R0 used a shared GDB 18.1/Python 3.13.11 runtime, pinned tool checkouts, and targets on the same guest. Validated source hashes matched the corresponding files. A separate review corrected validator exit codes, the realloc guard, and the watch budget state. It found no remaining blocking defect within the declared scope. Tests caught a deliberate mutation of generations in a temporary copy. Production code was unaffected by that test.

Failed attempts and pilots are retained and excluded from valid results. Recorded times cover whole subprocess runs in the emulated guest. Isolated overhead and native hardware performance remain unmeasured. The results establish no novelty, superiority, or exploitability. Allocator events and value changes in the one observed region are separate evidence. Same-value writes and data outside that region remain unknown.

The validation above closes the earlier Linux checks within its stated scope. The newer record at the top covers R3, which remained outside this earlier check. Native hardware, Kali, other allocators, and multithreading remained outside the R0–R2 scope.

The November 13 update retains the October 24 checks below as a historical record.

## Lab verifier update

The working directory was `/Users/user/Documents/ChatGPT/Ressembly`, copied from `/Users/user/Documents/Codex/Projects/Ressembly`. The original was preserved and its historical `work/` directory was excluded from the copy. This change concerned the verifier. The collector, core, C fixture, and prototype were unaffected.

**Reproduced defect:** the earlier verifier accepted an incomplete offline capture when Python ran with optimization enabled. It returned exit code 0 and described the file as a real capture. The same file failed without optimization. GDB was outside this test.

**Implemented fix:** explicit checks independent of `assert` validate the seven markers in the fixture, sequence and declared provenance, generation-based identities, sample bytes, differences and sizes, and the final object table. Malformed JSON, duplicate keys, nonfinite numbers, and files over 2 MiB are rejected. Incorrect invocation exits 2. Invalid or unreadable input exits 1. A pass establishes consistency with the fixture's expectations. Authenticity, real acquisition, and general suite format validation are outside the verifier's scope.

**Checks run in this session:**

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v` passed 18 tests, nine historical and nine new, with additional cases within tests. Covered normal and optimized CLI runs, fixtures with and without address reuse, partial and error states, and missing, inconsistent, and oversized inputs.
- `node --test tests/core.test.cjs` passed 14 tests.
- The C fixture compiled with `cc -std=c11 -g3 -O0 -fno-omit-frame-pointer -Wall -Wextra -Werror` and exited 0 on the ARM64 Mac. Its output explicitly identified a non-glibc environment.
- Python syntax was checked without importing GDB. `sh -n scripts/run-marker-lab.sh` passed. The Mac runner returned the expected exit code 2 without producing a Linux capture.
- Reversing the schema check in a temporary copy made the tests fail. The copy was removed afterward.
- A separate agent found no blocking defect in the reviewed scope and reran all 18 Python tests successfully. The review was static and offline.
- Hash comparison confirmed retention of the original and unchanged prototype and earlier tests.

This update introduced no Daybreak or other external dependency. It made no push, publication, or global configuration change. Build, run, and libc metadata remain file declarations. At this point, actual Linux x86-64 GDB sessions, competing tool benchmarks, overhead, allocator hooks, and watchpoints **had not been tested**.

## October 24, 2026 record

## Observed R1a results

- Nine offline Python tests passed. They cover generations on address reuse, failed allocation, unknown or null free, bounded immutable samples, read failure, duplicate allocation, event budgets, invalid input, and rendering errors without context.
- All 14 historical JavaScript tests passed on repeat. JavaScript syntax checks passed for the app and demo.
- The C fixture compiled with Apple clang 17 and `-std=c11 -g3 -O0 -fno-omit-frame-pointer -Wall -Wextra -Werror`. It exited 0 on the ARM64 Mac and explicitly reported a non-glibc environment. Linux and glibc remained outside this test.
- Python and shell syntax checks passed. The live script rejected the Mac with its expected exit code 2 and generated no capture.
- Prototype and historical test hashes matched before and after.
- Integrated review fixed quoting of the GDB Python check and rendering errors that lack addresses. The runtime adapter could not be tested because GDB was unavailable.

**Not run at the time:** GDB sessions, manual byte comparisons, debugger interruption tests, Linux or Kali x86-64 lab runs, competing tool benchmarks, overhead, watchpoints, and allocator hooks. Offline JSON fixtures remained labeled as synthetic. No GDB or glibc version was claimed as supported in production.

See [R1A.md](R1A.md) for the workflow and acceptance criteria, and the [October 24 audit](AUDIT-2026-10-24.md) for evidence classification. R0 documentation review was partial. R1a was implemented with operational validation still open. R1 and R2 were incomplete at that time.

## Historical HTML prototype record

The following sections concern the historical Windows prototype. The current Linux backlog is separate.

## Verified

- `node --test tests/core.test.cjs` passed 14 tests with zero failures and zero skips.
- Syntax checks passed for `prototype/core.js`, `prototype/app.js`, and `prototype/demo-data.js`.
- Tests cover ASLR, symbol collisions, separate modules, incompatible builds, different scopes, partial data, dropped events, provenance, event and thread references, invalid RVAs, unsorted sequences, and verification that the bundle is not mutated.
- The prototype has no external JavaScript dependency or cloud service, and imported data is not executed.

## Validation pending in later milestones

Windows x64 collection, real x64dbg sessions, register and memory captures, automated native trace imports, Ghidra connection, large file support, and measurements with users were outside M0.

## Interface QA

The preview opened in a local browser and was readable. Its indicators showed three B-only functions, two shared functions, and 2/6 entries. The B-only filter left exactly three rows. The initial detail showed B / event #3. End-to-end validation of import, export, and other interactions remained incomplete. No Windows desktop build was run. The temporary preview server was stopped. The files remained available locally.

## R4/R5 update on November 13, 2026

The earlier completion through R3 is historical. The [R4/R5 report](PHASES-4-5.md) records the added code, Linux and Ghidra evidence, Kali compatibility by module, human trial, and limits. The final package required a separate check from the pilots. Hashes and `validation.json` files were kept outside the package. VM cleanup was authorized after testing, and the evidence was retained on the host.

## R6 update on November 13, 2026

The Kali glibc 2.43-4 profile passed 24 live groups. Regression testing of a glibc 2.36 target in an isolated sysroot covered 16 groups. Both included the nested R2 set of 22 cases and R5 set of 14 cases. The run passed 97 Python and 14 JavaScript tests. It used a separate GDB oracle, caught a deliberate mutation, and verified the version probe and helper stop. See the [R6 report](R6.md). Package acceptance, independent repetition, and completed cleanup are recorded in `work/r6-gates/acceptance.json`. Native performance was not established. This milestone involved no publication at that point.
