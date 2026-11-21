# Ressembly roadmap

Updated November 21, 2026. This roadmap covers the UNIT-47 project. The [Windows/Qt v0.1 roadmap](ROADMAP-WINDOWS-v0.1.md) is retained as a historical record.

## Diagnostics 0.9.0

| Status | Feature | Verified result |
|---|---|---|
| ✅ | Cooperative processes and threads | Timeline tested with spawn and fork on macOS ARM64 and Ubuntu x86-64. |
| ✅ | jemalloc statistics | Six aggregate counters verified against an actual 5.4.0 export. |
| ✅ | Static Ghidra selections | Export and reopening verified in headless mode. |
| ✅ | Local viewer | Report import and navigation verified in the browser. |
| 🟡 | Extended features | Concurrent heap history, tracing arbitrary processes, Ghidra desktop dialogs, continuous synchronization, live debugger controls, and Windows and Linux ARM64 debugger backends remain open. |
| ⬜ | Suite 1.0 | Final scope and validation remain open. |

[Download the ZIP](../diagnostics/downloads/ressembly-diagnostics-0.9.0-local.zip) · [Quick start](../diagnostics/README.md) · [Validation](../diagnostics/VALIDATION.md)

The sections below record the suite milestones and the scope of the public debugger alpha 0.6.0.

## Goals and constraints

Ressembly is a modular reverse engineering and security research suite for Linux x86-64. It uses GDB and Python with a terminal interface. Object history is one of its modules. The suite has no mandatory dependency on Daybreak, GEF, Pwndbg, a paid service, or AI. Other architectures, Windows, LLDB, and a debugger GUI are separate work. FaultCore handles crash reproduction and minimization. LOLDEX is outside UNIT-47.

## Milestone numbering and validation

The request to complete phase 3 included **all of R3a through R3e**. The earlier informal mapping of phases 1, 2, and 3 to R1, R0, and R2 was retired. **R0 through R3 were validated in the declared scope.** The [phase report](PHASES-1-3.md) records the results, independent repeats, fixes, and limits.

| Phase | Deliverable | Validation |
|---|---|---|
| R0 | GDB, GEF, and Pwndbg comparison | 30 sessions and 30 independent repeats. Results are limited to the tested workflows. |
| R1a/R1b | Marker-based collection and reliability | 16 original and 16 independent tests, plus 16 regression tests after R3. |
| R2a | Selected malloc/free operations, object identity, and address reuse | Validated with R2b. Failures, missing returns, and coverage limits are recorded. |
| R2b | One watchpoint region | 22 original and 22 independent tests, comparison against a separate reference, spot checks at different widths, and 22 regression tests after R3. |
| R3a | Assembly, breakpoints, registers, and stack | Validated with GDB on targets with and without symbols. Unavailable data is reported explicitly. |
| R3b | Memory maps, permissions, dumps, searches, and pointers | Tested limits, inaccessible memory, cycles, null pointers, and refreshed data. The tests were repeated independently. |
| R3c | Structural heap view | 13 original and 13 independent sessions on glibc 2.36 with debug types, one arena, and one thread, plus four additional cases. |
| R3d | ELF properties and pattern utilities | 44 original and 44 repeat checks, including comparison with readelf, plus 18 independent checks. |
| R3e | Persistent dossiers | 14 original and 14 independent checks covering build and run identity, reopening, export, and comparison. |
| Integration | R3 with the R2 collector active | Two workflows with 20 GDB checks each, followed by independent repeats. Object identities remain distinct. |
| **R4** | **Installable UNIT-47 alpha** | Implemented under GPL-3.0-or-later. Positive user trial and separate final dossiers. |
| R5 | Extended history, offline Ghidra bridge, and local plugins | Implemented and validated within the scope recorded in the R4/R5 report. |

R1 through R3 were validated on Debian 12 x86-64 emulated with QEMU TCG on an ARM64 Mac, using GDB 13.1, Python 3.11.2, and glibc 2.36. R0 used a separately documented, shared GDB runtime. R4 added the limited Kali tests described below. Native hardware performance remains unverified. The standalone HTML prototype uses synthetic data.

## R4 and R5

The [combined report and test dossiers](PHASES-4-5.md) cover repeatable local builds and clean installation. Debian was used for the glibc 2.36 profile. Kali was tested for the general modules and explicit rejection of unsupported allocator profiles. The user trial was reported as positive, and the project owner selected the license. R5 added calloc and realloc history, four selected regions, build identity and file-offset exchange with Ghidra, and explicitly trusted annotation plugins. The observed differences cover selected regions.

## R6: glibc 2.43

The [R6 report](R6.md) records the collector and heap view on Kali glibc 2.43-4, explicit layout profiles, tests checked against independent reference results, regression testing against a matching glibc 2.36 sysroot, and the 0.6.0 package. Installation and cleanup were recorded in the local acceptance report. The temporary lab peaked below 3 GB, and the large test files were removed. The debugger alpha 0.6.0 was subsequently published on GitHub.

## Remaining work

Run extended tests on physical Linux x86-64 hardware and measure stability and usability in regular sessions. The diagnostic package covers cooperative process and thread reporting, aggregate allocator statistics, and review of static evidence. Broader process tracing, concurrent heap history, desktop and live debugger integration, and additional runtime backends have their own validation work. Define the supported scope before preparing and publishing suite 1.0.

## Completion criteria

A milestone requires code, a repeatable workflow, retained results, review, and documented limits. Linux support requires actual Linux tests. An allocator event records an allocator operation. Differences between snapshots show sampled values and leave intervening accesses unknown. Each supported version requires its own validation.
