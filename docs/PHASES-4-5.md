# R4 and R5 local report and validation scope

November 13, 2026. R4 delivered an installable local alpha. R5 added the agreed history extension, offline Ghidra integration, and local plugins. This report covers the tested platforms before publication. The user selected **GPL-3.0-or-later**. LICENSE contains the terms and NOTICE describes their scope and exclusions. The project has no mandatory dependency on Daybreak, GEF, Pwndbg, or AI.

## Observed evidence

| Area | Tests performed and evidence retained |
|---|---|
| Offline contracts | 93 Python and 14 JavaScript tests in `work/r4-r5-gates/python.txt` and `javascript.txt` |
| Pilot package 003 | 16 checks on Debian (`work/r4-package-debian-001`) and 16 on Kali (`work/kali-lab/package-pilot003`). Installation did not require a source checkout |
| Modules installed from the Kali pilot | 10 checks in `work/kali-lab/installed-pilot003` covering context, memory, plugins, dossiers, and static properties. Incompatible glibc profiles were rejected |
| R5 history | 14 live checks in `work/r5-history-003` and 14 independent repeats in `work/r5-history-independent-001`. Tests used a separate GDB oracle and detected an intentional mutation |
| Ghidra | 27 checks in `work/r5-ghidra-validation-002`, covering two PIE/non-PIE ELF fixtures and eight direct negative tests. Specific error messages were checked separately |
| Plugins | Nine contract tests and 17 checks across two GDB sessions in `work/kali-lab/plugins-validation/002`. The tests caught a mutation of the trusted hash |
| User trial | The user reported success in `work/r4-r5-gates/user-trial.json`. Entering one command per line resolved an initial paste issue |

The final package was tested separately from the pilots. Two builds produced identical bytes, with external hashes recorded in `work/r4-r5-final-build.json`. The Debian installation is recorded in `work/r4-package-debian-final`, the Kali installation in `work/kali-lab/package-final`, and the installed compatibility matrix in `work/kali-lab/installed-final`. The corresponding `validation.json` files record the final outcome. Pilot results cover their own package bytes. Final digests stay outside the ZIP so the archive does not contain a reference to its own hash. The package excludes dossiers, VMs, and keys.

## Compatibility and limits

Debian 12 x86-64 with GDB 13.1, Python 3.11, and glibc 2.36 covered the general modules, the heap view, and selected history. Kali 2026.3 x86-64 with GDB 17.2, Python 3.14.7, and glibc 2.43 covered the general modules. **The R2/R5 heap and allocator collectors explicitly reject glibc 2.43.** The tests ran real Linux kernels and processes in QEMU TCG on the ARM64 Mac. Performance on native hardware was unmeasured. Ghidra 12.1.4 with JDK 21 ran on the Mac using ELF files and references collected on Linux. Linux debugging on the Mac was outside that check.

R5 history is opt-in and covers one process, one thread, and up to four selected hardware regions. Calloc and realloc are allocator operations. A successful realloc creates a new identity even at the same address. Suspended or closed regions require a new selection. Missing returns and exhausted budgets produce explicit incomplete states. Reentrant or nested calls within a transaction are outside coverage. [History semantics](R5-HISTORY.md).

Plugins produce separate annotations. Trusted plugin code runs in a separate process with the user's permissions and without a sandbox. The Ghidra bridge checks identity and consistency. Authenticity and exploitability require separate evidence.

## Documentation comparison

The primary sources consulted on November 13 documented existing capabilities. [GEF context](https://hugsy.github.io/gef/commands/context/) presents registers, code, stack, and context. The [GEF heap helper](https://hugsy.github.io/gef/commands/heap-analysis-helper/) documents heap operation analysis. [Pwndbg features](https://pwndbg.re/dev/features/) and the [stable command index](https://pwndbg.re/stable/commands/) include context, heap inspection, and heap tracking. These capabilities predate the Ressembly modules described here. The [R0 report](R0-RESULTS.md) records the pinned versions and specific experimental findings. No benchmark was rerun on the versions described by the documentation.

Object identity, explicit selective coverage, and persistent dossiers may make some lab workflows easier. That remains a product hypothesis. The positive user trial covers the stated walkthrough.

## Retention and next milestone

The user authorized removal of both VMs, base images and downloads, the local QEMU runtime, and dedicated keys after final testing. Host logs, manifests, and evidence dossiers are retained. The coordinator records the actual removal and recovered space in `work/cleanup-report.json`. The old SSH and startup scripts require a rebuilt lab to run again. The original project directory was retained.

The proposed next milestone was dedicated glibc 2.43 allocator validation or testing on physical x86-64 hardware. Attach, fork, multithreading, other allocators, a GUI, and alternative backends were still open. This milestone did not create a remote repository, publication, push, release, or paid service.
