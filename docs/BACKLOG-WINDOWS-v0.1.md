> For current implementation status, see [R1a and the Linux gate](R1A.md) and the [audit](AUDIT-2026-10-24.md). This document retains the historical plan.

> Historical v0.1 document. [SUITE-UNIT47.md](SUITE-UNIT47.md) records the direction approved on October 24, 2026. That decision superseded the Windows/C++/Qt plan below.

# Ressembly historical Windows backlog

October 24, 2026. The tasks below were proposed. The README describes the M0 foundation that already existed.

## RS-000 — Windows x64 desktop shell

Build a C++/Qt application with observation import, a function list, evidence detail, and a notebook. Use a native GUI without an embedded browser or HTTP service. Run long operations outside the UI thread. Reuse the M0 corpus as the behavior contract. Conversion of the JavaScript engine would be separate work.

Acceptance: a reproducible Windows build, successful import of the demo bundle, visible indicators for partial data, a responsive window, and documented memory limits. Development can start on a Mac. The Windows gate requires a real build and test on Windows.

## RS-001 — Capture contract v1

Add a versioned JSON Schema and validator for the complete contract: input hash, capture identity, configuration, scope, producer, architecture, and quality. Separate declared metadata from independent checks. Include valid and invalid examples, explicitly reject unknown schemas, and keep validation independent of target execution.

Acceptance: malformed inputs, size limits applied before allocation, different builds and capture scopes, frames or threads that cannot be identified, and dropped data. Diagnostics must be readable and numeric values must retain their meaning.

## RS-002 — Portable real corpus

Create three small C/C++ programs with documented inputs and results. Build reproducibly on Windows x64 with and without symbols. Record hashes and compiler details in a manifest. Use fixtures designed to run normally. The analyst can check the source after completing the task.

Acceptance: controlled inputs produce at least two distinguishable behaviors and one counterexample. Source instrumentation, breakpoint sampling, and instruction tracing retain their distinct provenance.

## RS-003 — x64dbg collector prototype

Build a minimal plugin with a selected entry point and explicit start and stop. Copy valid data in the callback and process it outside the debugger thread. Keep callback work light, retain no expired pointers, and bound the buffer. Report dropped events and partial quality when the buffer fills.

Acceptance: manually compare module identity, RVA, and thread with x64dbg. Stopping, detaching, and target exits must leave the debugger responsive. Observations of selected functions describe only those functions. Requires a Windows x64 test environment.

## RS-004 — End-to-end workflow with real observations

Import a collector bundle into the viewer. Show the source identifier on each row. Export notes and references while preserving the source bundle. A note keeps its original experiment when the selection changes.

Acceptance: a second user can repeat the workflow from capture to dossier. Each row points to an existing source. Partial traces remain partial after export and reimport.

## RS-005 — Ghidra export integration

Import offline metadata for one build. Require a hash and architecture, normalize RVAs, and report collisions explicitly. Match using build and location identity. The viewer uses exported metadata and leaves decompilation to Ghidra.

Acceptance: modules at different load bases still match correctly, a name shared by multiple DLLs stays distinct, and a replacement build is rejected.

## RS-006 — Utility trial

Prepare tasks, a balanced order, and a measurement form. Obtain consent and authorization before contacting users. Compare work with and without the notebook, separating familiarity with the task from the effect of the tool. Record the result, including the possibility that the notebook offers no benefit.

## Sequence

RS-000, RS-001, and RS-002 design → RS-003 on Windows → RS-004 → RS-005 → RS-006. This historical plan was prepared without publication or autonomous overnight work.
