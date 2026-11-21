# Ressembly Diagnostics 0.9.0

A GPL-3.0-or-later package for application diagnostics and local report review. It requires Python 3.9 or later. Ghidra is required only to exchange static function selections.

Download the [ZIP](downloads/ressembly-diagnostics-0.9.0-local.zip), check its [SHA-256](SHA256SUMS), and extract it. Open a terminal in the extracted directory. See the [validation report](VALIDATION.md) for the tested scope.

```sh
python3 -B scripts/ressembly-diagnostics.py demo processes.json
python3 -B scripts/ressembly-diagnostics.py viewer
```

Open the address printed by the second command and select `processes.json`. The viewer listens only on `127.0.0.1`. Imported files stay in the browser. Press Ctrl+C in the terminal to stop the viewer.

To record the fork example on a supported system, use the `demo fork.json --method fork` subcommand. To import jemalloc JSON statistics, use `jemalloc stats.json summary.json`. Both commands require a new output path.

The [diagnostics guide](docs/DIAGNOSTICS.md) covers cooperative events, aggregate statistics, and the Ghidra script. The commands were tested on macOS ARM64 and Linux x86-64 within the reported scope. Runtime validation on Windows and Linux ARM64 is still open.

This package contains the cooperative timeline, jemalloc summaries, manual Ghidra selection exchange, and the viewer. Debugger backends and concurrent heap history are separate work in the suite roadmap.
