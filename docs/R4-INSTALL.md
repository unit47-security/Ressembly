# R4 — Local alpha package

The package contains Ressembly code, project-owned examples, guides, the license, and notices. It excludes `work/`, VM images, keys, captures, caches, external GEF and Pwndbg comparison tools, and the HTML prototype. R4 distribution was local. See `LICENSE` and `NOTICE` for licensing. External programs remain separate.

## Build and verify

From the source checkout, with Python 3.9 or later:

```sh
python3 scripts/build-local-package.py work/ressembly-0.5.0-local.zip
```

Choose a new output path. The builder includes only allowed directories, suffixes, and CLI files. The manifest records the path, size, mode, and SHA-256 of every file. Two builds with identical allowed files produce identical bytes. Checksums detect inconsistencies and do not authenticate the publisher. Historical files retained in source are records of past work.

The archive limit is 32 MiB. It permits up to 512 files, with at most 2 MiB per file and 24 MiB of total content. The local format accepts only regular, uncompressed ZIP entries at relative paths in the expected layout. Links and duplicate entries are rejected.

## User-space installation

Run from the source checkout as an ordinary user on Linux x86-64:

```sh
mkdir -p "$HOME/.local"
python3 scripts/install-local.py install work/ressembly-0.5.0-local.zip "$HOME/.local/ressembly-alpha"
"$HOME/.local/ressembly-alpha/bin/ressembly" verify
"$HOME/.local/ressembly-alpha/bin/ressembly" doctor
"$HOME/.local/ressembly-alpha/bin/ressembly" --help
```

The parent directory must already exist and belong to the user. Use a new prefix with no symlinks along the path. Install new versions in separate prefixes. Paths with spaces are supported when quoted as shown. The installer rejects root. It leaves `.gdbinit`, shell profiles, global PATH, and system directories untouched. Dependencies are installed separately. The package does not require pip, web services, or AI. The examples also require a C compiler.

The `doctor` command discovers the environment, Python, Python-enabled GDB, and the system libc. It distinguishes general prerequisites from the heap profile and flags unsupported host libc versions. Heap modules separately check the **libc loaded into the process**. A successful discovery does not certify operation or guarantee that glibc symbols are available. The [R4/R5 report](PHASES-4-5.md) records the tested matrix.

Installed layout:

- `bin/ressembly` holds the local launcher.
- `lib/ressembly/src` holds the GDB and Python modules.
- `lib/ressembly/scripts` holds the offline CLIs.
- `lib/ressembly/examples`, `integrations`, and `docs` contain examples, bridges, and guides.
- `.ressembly-manifest.json` lists the installed files.

See [R6.md](R6.md) for the updated allocator profile matrix. Version 0.6.0 adds the Kali build of glibc 2.43-4. The R4/R5 evidence describes the earlier release.

## First run

Build the binary and store results **outside the installation prefix**:

```sh
mkdir work/alpha-demo-001
cc -g3 -O0 "$HOME/.local/ressembly-alpha/lib/ressembly/examples/heap_lab.c" -o work/alpha-demo-001/heap_lab
"$HOME/.local/ressembly-alpha/bin/ressembly" gdb work/alpha-demo-001/heap_lab
```

In GDB, enter each command on a separate line. Use `set pagination off` to disable display pauses.

```gdb
rs-help
break lab_ready
run
rs-context
rs-maps
```

The launcher runs GDB with `-nx`, disables autoloading, and loads the suite from the installation prefix using a Python bootstrap. It passes arguments after `gdb` directly as GDB arguments, with no shell command concatenation. Refer to the module guides and tested matrix for heap collection, glibc symbols, and optional features.

Available offline CLIs:

```sh
"$HOME/.local/ressembly-alpha/bin/ressembly" lab --help
"$HOME/.local/ressembly-alpha/bin/ressembly" experiment --help
"$HOME/.local/ressembly-alpha/bin/ressembly" plugins --help
"$HOME/.local/ressembly-alpha/bin/ressembly" ghidra --help
```

The plugin and Ghidra guides detail their trust procedures and scope. The launcher leaves Ghidra installation and plugin activation to the user.

## Uninstall and retain data

```sh
"$HOME/.local/ressembly-alpha/bin/ressembly" uninstall
```

Before removing anything, the uninstaller checks the manifest, contents, file modes, paths, and full inventory. It stops **before deleting files** if it finds modifications, links, or unexpected files or directories. It does not recursively delete unknown content. Review and save additions or modifications before retrying. There is no `--force` option.

Keep notes, personal plugins, and dossiers in separate working directories. Installation and uninstallation assume no other process is modifying the prefix at the same time. An interrupted installation can leave an incomplete prefix. A retry does not automatically remove it, so verify it before manual deletion. The operation does not guarantee recovery from every disk failure.

## Validation

Offline packaging tests:

```sh
python3 -m unittest discover -s tests -p test_packaging.py -v
```

For Linux validation, run `scripts/validate-package-linux.py` with a new directory. It checks two reproducible builds, clean installation in a prefix with spaces, verification, a real GDB run against project-owned C code, the CLI, rejection of tampered content, preservation of added files, and uninstallation. To test an existing archive, pass `NEW_DIRECTORY EXISTING_ZIP`. That path explicitly records that build reproducibility was not checked in the guest. Retain separate results for each distribution. Offline Mac tests cover packaging and do not certify GDB on Linux or Kali.
