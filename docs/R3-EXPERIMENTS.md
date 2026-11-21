# R3e — Persistent experiments

Implemented and tested with real GDB snapshots. Results and independent repetitions are in the [final report](PHASES-1-3.md).

The `ressembly.experiment.v1` dossier is a self-contained JSON file with the binary identity and SHA-256, base64-encoded binary input, selected snapshots, notes associated with snapshots, and explicit limits. It can be reopened without GDB or the original process. Opening or importing a dossier does not restore a process, replay a session, or execute input or strings in the data.

## Local workflow

```sh
python3 scripts/ressembly-experiment.py create work/experiment.json work/owned-binary "Project experiment"
python3 scripts/ressembly-experiment.py input work/experiment.json work/input.bin "Expected input"
python3 scripts/ressembly-experiment.py show work/experiment.json
python3 scripts/ressembly-experiment.py note work/experiment.json "Observation" --snapshot ID
python3 scripts/ressembly-experiment.py compare work/experiment.json ID1 work/experiment.json ID2
python3 scripts/ressembly-experiment.py export work/experiment.json work/export.json
```

Acquire a debugger snapshot with `rs-experiment-snapshot FILE LABEL [ADDRESS LENGTH]` after loading `source /path/to/Ressembly/src/ressembly_experiment.py` in GDB. Offline acquisition uses `import-snapshot FILE SNAPSHOT_JSON BUILD_SHA256 RUN_ID LABEL` and records `supplied_json` provenance. For the known debug-context, R2 object-history, and R1 marker-history schemas, the build hash and run ID inside the snapshot must match its dossier record. The dossier rejects contradictions and leaves the file intact. The `gdb_context` label also declares provenance. Hashes catch inconsistencies and do not provide a cryptographic signature.

## Comparison and limits

Different builds are rejected, including during comparison. Different runs with the same identity scheme are allowed and flagged. Raw values and addresses do not establish object identity. Process IDs based on boot, PID, and start time and capture UUIDs use different identity schemes. A comparison across them reports `same_run: null`. Differences between snapshots leave intervening writes unknown. Partial sections remain partial, and recorded input does not establish which input the program consumed.

Limits are 256 MiB for the reference binary, 8 MiB for the dossier, 256 KiB per input, 1 MiB per snapshot, up to 128 records per collection, and 16,384 characters per note. Create and export reject an existing destination. Updates use a temporary file with fsync and atomic replacement. An exclusive lock prevents concurrent writers using this workflow. A forced stop may leave the lock in place. Check that no writer is active before removing it manually. Recovery from every disk failure is outside the guarantees.

The dossier is local and may contain sensitive input and memory. Export creates a full copy, with no transfer to external services.

GDB API sources: [Python commands](https://sourceware.org/gdb/current/onlinedocs/gdb.html/CLI-Commands-In-Python.html) and [inferiors and memory reads](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Inferiors-In-Python.html).
