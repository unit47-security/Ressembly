# Ressembly

**Understand behavior. Keep the evidence.**

Experimental reverse-engineering and memory-research suite by **UNIT-47**, using GDB/Python on Linux x86-64. **Alpha 0.6.0** — GPL-3.0-or-later.

## Diagnostics 0.9.0

This standalone package records process and thread activity from cooperating applications, imports aggregate jemalloc statistics and exchanges static function selections with Ghidra. Its local viewer reads the resulting reports.

[Download the ZIP](diagnostics/downloads/ressembly-diagnostics-0.9.0-local.zip) · [Quick start](diagnostics/README.md) · [Validation](diagnostics/VALIDATION.md) · [SHA-256](diagnostics/SHA256SUMS)

The sections below describe the public debugger alpha 0.6.0.

## Implemented

- Debug context: disassembly, registers, stack and breakpoints.
- Memory maps, bounded reads/search and pointer navigation.
- Selective malloc/free/calloc/realloc histories with generation-aware identities and up to four hardware watch regions.
- Structural heap profiles for exact glibc 2.36 and 2.43 layouts.
- Cyclic patterns, offsets and static ELF properties.
- Persistent experiment dossiers, snapshots, notes and comparisons.
- Offline Ghidra identity/offset bridge and explicitly trusted annotation plugins.

## Scope and limitations

The new allocator profile was tested on Kali 2026.3, glibc 2.43-4, GDB 17.2 and Python 3.14.7. The 2.36 regression uses matching isolated userland in the same Kali guest. Linux tests ran in QEMU TCG on an ARM64 Mac; native hardware performance is not established. Only launched local, single-thread/single-arena targets are supported. Attach, fork, multithread, other allocators and neighboring glibc versions such as 2.43.1 are not covered.

Allocator operations are distinct from observed writes. Selective watches do not record every access; missing events remain unknown. No single signal establishes exploitability. Plugins execute trusted code with user permissions, not inside a security sandbox. The Ghidra bridge is offline, not live GUI synchronization.

## Build and install locally

Python 3.9+, Linux x86-64, GDB with Python, a C compiler and matching libc debug symbols are required for the relevant modules. No GEF, Pwndbg, Daybreak, paid service or mandatory AI dependency. Run as an ordinary user.

```sh
mkdir -p build "$HOME/.local"
python3 scripts/build-local-package.py build/ressembly-0.6.0-local.zip
python3 scripts/install-local.py install build/ressembly-0.6.0-local.zip "$HOME/.local/ressembly-alpha"
"$HOME/.local/ressembly-alpha/bin/ressembly" doctor
"$HOME/.local/ressembly-alpha/bin/ressembly" --help
```

Use a new installation prefix. Keep binaries and experiment outputs outside that prefix. `doctor` discovers prerequisites; it does not certify a target. See [installation and removal](docs/R4-INSTALL.md), [commands](docs/R3.md), [R6 profile and evidence summary](docs/R6.md), [Ghidra](docs/R5-GHIDRA.md) and [plugins](docs/R5-PLUGINS.md).

## Developer validation

```sh
python3 -m unittest discover -s tests
node --test tests/core.test.cjs
# On a compatible Linux x86-64 laboratory:
python3 scripts/validate-r6-linux.py work/r6-NEW
```

The final local validation passed 97 Python tests, 14 JavaScript tests, 24 Kali 2.43 groups with an independent replay, and 16 mixed-userland 2.36 groups. Aggregated groups include the nested 22-case R2 and 14-case R5 corpora; do not count them as additional independent sessions. Packaging passed 16 checks plus five installed-use checks. Raw local dossiers and temporary lab images are intentionally excluded from this repository; developer validators reproduce the checks in an appropriate laboratory. See the [roadmap](docs/ROADMAP.md). Historical reports retain their original local paths and phase-specific scope.

## Historical prototype

`prototype/index.html` is an offline demonstration with synthetic data. It is not the operational debugger or a GUI for the backend. The superseded Windows/Qt plans remain historical documents.

## License

Original project code, owned examples and documentation: **GPL-3.0-or-later**, without warranty. See [LICENSE](LICENSE) and [NOTICE](NOTICE). External tools retain their licenses and are not bundled.
