# Ressembly reverse engineering suite by UNIT-47

The project adopted this direction on October 24, 2026. As of November 13, **R0, R1, R2, and R3a–R3e were implemented and validated in an emulated Debian x86-64 lab.** R4 and R5 were implemented within the scope of the [R4/R5 report](PHASES-4-5.md), which covers the local GPL-3.0-or-later package, extended history, Ghidra, and plugins. R6 added support for the Kali glibc 2.43-4 build, with [documented tests and limits](R6.md). The November 13 record predates publication. Native hardware tests were still open. See the [full phase report](PHASES-1-3.md).

## Identity and goal

Ressembly is a modular suite developed by UNIT-47 for reverse engineering and vulnerability research in authorized environments.

The goal is a coherent environment for research. GEF and Pwndbg provide references and comparison points. Claims of superiority require measurements. The first proposed differentiator was a readable lifetime of memory objects with references to recorded observations.

This decision superseded the earlier Windows-first C++/Qt plan and broadened the scope beyond comparing runs. The existing HTML prototype demonstrates the offline workflow. Operational GDB integration is provided separately.

## Proposed architecture

- Initial engine: GDB on Linux x86-64, with Kali evaluated as a deployment environment.
- Adapter: A Python extension that collects data through debugger APIs.
- Debugger-independent core: Object identity, validation, events, comparisons, and export, testable offline.
- Initial interface: Terminal commands, readable context, and navigation through evidence.
- Separate modules with explicit contracts so new analyses can be added without rewriting the core.
- GEF is optional. Running both tools together requires testing.

Windows, other debuggers, other architectures, and a graphical interface remained extensions to evaluate. The first version requires no web service or AI model.

## Suite components

| Component | Responsibility |
|---|---|
| Debugger context | Assembly, registers, stack, maps, and current locations |
| Memory exploration | Selected regions, search, pointers, and annotations |
| Object lifetime | Allocations, frees, address reuse, and observed accesses |
| Experiments | Inputs, environment, snapshots, comparisons, notes, and references |
| Extensions | Adapters and modules with declared versions and capabilities |

The initial modules through R3 are available within the limits of [R3.md](R3.md). Broader coverage remained separate work.

## First technical experiment

Use a project-owned C fixture on Linux x86-64 with one process, one thread, and a documented glibc build. The experiment checks whether a report can distinguish a new allocation from an earlier object at the same address. It records selected allocator operations and separate, bounded memory observations, then displays the resulting timeline with its coverage limits.

Allocator events and memory writes are distinct. Watchpoints have limits on count and size, and unrecorded writes remain unknown. Broader instrumentation requires a backend decision and overhead measurements.

Each event should preserve the target and build identity, run, collection order, thread, type, related object, raw address, code location if known, and provenance. Module and offset identities can help compare code locations. Heap and stack pointers are meaningful within their recorded runs.

An observation made after a free requires checking for intervening reallocations. A single observation is insufficient to establish exploitability, and missing events leave the corresponding accesses unknown.

## Milestones and acceptance criteria

[ROADMAP.md](ROADMAP.md) records the November 13, 2026 plan, expected results, dependencies, environment, and completion evidence. [BACKLOG.md](BACKLOG.md) breaks the phases into tasks. [VERIFICA.md](VERIFICA.md) records the checks actually performed.

- **R0:** Practical comparison of the tools. Completion requires hands-on testing beyond the documentation review.
- **R1:** Core and minimal collection. R1a and R1b were validated in the emulated lab, with evidence and independent repeats for reliability and negative cases.
- **R2:** Selected malloc and free tracking and one observed region, with separate records for allocator events and observed value changes.
- **R3:** Debugger context, memory exploration, a declared heap profile, ELF inspection and pattern utilities, and persistent experiments. These were validated in the initial scope, including integration and independent review.
- **R4:** Installable local UNIT-47 alpha with explicit license and compatibility. Publication required a separate request.
- **R5:** calloc and realloc history, four regions, an offline Ghidra bridge, and trusted local plugins, all with documented limits.
- **R6:** A glibc 2.43 profile with layout-specific handling, glibc 2.36 regression, and a temporary lab under 3 GB.

The roadmap requires checks for address reuse, missing reads, interruption, limited resources, compatibility, and review of results. Estimates are preliminary budgets.

## Relationship to other projects

FaultCore handles crash reproduction and minimization. Ressembly studies execution and memory during analysis. RoleDiff compares permissions. LOLDEX is outside UNIT-47. Any data exchange requires a documented contract.

## Verified status

The HTML prototype uses synthetic data and works offline. The GDB/Python backend includes R1, R2, and R3 and runs independently of GEF, Pwndbg, and Daybreak. [PHASES-1-3.md](PHASES-1-3.md) records the tests and limits. [R3.md](R3.md) describes the supported workflow. The R1 marker adapter remains a separate historical demonstration. R2 records selected malloc and free operations without allocator markers. The suite loader keeps allocator operations distinct from observed value changes.

Phase 3 includes R3a through R3e. The earlier informal label that equated it with R2 was incomplete. R4/R5 added limited Kali checks for general modules and has separate evidence and limits. The historical tests establish the declared scope. Broader product maturity, comparative advantages, and native hardware remain outside that evidence.

## Initial comparison sources

- Pwndbg: https://github.com/pwndbg/pwndbg and https://github.com/pwndbg/pwndbg/releases
- GEF: https://github.com/hugsy/gef
- Tenet: https://github.com/gaasedelen/tenet
- Ghidra Debugger: https://ghidra.re/ghidra_docs/GhidraClass/Debugger/A6-MemoryMap.html

These sources identify tools and capabilities for comparison. Market demand requires separate evidence.
