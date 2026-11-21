# R5 — opt-in extended allocator history

R6 extended the profile to Kali glibc 2.43-4. See [R6](R6.md) for layout and return-handling differences. The glibc 2.36 results below are historical.

R5 preserves the R2 collector and stores extended history using `ressembly.object-history.v2`, with the target SHA-256 and a capture UUID. A GDB session can use one collector version for one capture. Closing a capture does not make it possible to load the other collector in the same session.

## Scope

The initial lab used Linux x86-64, local GDB, a launched single-threaded process, and glibc 2.36. The profile records selected glibc malloc, free, calloc, and realloc calls and observed returns. Nested and reentrant allocator calls during a transaction are outside coverage. This also applies to calls from a signal handler that interrupts a transaction.

The module reuses the validated run checks, saving, and continuation behavior. The extended model records realloc transactions and separate observation windows. The only R2 behavior change prevents it from starting after a v2 capture. Old event files retain their original format.

## Operation semantics

- calloc retains the element count, element size, mathematical product, and size_t overflow status. The zeroing operation does not become a sequence of observed writes.
- realloc with a null old pointer records a new allocation on the observed return. The internal malloc is not counted again. A request of size zero provides no region to observe.
- A failed nonzero realloc preserves the previous object's identity and size.
- A successful realloc closes the prior identity and creates a successor even if the address is unchanged. This is an object-history convention. It does not assert that the allocator physically freed and reallocated the same memory.
- Realloc with a non-null pointer and zero size follows the declared glibc behavior for the profile. That behavior is allocator-specific.
- A missing return or exhausted budget leaves the transaction `unknown_after_incomplete_realloc`. The record does not invent a successful realloc or free.

## Observation regions and code references

Up to four nonoverlapping, naturally aligned regions of 1, 2, 4, or 8 bytes can be selected within requested object sizes. Every window has its own identity, sample, activation, events, and termination. Coverage requires successful insertion on resume. External hardware slot usage may prevent insertion and software fallback is refused. Same-value writes may be absent.

An object's windows end at free or realloc entry. A failed realloc still requires a new selection. Windows on other objects remain separate.

Events carry stop PCs and may include a function, source, and module mapping. A file offset comes from the on-disk mapping plus the offset within that mapping. It is distinct from a load-base-relative RVA. Anonymous mappings have no known file offset. A caller return site and a watchpoint stop PC do not establish the instruction responsible for a write.

## Validation

The test fixture is project-owned and emits no allocator markers. The matrix covers calloc and realloc argument and return cases, requested region coverage, multiple objects, hardware limits, unavailable memory, signals, incomplete returns, event budgets, and collector conflicts. An independent GDB path compares zeroing, in-place and moving realloc, and retention after failure.

The Debian validation passed 14 cases in `work/r5-history-003`. The independent repeat passed the 14 cases in `work/r5-history-independent-001`. Both dossiers contain source hashes. Five offline model tests passed and detected a mutation of the zero-size realloc policy. The integrated suite was checked with two load orders and a reload in `work/r5-independent-regression-001`.

The emulated Debian x86-64 lab does not establish native performance, current Kali support, other libc versions or allocators, attach, fork, or multithreaded collection.

## Primary sources

- [glibc 2.36 allocator source](https://raw.githubusercontent.com/bminor/glibc/glibc-2.36/malloc/malloc.c).
- [GNU realloc](https://sourceware.org/glibc/manual/latest/html_node/Changing-Block-Size.html) and [GNU calloc](https://sourceware.org/glibc/manual/latest/html_node/Allocating-Cleared-Space.html).
- [GDB watchpoints](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Watchpoints.html).
- [GDB FinishBreakpoint](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Finish-Breakpoints-in-Python.html).
