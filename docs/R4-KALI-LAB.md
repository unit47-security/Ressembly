# R4 — Local Kali amd64 lab

The VM started and provisioning completed. Tool availability alone does not establish module compatibility.

The lab used a **full Kali amd64 VM**, separate from the Debian VM used for R1 through R3. It reused only the QEMU 11.1.3 runtime extracted in the working directory. QEMU TCG runs a real x86-64 kernel and processes. The resulting measurements do not represent physical x86-64 CPU performance.

## Provenance

The official image `kali-linux-2026.3-cloud-genericcloud-amd64.tar.xz` was published on October 24, 2026 and downloaded from the fixed URL `https://kali.download/cloud-images/kali-2026.3/`. Its observed SHA-256 matched the official `SHA256SUMS` entry:

```text
087a9c43b6082b0a6aae666debe26c9edf6e3960a90952fc94720e755d628e58
```

The cloud directory provided the checksum. The request for `SHA256SUMS.gpg` returned HTTP 404. A detached signature was not verified. Verification consisted of comparing the image with the checksum obtained through the official HTTPS endpoint.

The archive contains only `disk.raw`, a sparse image with a virtual capacity of 25 GiB. The guest used a separate overlay and the original image was retained at this stage. The host had about 38 GiB free before download. The compressed archive was about 241 MiB.

## Local isolation

- Lab files were in `work/kali-lab/` and were excluded from distribution.
- SSH listened only on `127.0.0.1:22248` with user `lab`, a dedicated local key, and password authentication disabled.
- The host Mac's SSH, shell, and global package settings were untouched.
- Cloud-init installed GDB, Python, GCC, binutils, and libc symbols only in the guest.
- The lab required no cloud service, account, payment, or publication.

The historical start, access, and shutdown workflow ran from the project root:

```sh
sh work/kali-lab/start-lab.sh
sh work/kali-lab/ssh-lab.sh 'cat /etc/os-release; uname -m; gdb --version; getconf GNU_LIBC_VERSION'
sh work/kali-lab/stop-lab.sh
```

Use one instance per overlay. Keep keys, images, and provisioning data in the lab and out of the Ressembly package.

## Compatibility criteria

The matrix treats installation, debugger and memory commands, static tools, and dossiers separately from modules tied to a specific glibc version. Heap modules are expected to reject unsupported glibc explicitly. A successful installation alone does not establish that all modules work.

## Primary sources consulted

- [Official Kali downloads](https://www.kali.org/get-kali/).
- [Current cloud image index](https://kali.download/cloud-images/current/), which listed Kali 2026.3 amd64 when checked.
- [Official image download and verification guidance](https://www.kali.org/docs/introduction/download-official-kali-linux-images/).

Local logs and manifests included `work/kali-lab/provision-manifest.json`, `archive-members.json`, `seed-build.log`, and `serial.log`. Validation dossiers were added after the runs.

## Recorded versions

`work/kali-lab/guest-versions.txt` records Kali 2026.3, kernel `7.1.5+kali-cloud-amd64`, glibc and libc6-dbg `2.43-4`, GDB `17.2-1+b1`, GDB Python `3.14.7`, GCC `16.2.0`, and GNU binutils `2.47`. Cloud-init ended with `status: done` and the `provision-ready` marker.

This glibc differs from the originally validated 2.36. The subsequent dossier separates successful installation and general module tests from explicit rejection by modules with unsupported heap profiles.

## Installed pilot tests

The `ressembly-r4-pilot003.zip` pilot, SHA-256 `0efc6a048de64433281d7b0e10e8b023b814f9c0b04208190f75cc8380d0c965`, passed 16 installation, launch, and uninstall checks in a new prefix containing spaces. The test environment contained no source checkout. The dossier is `work/kali-lab/package-pilot003`.

The additional installed-module matrix passed 10 checks in `work/kali-lab/installed-pilot003`. It checked debugger context and bytes against direct GDB commands, separate annotations from an explicitly trusted plugin, saving and reopening a real snapshot, static ELF inspection, integrity verification, and uninstall. **R2, the structural heap view, and R5 history explicitly rejected glibc 2.43** without writing misleading captures. The general modules worked within the tested scope. Heap support on that Kali build was outside the pilot's scope.

Independent plugin validation from selected sources passed nine contract tests and 17 checks across two GDB sessions in `work/kali-lab/plugins-validation/002`. The first attempt was retained after a quoting error in the validator. The fix required no changes to Ressembly. A mutation that removed verification of the trusted hash was caught in a separate copy.

The final archive requires a new dossier with its own hash.

## Final validation and evidence retention

The final archive's designated validation paths are `work/kali-lab/package-final` and `work/kali-lab/installed-final`. The corresponding `validation.json` records results and checks actually performed. The archive digest is retained with the evidence. A designated path does not imply a pass before testing.

The user authorized VM removal after testing. Results, versions, logs, and manifests are copied to the host before removal, and the coordinator records removal separately. The start commands above describe the historical lab. Heavy archives, disks, and lab keys are kept separate from retained evidence.
