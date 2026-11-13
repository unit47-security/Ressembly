/* Owned glibc/SysV x86-64 lab. No allocator markers, no invalid dereferences.
 * Checkpoints only stop GDB; allocations are observed at actual libc hooks. */
#include <stdint.h>
#include <stdlib.h>
#include <signal.h>
#include <string.h>
#include <gnu/libc-version.h>
#include <sys/mman.h>
#include <unistd.h>
volatile unsigned char *lab_p;
volatile unsigned char *lab_q;
const char *lab_libc;
volatile uint64_t resource_slots[4];
volatile size_t impossible_size = SIZE_MAX;
__attribute__((noinline)) void lab_ready(void) { __asm__ volatile ("" : : : "memory"); }
__attribute__((noinline)) void lab_initialized(void) { __asm__ volatile ("" : : : "memory"); }
__attribute__((noinline)) void lab_after_a(void) { __asm__ volatile ("" : : : "memory"); }
__attribute__((noinline)) void lab_after_same(void) { __asm__ volatile ("" : : : "memory"); }
__attribute__((noinline)) void lab_reused(void) { __asm__ volatile ("" : : : "memory"); }
__attribute__((noinline)) void lab_done(void) { __asm__ volatile ("" : : : "memory"); }
int main(int argc, char **argv) {
    lab_libc = gnu_get_libc_version();
    lab_ready();
    if (argc > 1 && strcmp(argv[1], "signal") == 0) raise(SIGUSR1);
    lab_p = malloc(32);
    if (!lab_p) return 1;
    memset((void *)lab_p, 0, 32);
    if (argc > 1 && strcmp(argv[1], "unreadable") == 0) {
        /* Negative collector test: remove this owned page, never dereference/free it. */
        uintptr_t page = (uintptr_t)lab_p & ~((uintptr_t)sysconf(_SC_PAGESIZE) - 1);
        if (munmap((void *)page, (size_t)sysconf(_SC_PAGESIZE)) != 0) return 3;
        lab_initialized();
        return 0;
    }
    lab_initialized();
    if (argc > 1 && strcmp(argv[1], "realloc") == 0) {
        void *replacement = realloc((void *)lab_p, 64);
        if (replacement) lab_p = replacement;
        free((void *)lab_p);
        return 0;
    }
    if (argc > 1 && strcmp(argv[1], "calloc") == 0) {
        void *extra = calloc(1, 32);
        if (extra) free(extra);
        free((void *)lab_p);
        return 0;
    }
    lab_p[0] = 'A';
    lab_after_a();
    lab_p[0] = 'A'; /* Same-value write is real source behavior, not a watch event. */
    lab_after_same();
    lab_p[0] = 'B';
    free((void *)lab_p);
    lab_q = malloc(32);
    if (!lab_q) return 1;
    memset((void *)lab_q, 'C', 32);
    lab_reused(); /* Reuse is allocator-dependent; don't assume it in implementation. */
    free((void *)lab_q);
    void (*volatile free_call)(void *) = free;
    free_call(NULL); /* Prevent compiler from erasing the actual free(NULL) call. */
    void *failed = malloc(impossible_size);
    if (failed) { free(failed); return 2; }
    lab_done();
    return 0;
}
