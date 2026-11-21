# R3d — local lab utilities

This milestone covers cyclic-pattern and offset utilities and static inspection of little-endian x86-64 ELF64 files. The Python module uses the standard library. Linux validation used GCC and the GNU readelf and strip tools already available in the lab.

## Static ELF inspection

From the repository root, inspect a file without running it:

```sh
python3 scripts/ressembly-lab.py elf work/validation-example/binary
```

The parser accepts amd64 ET_EXEC and ET_DYN files up to 64 MiB, with at most 1,024 program headers, 8,192 sections, and 100,000 symbols. It rejects extended numbering, other architectures, ELF32, and big-endian inputs. Bounds and resource limits apply. The parser does not replace a full ELF validator or the system loader.

- **PIE:** ET_DYN with DF_1_PIE yields `yes`. ET_EXEC yields `no`. ET_DYN without that flag yields `undetermined`, including shared libraries without the flag.
- **Stack and NX:** The executable flag on PT_GNU_STACK is an on-disk property. A missing header yields `unknown`. `nx_stack=yes` records a request for a non-executable stack. Runtime permissions depend on the environment.
- **RELRO:** PT_GNU_RELRO with immediate binding yields `full_configuration`. The segment alone yields `partial_configuration`. Declared ELF settings do not establish the loader's applied permissions.
- **Canary:** The parser distinguishes defined and undefined stack protector symbols. Symbol presence does not establish that every function is instrumented. A missing symbol table yields `unknown_no_symbol_tables`.

The report records SHA-256 and byte size for the file it read. That information does not authenticate the file's origin. Runtime ASLR, CET, fortify, dependency behavior, and bypasses are outside the stated scope.

## Pattern utility scope

The utilities support a bounded prefix of a non-repeating de Bruijn sequence. Offsets are measured in bytes from zero. Integer queries use an explicit width and byte order. Hexadecimal byte sequences preserve their ordering. Search results distinguish unique, ambiguous, and missing matches, with an explicit flag when more than 100 matches exist. A result describes the searched prefix.

## Repeatable validation

The 11 offline tests check known vectors, uniqueness over small cycles, byte order, ambiguous matches, bounds, incomplete headers, and CLI behavior. On Linux, the lab compares file properties with GNU readelf using executable and library fixtures with different configurations, including stripped and missing-section-table cases. Missing and malformed inputs are rejected. The dossier records source hashes, tool versions, invocations, status codes, and raw comparison outputs.

The author run in `work/r3-labtools-001/validation.json` passed **44 checks**, including the 11 offline tests. The environment was Debian 12 x86-64 emulated with QEMU TCG, kernel 6.1.0-54-cloud-amd64, GCC 12.2.0, binutils 2.40, and Python 3.11.2. The binaries were inspected statically. A separate mutation that misclassified all ET_DYN files as PIE was detected by the shared-library test. An independent repeat passed the same 44 checks in `work/r3-labtools-independent-001`. Another 18 checks are recorded in `work/r3-labtools-review-probes-001`.

## Primary sources reviewed on November 13, 2026

- [GNU ld options](https://sourceware.org/binutils/docs/ld/Options.html)
- [GNU readelf](https://sourceware.org/binutils/docs/binutils/readelf.html)
- [GCC instrumentation options](https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html)
- [glibc 2.36 ELF structures and constants](https://raw.githubusercontent.com/bminor/glibc/release/2.36/master/elf/elf.h)
