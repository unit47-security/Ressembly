# R5 — Explicit local annotation plugins

The implementation is in `src/ressembly/plugins.py`, `plugin_worker.py`, and `plugin_gdb.py`. The CLI is `scripts/ressembly-plugins.py`, and the project-owned example is in `examples/plugins/summary/`. The initial API accepts JSON and returns **annotations**, which are kept separate from debugger observations. Plugins run on explicit request. Downloads, a marketplace, directory discovery, and execution when the suite loads are outside the scope.

## Terminal workflow

From the project root:

```sh
python3 scripts/ressembly-plugins.py inspect examples/plugins/summary
python3 scripts/ressembly-plugins.py run examples/plugins/summary snapshot.json --trust-sha256 HASH --output annotations.json
```

Review the local code and replace `HASH` with the SHA-256 displayed by the inspection command. The `snapshot.json` input is an already captured JSON object. The example counts available registers. It does not infer write coverage. The `--output` option creates a new file and rejects an existing destination. Without it, the result goes to the terminal. Installed packages expose the same workflow through `ressembly plugins`.

## Usage in GDB

Load the suite and stop your own program in GDB:

```text
rs-plugin list
rs-plugin inspect /path/to/plugin
rs-plugin load /path/to/plugin HASH
rs-plugin run summary
rs-plugin unload summary
```

The `inspect` command reads and validates the files without executing them. The `load` command registers the identity and explicitly supplied hash without running the code. Only `run` captures the current context and invokes the plugin. The included example has ID `summary`. Other plugins use their own IDs. Quote paths containing spaces.

Trust covers **code and metadata**. Changing `plugin.py`, the version, or the manifest after loading causes the next run to be rejected. Duplicate IDs are rejected until unloaded with `unload`. A new GDB session starts with an empty registry. Trust is not saved globally, and stops do not trigger automatic plugin callbacks.

## API 1 contract

The plugin directory contains two regular files. Symlinks are rejected. The `plugin.json` manifest contains exactly these fields:

```json
{"id":"summary","version":"1.0.0","api_version":1}
```

The `plugin.py` file defines:

```python
def analyze(snapshot):
    return {
        "api_version": 1,
        "annotations": [{"message": "Analyst note", "address": 4096}]
    }
```

The optional `address` must be an unsigned 64-bit integer. A nonempty message can have up to 2,048 characters. The limit is 128 annotations. Extra fields such as `observations` or `provenance` in plugin output are rejected. This format does not let plugins mark their results as captured events.

Successful responses follow schema `ressembly.plugin-annotations.v1`. They retain the plugin ID, version, API, and hash, the snapshot reference and hash, the provenance label `trusted_local_plugin_output`, and the status `annotations_not_debugger_observations`. These labels describe provenance. They do not verify the content of the note or authenticate later copies.

## Execution and limits

A separate Python process receives JSON input and runs in a temporary directory. The plugin receives a serialized copy of the snapshot. Changes to the copy do not affect the debugger's object. The API does not directly provide GDB commands or an inferior object.

**Plugins run as trusted local code with the user's permissions.** The separate process does not limit filesystem or network access and cannot make a hostile plugin safe. Inspection and hashing bind authorization to the selected bytes. Code review is still necessary. State preservation tests apply to the project-owned examples that were run.

The runner limits the manifest to 8 KiB, code to 128 KiB, and the serialized request to 1 MiB. The default timeout is five seconds and the API allows at most 10 seconds. Worker CPU time is limited to five seconds. Captured output and errors are limited to 1 MiB per file. The runner attempts to terminate the process group it started. Descendants that leave the group may remain. There is no memory limit or system isolation guarantee.

Plugin errors, invalid JSON, unsupported API versions, timeouts, and exceeded limits result in explicit failure. Annotations from a failed run are discarded. Invocations do not automatically run dossier inputs. Annotations do not establish exploitability.

## Validation performed

```sh
python3 -m unittest discover -s tests -p test_plugins.py -v
python3 scripts/validate-plugins-linux.py work/plugins-NEW
```

The validator requires Linux x86-64 and a new directory. It builds project-owned C code, runs two separate GDB processes, and retains commands, output, exit codes, references, and hashes. Direct GDB commands compare registers and 64 stack bytes before and after the plugin. The checks also verify that the target does not advance, inspect and load do not execute the plugin, changed digests are rejected, and a new session starts with an empty registry.

Independent Kali validation at `work/kali-lab/plugins-validation/002/validation.json` recorded **17 passing checks across two GDB sessions**. **Nine contract tests** passed on both the Mac and Kali. The environment was Kali 2026.3 x86-64 with kernel 7.1.5, GDB 17.2, and Python 3.14.7 under QEMU TCG on an ARM64 Mac. It provides no native performance measurements.

Attempt `001` was retained. Its embedded Python had a quoting issue in the test harness. A raw string and a pre-execution syntax check fixed the harness without changes to the product. Testing caught a mutation in a separate copy that skipped the trusted hash comparison (`work/kali-lab/plugins-mutation/`).

The installed Kali pilot was tested separately with the `summary` example, real GDB observations, and a final integrity check (`work/kali-lab/installed-pilot003`). Validation of the final package and repetitions on Debian require separate evidence in the integrated report.
