# Ressembly backlog

November 13, 2026. The [roadmap](ROADMAP.md) uses the R0–R5 phase labels. The [evidence report](PHASES-1-3.md) records completion through R3. The [Windows v0.1 backlog](BACKLOG-WINDOWS-v0.1.md) is historical.

| ID | Phase | Task | Status |
|---|---|---|---|
| LIN-001 | R1a | Linux x86-64 lab and tool versions | Validated on emulated Debian x86-64 |
| LIN-002 | R1a | C capture with verified markers and bytes | Validated against an independent reference and repeat |
| LIN-003 | R0 | Three lab programs with controls | Validated |
| LIN-004 | R0 | GDB, GEF, and Pwndbg comparison | 30 original and 30 independent sessions validated |
| LIN-005 | R1b | Interruptions, errors, budgets, exit, and new runs | Validated, including regression after R3 |
| LIN-006 | R1b | Metadata, hashes, and incomplete files | Validated for consistency. Authenticity requires separate evidence. |
| LIN-007 | R2a | Selected malloc and free operations and object generations | Validated within the selected scope |
| LIN-008 | R2b | Hardware watch region, resource limits, and cost | Validated, including regression after R3 |
| LIN-009 | R3a | Debugger context | Validated with and without symbols, including an independent repeat |
| LIN-010 | R3b | Memory maps, bounded searches, and pointers | Validated, with explicit limits and missing data |
| LIN-011 | R3c | glibc 2.36 heap view | 13 original and 13 independent sessions, plus four additional cases |
| LIN-012 | R3d | ELF properties and pattern utilities | 44 original and 44 repeat checks, plus 18 independent checks |
| LIN-013 | R3e | Persistent experiments | 14 original and 14 independent checks, including reopening by a separate reviewer |
| LIN-013I | R3 | Integration and regressions | Unified loader, two workflows with independent repeats, and successful R1/R2 regressions |
| **LIN-014** | **R4** | **Alpha package, license, compatibility matrix, and clean installation** | **Implemented and tested on Debian and Kali by module. Native hardware remains unverified.** |
| LIN-015 | R5 | calloc and realloc history, four regions, and code references | Validated on glibc 2.36, including independent repeats |
| LIN-016 | R5 | Offline Ghidra bridge with hashes, offsets, and byte samples | 27 live checks covering PIE, non-PIE, and negative cases |
| LIN-017 | R5 | Trusted local annotation plugins | Contract and live GDB sessions validated. Plugins run with the user's permissions. |
| LIN-018 | R6 | Kali glibc 2.43 profile | Implemented with layout-specific handling, corpus tests, and a 2.36 regression. See [R6.md](R6.md). |

R3 is complete within its declared scope. The [R4/R5 report](PHASES-4-5.md) records the separate evidence and limits for those phases. The November 13 record predates publication. The lab VMs can be removed after preserving the evidence. Daybreak and mandatory AI remain outside the plan.
