# Preparing the first GitHub alpha

November 13, 2026. This report records preparation for GitHub. The final decisions on creating the repository, its visibility, and upload were reserved for explicit approval by the project owner.

The proposed scope was **experimental alpha 0.6.0** on Linux x86-64 with GDB and Python under GPL-3.0-or-later. This scope identifies the tested capabilities. It makes no claim of platform coverage beyond that matrix, superiority to GEF or Pwndbg, or automated exploitability assessment.

## Prepared material

- Source, project-owned C fixtures, tests, and repeatable validators.
- The full LICENSE and a NOTICE for original code. External tools retain their licenses and are excluded from the package.
- README, roadmap, local installation and removal instructions, and module limits.
- A deterministic package, SHA-256 manifest, and installation checks. The final result is recorded in `work/r6-gates/acceptance.json`.
- `.gitignore` excludes `work/`, bytecode, and Finder metadata. VM images, keys, dossiers, and downloaded dependencies are excluded from the publication scope.
- A limited key and token pattern scan of text files, recorded in `work/r6-gates/publication-pattern-scan.json`. This scan cannot establish the absence of all secrets.

## Publication notes

List the tested builds, identify TCG emulation on the Mac, and describe the glibc 2.36 regression in mixed userland. Adjacent versions such as 2.43.1, native hardware, multithreading, attach and fork, other allocators, and a GUI remain unvalidated. Ghidra integration is offline. Trusted plugin code runs with the user's permissions and without a sandbox.

Select source, examples, tests, integrations, guides, and license from the working directory. A release should attach the final package and its checksum. A checksum verifies file consistency. Publisher authenticity needs separate evidence.

Before uploading, check that final acceptance reports PASS and confirm the account or organization, repository name, and visibility with the project owner. As of R6, no remote repository or publication workflow had been created. The name and trademark had yet to be verified.
