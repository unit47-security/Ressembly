# Validation

Ressembly Diagnostics 0.9.0 was verified in its declared diagnostic scope.

- Reproducible ZIP from two builds. Manifest hashes and archive SHA-256 verified.
- macOS ARM64 and Ubuntu x86-64 on AWS: cooperative spawn/fork and the loopback viewer.
- macOS ARM64: six aggregate metrics matched a real jemalloc 5.4.0 JSON export.
- Ghidra 12.1.4 headless: static selection export and reopening on an owned ELF, rejection of invalid inputs and static export on ELF ARM64 and Windows COFF objects.
- Browser: imported diagnostics, selected a worker and inspected its thread events.
- Source validation gate: 189 Python tests and 27 JavaScript tests.

Windows and Linux ARM64 debugger runtimes, the Ghidra desktop dialog, continuous synchronization and live debugger controls remain open.

The English documentation update changed the guides and their manifest hashes. Code and viewer assets in the ZIP are byte-for-byte identical to the tested package. The rebuilt ZIP passed manifest and link checks, and its extracted demo passed both spawn and fork on macOS ARM64.
