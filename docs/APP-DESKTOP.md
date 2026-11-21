> Historical v0.1 document. [SUITE-UNIT47.md](SUITE-UNIT47.md) records the direction approved on October 24, 2026. That decision superseded the Windows/C++/Qt plan below.

# Ressembly desktop application

The desktop proposal of October 24, 2026 described a Windows x64 application in C++ with Qt. The HTML preview illustrates the interface until the native application is ready.

## Components

- **Ressembly.exe:** Desktop window, experiment management, evidence viewer, notebook, and export.
- **C++ core:** Binary and module identity, observation validation, RVA normalization, comparison, and evidence references. Implementation remained open. It would have to reproduce the M0 corpus results.
- **x64dbg adapter:** Separate plugin for supported events and commands. Initial scope would cover selected observation points while x64dbg remained responsible for debugging.
- **Ghidra adapter:** Links static metadata to the exact build. Planned after the collector.

## First native workflow

The initial shell would open local observation files for offline analysis. An explicit connection to the Windows collector would follow once tests passed. The design requires no HTTP listener. Any IPC would be local to the session and check the process identity. The prototype has no IPC.

## Proposed screen

1. Experiments and inputs on the left.
2. Functions and assembly in the center, with clear provenance.
3. Registers, memory, and stack when captured by the debugger.
4. Evidence and annotations linked to the experiment.
5. Comparison of observations from the same binary using build and module identity. Absolute addresses and names alone are insufficient.

An empty panel displays “not captured.” Execution controls require a live, verified backend.

## Development and validation

Qt and C++ provide the desktop interface. Each operating system still needs a compatible debugging backend. The first operational version would require Windows x64. A future macOS application could read dossiers and exports. Native macOS debugging would require a separate adapter.

At the time of this proposal, the deliverables were the project design, initial contract, preview, and JavaScript comparison engine. The .exe build, x64dbg plugin, and verified live session were still open.
