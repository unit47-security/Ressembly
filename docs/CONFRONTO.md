# Tool comparison · October 24, 2026

This review examined primary sources. Benchmarks and reported issues in other tools required separate tests. The stable and current documentation changes over time, so the next lab needed to record exact versions and compatibility. Novelty, superiority, and market demand were unverified.

| Tool | Documented capabilities | Relevant limits |
|---|---|---|
| GEF | Register, stack, and code context, memory maps, search, and glibc heap views. A helper follows allocations and frees and flags possible anomalies. | The helper is described as unstable, with false positives and missed cases. It covers selected events. |
| Pwndbg | Context, maps, telescope, glibc heap views, cyclic and checksec utilities, and selected heap tracking with caller attribution, relative addresses, and hardware breakpoints. | The documentation lists use-after-free detection. Other detections and support for different allocator or libc builds require verification. |
| GDB | Python APIs for breakpoints and memory reads, watchpoints, record and replay, and reverse execution. | A watchpoint can miss a write that leaves the value unchanged. Hardware watchpoints are limited in number and size. Software fallback can be expensive. Branch tracing omits memory data. |
| rr | Linux record and replay with GDB and reverse watchpoints. | CPU, kernel, and syscall constraints apply. It emulates one core. Memory shared with processes outside the recorded tree is unsupported. |
| Tenet | x86 and AMD64 trace exploration in IDA, with a timeline and searches for reads and writes. | Coverage depends on the input trace. The reader can miss external and kernel accesses omitted by the recorder. |

Primary sources consulted:

- GEF: [context](https://hugsy.github.io/gef/commands/context/), [vmmap](https://hugsy.github.io/gef/commands/vmmap/), [search-pattern](https://hugsy.github.io/gef/commands/search-pattern/), [heap](https://hugsy.github.io/gef/commands/heap/), [heap analysis helper](https://hugsy.github.io/gef/commands/heap-analysis-helper/).
- Pwndbg: [command catalog](https://pwndbg.re/stable/commands/), [heap tracking documentation](https://pwndbg.re/stable/commands/linux_libc_elf/track-heap/), [upstream releases](https://github.com/pwndbg/pwndbg/releases).
- GDB: [watchpoints](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Watchpoints.html), [record and replay](https://www.sourceware.org/gdb/download/onlinedocs/gdb.html/Process-Record-and-Replay.html), [Python breakpoints](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Breakpoints-In-Python.html), [memory reads](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Inferiors-In-Python.html).
- [rr project](https://rr-project.org/) and [Tenet upstream](https://github.com/gaasedelen/tenet).

## Implications

Existing tools already offered object history, watchpoints, and timelines. The hypothesis was that a workflow with generation-based identities, evidence references, and explicit limits would be useful. The planned analysis modules needed to be compared with existing capabilities. The October 24 audit recorded no integrations with these tools.

## Experimental comparison pending at the time of the audit (R0)

The proposed comparison used three project-owned diagnostics fixtures with clean controls and memory-error categories. It called for an authorized Linux lab with recorded hashes, compiler and glibc versions, tool revisions, and a repeatable task order. Evaluation would preserve logs and manual observations and measure time, steps, missed events, and interpretation errors across repetitions. Tool behavior would be judged against its documented contract. This audit did not run those tests.

## Historical references

The earlier Windows comparison included [x64dbg Trace](https://help.x64dbg.com/en/latest/gui/views/Trace.html), [Lighthouse](https://github.com/gaasedelen/lighthouse), [Dragon Dance](https://github.com/0ffffffffh/dragondance), [WinDbg TTD](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/time-travel-debugging-overview), and [Pernosco](https://pernos.co/). These references document the earlier proposal.
