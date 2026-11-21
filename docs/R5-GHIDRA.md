# R5 — Offline Ghidra bridge

The bridge matches a GDB reference to **the same ELF** using SHA-256, file offset, original bytes, and ELF virtual address. It works offline without controlling an open Ghidra session. Ghidra and the JDK are separate tools selected by the user.

Load the suite and stop your own program in GDB before exporting a reference:

```gdb
rs-code-reference reference.json
```

In the terminal, replace these paths with the paths for your local installation:

```sh
PREFIX/bin/ressembly ghidra validate reference.json /path/to/program
PREFIX/bin/ressembly ghidra analyze reference.json /path/to/program --ghidra-home /path/to/ghidra_12.1.4_PUBLIC --java-home /path/to/jdk-21 --workdir /path/to/new-analysis
```

From the checkout, use `python3 scripts/ressembly-ghidra.py` in place of `PREFIX/bin/ressembly ghidra`. Quote paths containing spaces. The `validate` command checks the reference against the file without Ghidra. The `analyze` command requires a new directory. It imports a copy into the local project and retains the command, logs, and `ghidra-link.json`. JVM arguments confine caches, settings, and temporary files to the analysis directory. The bridge does not save global launcher settings.

The output identifies the resolved function and address. A file offset is distinct from an RVA relative to the load base. For PIE, the mapping uses the ELF segment and the Ghidra mapping, so runtime and Ghidra addresses may differ. A watchpoint PC represents the point where execution stopped after an instruction. It does not identify the writing instruction on its own. Anonymous and unresolved references remain unresolved.

The bridge rejects mismatched hashes, fractional offsets or offsets outside uint64, contradictory runtime mappings, inconsistent ELF addresses, duplicate JSON keys in the script, and changed bytes in the imported program. It rejects an existing destination. Ghidra can return exit status zero even when a script fails. Confirm the expected result file exists and retains the expected identity. A consistent JSON document does not establish authenticity.

`work/r5-ghidra-validation-002/validation.json` records **27 passed checks**, with two complete imports covering PIE and non-PIE and eight direct negative imports. The ELF files and references came from Linux. An independent comparison used GNU nm, readelf, and the bytes themselves. Ghidra 12.1.4 and JDK 21 ran on the ARM64 Mac, including paths with spaces. Negative diagnostics were checked separately in `negative-diagnostics-review.json`. Attempt 001 was excluded after the final hash check showed that the Java script had changed during testing.

For developer reproduction, `scripts/validate-ghidra-local.py` requires the Linux corpus with references and nm and readelf reference results, explicit Ghidra and JDK paths, and a new directory. It is excluded from the user package. Other binary formats, architectures, and Ghidra versions were outside this validation. The bridge makes no vulnerability or exploitability determinations.
