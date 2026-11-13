/* Owned single-thread teaching target. Marker kinds: 1 alloc, 2 free completed,
 * 3 snapshot. Markers are an explicit protocol, not general allocator hooks. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#ifdef __GLIBC__
#include <gnu/libc-version.h>
#endif
__attribute__((noinline)) void rs_event(int kind, uintptr_t ptr, size_t size) {
    __asm__ volatile ("" : : "r"(kind), "r"(ptr), "r"(size) : "memory");
}
static void release(void *p) {
    uintptr_t address = (uintptr_t)p;
    free(p);
    rs_event(2, address, 0);
}
int main(void) {
#ifdef __GLIBC__
    printf("allocator=glibc version=%s\n", gnu_get_libc_version());
#else
    puts("allocator=non-glibc; unsupported live acquisition platform");
#endif
    char *p = malloc(32);
    rs_event(1, (uintptr_t)p, 32);
    if (!p) return 1;
    memset(p, 'A', 32);
    rs_event(3, (uintptr_t)p, 32);
    p[4] = 'B';
    rs_event(3, (uintptr_t)p, 32);
    release(p);
    char *q = malloc(32); /* Reuse is allocator-dependent, never assumed. */
    rs_event(1, (uintptr_t)q, 32);
    if (!q) return 1;
    memset(q, 'C', 32);
    rs_event(3, (uintptr_t)q, 32);
    release(q);
    return 0;
}
