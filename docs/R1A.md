# R1a: markers and samples from a project-owned fixture

Updated November 13, 2026. The R1a marker workflow and R1b reliability checks passed on Debian 12 x86-64 under QEMU TCG emulation. A separate agent repeated all 16 live tests. See [R1 validation](R1-VALIDATION.md). Native hardware, Kali, and a general suite tracker remain outside this validation.

## Scope

`examples/marker_lab.c` uses actual malloc and free calls. It reports selected operations through `rs_event(kind, ptr, size)`. Kind 1 records an allocation return, kind 2 declares a completed free, and kind 3 requests a sample. The fixture does not read freed memory. Reuse of the second allocation depends on the allocator. The offline test forces reuse to verify separate identities.

`src/ressembly/history.py` assigns a generation per address. An unmarked free remains unknown. `src/ressembly_gdb.py` collects markers with Python breakpoints, reads at most 64 bytes per sample, and has a budget of 10,000 events. Differences record changed offsets in comparable bytes. `None` indicates that no earlier sample is available. Coverage remains partial after a normal exit.

Arbitrary targets, attach, multiple processes or threads, realloc, calloc, alternative allocators, heap parsing, and individual write tracking are outside this workflow. The runner requires Linux x86-64 with glibc and GDB Python 3.9 or later. The operational check covered GDB 13.1, Python 3.11.2, and glibc 2.36 in the Debian lab. The workflow has no GEF, Pwndbg, AI, or service dependency. Coexistence with other extensions was not tested. Use GDB `-nx`.

## Linux workflow

From the project directory in an authorized Linux x86-64 environment with a C compiler, glibc, Python-enabled GDB, and Python 3:

```sh
sh scripts/run-marker-lab.sh work/linux-r1a-001
python3 scripts/show-marker-history.py work/linux-r1a-001/history.json
```

Use a new output directory. The workflow compiles the fixture with debug symbols and optimization disabled, starts GDB without personal configuration, saves JSON and logs, and checks the expected events. Expected results: seven markers, a difference only at offset 4 in the second sample, two distinct object identities that are both freed, and exit code 0. This checks the fixture within the declared scope.

For a manual run after compilation, start from the project root:

```text
gdb -nx -q work/linux-r1a-001/marker_lab
source src/ressembly_gdb.py
rs-start work/manual-history.json
run
rs-show
rs-save
```

Use one capture per GDB session. `rs-save` persists the current state. Process exit, a signal stop, and a normal GDB exit have dedicated save paths. Forced debugger shutdown or a crash can lose data after the last save. An interruption before exit is an incomplete session. Use a fresh capture for a second run.

## Contract and provenance

The `ressembly.marker-history.v1` schema is separate from the historical HTML schema. Metadata records the run UUID, binary SHA-256 and path, host, GDB version, architecture, host libc, and process and capture states. Host libc alone does not establish the libc loaded by the inferior. Retain fixture output reporting the actual glibc version and the runner's environment files. Each normal marker includes sequence, thread, PC, kind, address, size, and object identity when available. Collector errors may have incomplete context and remain explicitly classified as errors.

`explicit_target_marker` records a declaration by the target. `bytes_hex` comes from a GDB read at the marker. The marker PC cannot identify the instruction that changed the bytes. Module and offset normalization and pointer equivalence across runs are outside this schema. Exports contain addresses and lab samples with their declared provenance.

## Offline tests and original next validation step

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/core.test.cjs
```

Python tests use constructed offline data. The next step at the time was to run and manually check the Linux fixture, comparing markers, bytes at checkpoints, thread, addresses, generations, logs, and hashes. The plan then covered interruption and failure cases and overhead measurements before selecting allocator hooks and a watchpoint region with explicit limits and GEF/Pwndbg comparison. The November 13 update above records the validation that was subsequently performed.

## Lab verifier update

The verifier checks the seven markers emitted by `marker_lab.c`. Its checks stay active under `python3 -O` and do not rely on `assert`. The input budget is 2 MiB. Malformed JSON, duplicate keys, and nonfinite numbers are rejected. Incorrect invocation exits 2. Invalid or unreadable input exits 1. Checks cover consistent sequence, address, generation identity, samples, final objects, and declared coverage. A pass establishes consistency with the fixture expectations only.

Test data are synthetic fixtures in memory or temporary directories, including when their fields resemble collector output. The viewer is a preliminary reader for trusted local files. Authenticity is outside its scope.

The working copy is `/Users/user/Documents/ChatGPT/Ressembly`. The original from October 24 remains in its previous directory. The November 13 work ran the Linux x86-64 validation and manual GDB comparison in the emulated lab. See [R1 validation](R1-VALIDATION.md). This work introduced no Daybreak dependency.
