# R0 — comparison corpus

The corpus used project-owned, single-process, single-thread C fixtures with debug symbols and optimizations disabled. The runner and fixtures are part of the development lab. Ressembly has no runtime dependency on the compared tools, Daybreak, an external service, or an automatic download.

| Case | Control | Test variant | Interpretation |
|---|---|---|---|
| Buffer | Writes only within the logical buffer | Changes the logical sentinel within the same C object | A change in the sentinel is observable. It is not evidence of a write beyond the C object. |
| Object lifetime | Reads a live object before freeing it | Attempts a read after the object has been freed | This variant intentionally exercises undefined behavior in the owned fixture. A returned value, crash, or reuse is not guaranteed. A checkpoint distinguishes whether the object was live. |
| Pointer | Keeps a pointer to one owned benign function | Selects a second owned benign function | The two functions yield different known results. The fixture accepts no external address. |

The fixture's checkpoints identify selected memory and the stage of execution. The runner captures bounded bytes, backtraces, and registers. Bytes left at a freed address are not treated as live object contents. Tests do not require a specific stale value or draw conclusions about exploitability.

## Linux x86-64 test environment

The comparison used an authorized glibc lab with Python-enabled GDB, a C compiler, and Python 3. GEF and Pwndbg were prepared separately from the runner. The lab recorded their full revisions and required clean checkouts. Each session used a fresh output directory and a GDB invocation isolated from the user's initialization files.

The shared manual profile recorded selected checkpoints and watchpoint stops across tools. The helper profile tested each tool's own diagnostic helper separately. Recorded program counters and backtraces describe where execution stopped. Attribution of a write requires checking the semantics of the observed stop.

The dossier records source and binary SHA-256 hashes, loader hashes, tool revisions, compiler and GDB versions, host and libc, six logs, and a JSON manifest. Elapsed batch time includes debugger startup and does not measure analyst time or collector overhead in isolation. The line count of the generated script does not measure manual effort. Report the emulation backend separately from hardware measurements.

The runner records observations. A `setup-error` status means a loader or command was not observed or that the log contains an error, even when GDB exits successfully. `commands-observed` reports command execution and does not certify a detection. If `inferior_exit_observed` is false, the run did not observe a clean target exit. An earlier stop may explain that result. The manifest also records debugger exit status, timeouts, signals, and early stops. The per-session timeout is 90 seconds.

## R0 review criteria

The review compares available information, stop locations, allocation and free events, address reuse and object identity, sampled bytes, missing writes, false signals, and analyst effort for all six cases. It records tool versions and any additional manual steps. Measuring an analyst benefit would require separate trials with the task order alternated. The corpus alone establishes neither novelty nor superiority.

## Interpreting stops

A read watchpoint can stop in both the control and the lifetime test variant. The preceding checkpoint supplies the relevant lifetime context. The sentinel and pointer tests instead compare the observed changes in the relevant variants. The referenced GEF and Pwndbg revisions have different watchpoint implementations and coverage. The comparison does not identify a single cause for a missing signal or establish competing tool defects. GEF documents its helper as experimental.

The lab pinned GEF `809864d00442f9993298e33fd9cd282d687d2f45` and Pwndbg `9760ac8f1346d142857cffc933995cd6fca34dff`. The [GEF documentation](https://hugsy.github.io/gef/commands/heap-analysis-helper/) and [Pwndbg documentation](https://pwndbg.re/stable/commands/linux_libc_elf/track-heap/) were reviewed on November 13, 2026. Current documentation can differ from the pinned revisions.

## Runner compatibility and results

Pilot sessions identified a GDB script path quoting issue and a control-flow conflict in the tested Pwndbg revision. The main comparison used separate compatible runner configurations. The excluded pilots were retained and were not counted as tool detection results. Watchpoints ended at the fixture boundary so later stack reuse would not be counted as an in-lifetime observation.

See [R0 results](R0-RESULTS.md) for the actual comparison and its limits. The report verifier checks 30 selected sessions for checkpoints, samples, and triggers. It does not authenticate provenance or measure usability.
