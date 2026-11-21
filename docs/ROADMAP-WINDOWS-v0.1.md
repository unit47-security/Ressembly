> For current implementation status, see [R1a and the Linux gate](R1A.md) and the [audit](AUDIT-2026-10-24.md). This document retains the historical plan.

> Historical v0.1 document. [SUITE-UNIT47.md](SUITE-UNIT47.md) records the direction approved on October 24, 2026. That decision superseded the Windows/C++/Qt plan below.

# Ressembly roadmap v0.1

October 24, 2026. These milestones and estimates assumed one experienced developer working regularly, access to Windows x64 for native tests, and time for review. Learning reverse engineering and working on other projects would lengthen the schedule.

## M0 — Direction and offline prototype

Delivered: the specification, tool comparison, visual notebook, function-entry comparison, filters, JSON import, and annotated export. The prototype labels its data as synthetic. The engine has 14 tests. Visual checks are recorded in VERIFICA.md.

The milestone covered a preview. Windows debugging, live collection, replay, and Ghidra integration were still open.

## M1 — Desktop shell, stable contract, and real corpus (estimated 1–2 weeks)

- Build a native C++/Qt shell on Windows x64 to import offline observations. The shell requires no embedded browser.
- Version the observation format with required fields, limits, and rules for unknown data.
- Record input hashes, capture configuration, tool and build identities, and the actual test environment.
- Create three small, benign C/C++ programs for header parsing, format selection, and simple decoding.
- Compile with and without symbols and use explicit collection to gather repeat observations.
- Test ASLR, different modules, identical inputs, partial recordings, ambiguous names, and configuration changes.

Gate: use an actual capture bundle through import, comparison, annotation, and export. Preserve unknown binary identity and coverage. Reject incompatible imports with a readable reason.

## M2 — Windows x64 collector for x64dbg (estimated 2–4 weeks)

- Build a C++ plugin for one user-space process, explicitly activated by the analyst.
- Start with a declared set of breakpoints at selected function entries.
- Copy valid data in the callback and pass it to a bounded worker queue.
- Record module loads and unloads, image base, RVA, thread, and event references.
- Display collection status and resource limits. Record dropped data, cancellation, and disconnection.
- Report coverage limited to the selected functions.

Gate: at least 20 captures on small Windows x64 fixtures. Check identities and addresses against the debugger, maintain UI responsiveness, and preserve partial quality on interrupted runs. Measure overhead and data volume in a documented environment. This phase requires a native or compatible Windows environment.

## M3 — Persistent notebook and experiment search (estimated 2–3 weeks)

- Record the question, action, input, controls, and environment for each experiment.
- Link hypotheses to locations and events and keep them separate from captured facts.
- Use these hypothesis states: proposed, supported in the sample, counterexample found, and inconclusive. A diff alone cannot decide the outcome.
- Record repeats, counterexamples, and conflicting observations.
- Search functions, inputs, and notes and navigate to the original reference.
- Restore sessions while preserving the collected data.

Gate: a colleague can resume an experiment from its dossier and find every reference. Notes retain their references after an update or import.

## M4 — Static Ghidra bridge (estimated 2–3 weeks)

- Import function names, signatures, and addresses from a declared export.
- Validate the hash, architecture, module, and image base before linking an event.
- Match the exact build and leave ambiguous offsets unresolved.
- Keep inferred pseudocode, analyst annotations, and runtime data separate.
- Open the corresponding location in a compatible environment with documented versions and limits.

Gate: match the corpus correctly with and without symbols and reject a replaced binary. A missing function in Ghidra results leaves its execution status unknown.

## M5 — Comparison with real work (estimated 2–3 weeks)

Five users complete three tasks: locate a parser, distinguish two modes, and test a hypothesis with a counterexample. Compare with x64dbg plus Ghidra and with the analyst's usual tools.

Measure time, errors, manual steps, and dossier quality. Use task performance and dossier quality to assess utility.

Proposed gate: reduce median time by at least 25% on two tasks without increasing incorrect conclusions. If the trial finds no benefit, improve the notebook or keep it as a plugin. Building a complete debugger would require a separate decision.

## M6 — Alpha distribution (estimated 2–4 weeks after the preceding gates)

Prepare reproducible packaging, installation instructions, collector limits, large-trace handling, accessibility, portable exports, examples, and a tested compatibility matrix. Release the capabilities that pass their checks.

Gate: a new Windows machine completes the documented workflow, a user recognizes partial capture, and the application remains responsive with the reference corpus.

## After the alpha: select one extension

- Improve the association between behaviors and functions through repeated experiments.
- Add trace formats using independent adapters.
- Add Linux or ARM64 support after measurements and demonstrated demand.
- Refine the C++/Qt shell using results from the usability trial.

AI support remains optional and comes later. Any explanation must cite observations, distinguish hypotheses, and leave process control with the user. FaultCore remains responsible for the crash reproduction and minimization pipeline.

## Overall effort

The original estimate was 11–19 weeks after M0 for a narrow first alpha, assuming the necessary skills and environment were available. A developer still learning or working on other projects should allow more time and revisit each estimate after its milestone.
