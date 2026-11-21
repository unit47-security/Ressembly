> Historical v0.1 document. [SUITE-UNIT47.md](SUITE-UNIT47.md) records the direction approved on October 24, 2026. That decision superseded the Windows/C++/Qt plan below.

# Ressembly initial specification v0.1

October 24, 2026. This document records the proposed technical direction and the M0 prototype. Debugger integration was still planned.

## Product decision

A Windows desktop application in C++ with Qt for researchers who study software behavior in controlled experiments. The interface takes inspiration from OllyDbg's readability and organizes the work around questions, observations, and hypotheses.

Initial question: “Which code participates in decoding this format?”

Workflow: record experiment A → perform action B with one declared variation → collect comparable observations → find functions observed only in B → inspect the result in the debugger and Ghidra → run a third experiment to look for a counterexample → write a note linked to the events.

The comparison produces candidates for investigation. The analyst interprets the evidence. Additional events, frequency differences, and coincidences are insufficient to establish a function's meaning or role.

## Users and first lab

Researchers and developers work with native programs they own, open-source programs, or other authorized targets. The first planned operational lab is Windows x64 in user mode, with one process and the same binary across runs. The offline observation reader can also be used from a Mac.

Use small programs with normal behavior, such as reading a header, decoding an image, or selecting an algorithm. FaultCore remains responsible for crash handling and input reduction.

## Planned MVP features

1. Create an experiment with a question, input, action, environment, and observation window.
2. Collect observations through an x64dbg adapter, starting with breakpoint snapshots and selected entry points.
3. Keep the binary and build identity, module hashes, RVAs, thread, event, and provenance. Use stable identities to compare runs.
4. Compare observations with identical builds and capture scopes. Show coverage, losses, and unobserved portions.
5. Rename and annotate functions in the notebook while retaining the original evidence.
6. Link observations to static Ghidra locations after checking the hash and image base.
7. Export a readable dossier with verifiable references, hypotheses, counterexamples, and limits.

## What M0 implements

The prototype compares function-entry inventories. It leaves instruction sequences, call stacks, durations, and causal relationships unresolved. The `function_entry` type defines a proposed internal contract. Native format compatibility requires separate work.

A location is identified by the module SHA-256 and normalized RVA. The function name is descriptive. The reference binary hash must match both observations and the bundle header. A different module has a distinct identity. The comparison is limited to one build.

`complete` is a statement supplied by the producer. The interface displays it as declared completeness. The comparison does not establish exporter trustworthiness. A partial trace stays partial and leaves unobserved execution unknown.

Sequence numbers describe collection order within the applicable capture. They do not establish causality across threads. Counts refer to events. Normalization preserves the meaning of recorded data.

## Selected architecture

```text
x64dbg adapter (C++, planned)
   ↓ copied events, bounded queue, lightweight callbacks
Versioned observation format plus target identity
   ↓
Offline engine: validation → normalization → comparison → references
   ↓
C++/Qt desktop app: experiments | assembly | registers | memory | evidence | notebook
   ↔ Ghidra adapter (planned, exact matching)
```

M0 uses dependency-free JavaScript and local HTML for the preview. The proposed product was a Windows x64 C++/Qt executable without a web server. The C++ core would have to pass tests on the same corpus. A macOS offline reader could work independently of the Windows debugger.

The first live integration would use the existing debugger through a separate, optional plugin. REA and ReAgent remain complementary tools. M0 has no dependency on them or implemented REA integration.

## Performance and data

M0 allows up to 20 observations, 50,000 events per bundle, 256 modules per observation, and 5 MB for UI imports. These are prototype limits. Larger inputs would require streaming, pagination, and background workers to keep the UI responsive.

The future adapter must report dropped events, full buffers, cancellation, and disconnection. An interrupted capture remains partial. Callbacks must drop references to debugger pointers after their validity ends.

The viewer treats imported content as data and starts no processes during import. Exports contain declared inputs and analyst notes. Handle those research records according to the user's environment. The prototype requires no cloud service.

## Outside the MVP

Kernel and driver support, multiple processes, deterministic replay, universal backtracking, automatic type recovery, full taint tracking, semantic recovery across builds, automatic vulnerability detection, program patching, and autonomous AI agents.

A proposed feature belongs in the MVP only if it reduces real experiment work while preserving the evidence.

## Product validation

Compare the notebook with normal use of x64dbg and Ghidra on three small fixtures and with at least five users. Measure time to the first correct hypothesis, time to verification, interpretation errors, and the ability to resume after one day.

The proposed gate is a reduction of at least 25% in median time for two of three tasks without an increase in incorrect conclusions. This was a target for the trial. If the trial finds no benefit, narrow the product to a plugin or notebook, or abandon the standalone debugger proposal.
