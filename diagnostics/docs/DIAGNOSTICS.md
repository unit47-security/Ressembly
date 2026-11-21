# Process diagnostics, allocator statistics, and Ghidra selections

These features are available in Diagnostics 0.9.0.

## Processes and threads

```sh
python3 -B scripts/ressembly-diagnostics.py demo processes.json
python3 -B scripts/ressembly-diagnostics.py demo fork-processes.json --method fork
```

The demo supervisor starts two child processes. Each child records two threads, and a barrier ensures that their recorded sections overlap. The supervisor verifies the children's exit status and saves the report. The default start method is `spawn`. Use `fork` on systems where Python supports it. In a full Ressembly installation, the equivalent command starts with `ressembly diagnostics`.

For cooperating applications, create a `ressembly.diagnostics.ProcessLog` in the process that emits the log. Use `with log.thread("label")` around the section to record. Call `log.close()` to obtain the process record after all sections have closed. Declare the parent relationship with `ProcessLog("child", parent_id=parent_id)`. After a fork, create a new log in the child. Use `report` to assemble the records and `write_new` to save to a new path on a filesystem that supports hard links.

Report identifiers distinguish process and thread instances when the operating system reuses PIDs or TIDs. Sequence numbers and elapsed times apply within each process. Events describe sections declared by the application, with a limit of 128 events per process. Exit codes are observed by the demo supervisor. Attaching to arbitrary processes and following heap object histories across threads, arenas, and processes remain open roadmap items.

## jemalloc statistics

A program using jemalloc can export aggregate statistics as JSON with `malloc_stats_print`. The [jemalloc manual](https://jemalloc.net/jemalloc.3.html) describes the format, the `J` option, and the delay that thread caches can introduce into the counts.

```sh
python3 -B scripts/ressembly-diagnostics.py jemalloc stats.json summary.json
```

The importer reads up to 1 MiB. It records valid byte counts, missing metrics, and the SHA-256 of the source file. `examples/jemalloc_stats_lab.c` produces a sample by allocating and freeing a block. This importer reports process-wide aggregates. The debugger's heap views and collectors use the declared glibc profiles.

## Review a function in Ghidra

1. Add `integrations/ghidra` to Ghidra's Script Manager directories and open your program.
2. Place the cursor inside a function and run `RessemblyReview.java`. Choose **export** and select a new JSON file.
3. Open the JSON in the viewer to see the program name, language, qualified function name, and hash.
4. To resume review, run the script in Ghidra, choose **open**, and select the JSON. The script checks the hash and language and resolves a unique function name before moving the cursor.

The exchange is manual and limited to a static selection. The export has five text fields. The script rejects mismatched hashes, absent or ambiguous function names, duplicate fields, and existing export destinations. It leaves the program contents unchanged. The [GhidraScript documentation](https://ghidra.re/ghidra_docs/api/ghidra/app/script/GhidraScript.html) covers the dialog and navigation APIs.

## Validation on November 21, 2026

| Feature | Test performed |
|---|---|
| Processes and threads | `spawn` and `fork` on macOS ARM64 and Ubuntu x86-64 on AWS. Verified three distinct PIDs per session, parent-child links, two distinct threads per child, per-process event order, and clean exits. |
| jemalloc | Built 5.4.0 in a temporary directory on macOS ARM64. Compared all six imported counters and the source SHA-256 with the C program's actual JSON export. |
| Ghidra | Ghidra 12.1.4 with JDK 21 in headless mode. Exported and reopened a selection on an owned x86-64 ELF fixture. Verified rejection of a mismatched hash, duplicate field, and existing output file. |
| Windows and Linux ARM64 artifact formats | Exported a static selection from an x86-64 COFF object and an ARM64 ELF object compiled on the Mac. Debugger backends still need runtime tests on the corresponding systems. |
| Viewer | Imported an actual fork timeline, jemalloc statistics, and a selection exported from Ghidra. Verified per-process views, paired events, displayed values, and clearing the view. |

The Ghidra desktop dialogs, continuous synchronization, and live debugger controls remain open. The viewer command prints its loopback address and serves the viewer assets. The [package guide](DIAGNOSTICS-PACKAGE.md) covers extraction and your first report.
