# R1 — acquisition lifecycle validation

Validated 13 November 2026 for the owned marker lab only: single inferior and thread, Linux x86-64 guest Debian 12, glibc 2.36, GDB 13.1, embedded Python 3.11.2, GCC 12.2. The guest runs under local QEMU TCG full-system emulation on macOS ARM64. This is actual guest GDB/kernel execution, not fake-GDB testing; it is not native hardware, Kali certification or a general target/allocator support claim.

Latest author validation: `work/validation/r1-validation-005/validation.json`, **16/16 checks PASS**, exit 0. The normal runner also passed at `work/validation/r1-default-001/`. Independent built-in GDB oracle logs and comparison are under `r1-validation-005/independent-oracle/`; all three sampled byte sequences matched, with register/thread/code context retained. Absolute ASLR addresses are deliberately not compared across runs. Independent reviewer execution is reported separately by the parent.

The first real attempt (`r1-validation-001`) exposed that GDB 13.1 treats internal quotes in `source "/path/script.py"` as filename characters. The loader was corrected to pass the raw source path, and the failed dossier is retained. Later validation review found that negative tests must also check GDB return codes; final sessions retain `process.json` and reject later command failures even when JSON had already been saved. `r1-validation-002` through `004` preserve those earlier checks; `005` is the final strict run.

## Commands

- `rs-start OUTPUT.json [EVENT_LIMIT]`: loaded target, before starting the inferior; default 10000 events, configurable 1–10000 for budget tests. Snapshot limit remains 64 bytes.
- `run`: first run only. PID, inferior number and target path are bound to the capture. A follow-up run is not appended: the collector prints REJECTED and stops at the marker, preserving the closed capture. This does not override GDB's built-in run command or prevent every possible target execution.
- `rs-show`, `rs-save`: show and persist current data.
- `rs-stop`: close collection explicitly with interrupted status. A new capture requires a fresh GDB session.

Loading the adapter twice is rejected before resetting acquisition state. Start refuses an already running/attached process, existing files and symlinks. Save uses a private temporary file in the destination directory and atomic replacement. Every marker is persisted; this favors small-lab evidence retention over throughput and has not been benchmarked as a general tracing backend. Disk errors remain errors; there is no guarantee after force-killing the debugger or host.

## States and scope

Normal exit records the available exit code and `partial_marker_coverage`; it never means complete allocator/write coverage. An exit notification without a code is `ended_without_exit_code` and interrupted: detach, kill and unavailable exit status cannot be called a successful target exit. A signal stop is persisted as interrupted and resumable until explicit close; resuming the same process returns collection to collecting. Explicit stop or debugger exit closes as interrupted. Unknown markers, read failures, scope changes or event limits stop collection and preserve the error/limit state.

The on-disk target digest is checked again at first continue; a replaced build is rejected. PID/inferior/target changes and multiple threads are rejected instead of joining observations. Future allocator tracking and watchpoint support have separate contracts and are not implemented by these changes. The marker schema and seven-event verifier remain unchanged.

## Real Linux procedure

From the project root on Linux x86-64 with glibc, GDB Python >=3.9, Python3 and a C compiler:

```sh
python3 scripts/validate-marker-linux.py work/r1-validation-001
```

Use a new directory. This runner invokes actual GDB subprocesses with `-nx`; it does not use the unit-test mock. It compiles our normal target and a generated negative target inside the dossier, retaining binaries, source, command files, logs, kernel/compiler/GDB/libc and SHA-256 identities. The intentionally invalid read-failure case declares address 1 via markers but does not dereference it in the C program; the collector's GDB read must fail. The SIGUSR1 case stops deliberately and is not a crash finding.

Cases: normal acquisition twice; independent GDB oracle; second run not merged; event budget; memory-read failure; signal interruption; explicit stop; kill without fabricated exit code; duplicate source rejected; pre-existing output preserved; already running target rejected; target/build changes rejected; missing marker rejected; validator rejects a command error occurring after valid capture JSON was saved. `validation.json` contains per-case result, GDB return codes and elapsed wall time. Managed sessions require code 0; command refusals require code 1. GDB 13.1 duplicate Python source reports its expected single GdbError traceback with code 0, measured and checked separately. A FAIL, timeout or command error is retained and must be investigated; a report's presence is not a PASS.

After the scripted checks, manually inspect marker arguments and `x/32bx` at checkpoint stops and compare with JSON, including thread/address/object generation. Preserve the manual log. Run under emulation must be labeled as such: actual guest GDB is useful correctness evidence, but elapsed time is not a native-machine performance claim. No Kali compatibility claim follows from a Debian/Ubuntu run.

## Offline tests

`tests/test_gdb_adapter.py` uses a deliberately fake GDB API for lifecycle/error paths. The fake forbids execution/frame mutations and validates output preservation. These tests cannot prove API/runtime behavior, watchpoints or a Linux kernel interaction. Baseline before changes: 18 Python tests passed. Added lifecycle tests: 11 passed on macOS; the final combined suite can also include independent R0 tests added by another agent.
