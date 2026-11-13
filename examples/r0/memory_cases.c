/* Owned teaching corpus. "bad uaf" intentionally executes undefined behavior.
 * No address reuse, stale value, crash, or exploitability is assumed. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

unsigned char *rs_address;
size_t rs_length;
volatile unsigned rs_observed;
__attribute__((noinline)) void rs_checkpoint(const char *label) {
    __asm__ volatile("" : : "r"(label) : "memory");
}
static void sample(const char *label, void *address, size_t length) {
    rs_address = address;
    rs_length = length;
    rs_checkpoint(label);
}
static int buffer_case(int bad) {
    unsigned char storage[16];
    memset(storage, 'A', sizeof storage);
    sample("buffer-before", storage, sizeof storage);
    /* Logical buffer is bytes [0,8), adjacent sentinel is [8,16).
     * Both writes remain inside the actual C array: no C out-of-bounds UB. */
    memset(storage, 'B', bad ? 12 : 8);
    sample("buffer-after", storage, sizeof storage);
    rs_observed = storage[8];
    printf("logical_sentinel_changed=%u\n", rs_observed != 'A');
    return (rs_observed != 'A') == bad ? 0 : 2;
}
static int uaf_case(int bad) {
    unsigned char *p = malloc(32);
    if (!p) return 3;
    memset(p, 'A', 32);
    sample("heap-live", p, 32);
    if (bad) {
        uintptr_t stale = (uintptr_t)p;
        free(p);
        /* Integer retained for debugger display. This is not a valid object. */
        sample("heap-freed-before-access", (void *)stale, 32);
        rs_observed = *((volatile unsigned char *)stale + 16); /* intentional lab UAF */
        sample("heap-freed-after-access", (void *)stale, 32);
    } else {
        rs_observed = p[16];
        sample("heap-live-after-access", p, 32);
        free(p);
    }
    puts(bad ? "uaf_attempted=1; value/crash not specified" : "uaf_attempted=0");
    return 0;
}
static void benign_a(void) { rs_observed = 1; }
static void benign_b(void) { rs_observed = 2; }
static int pointer_case(int bad) {
    void (*slot)(void) = benign_a;
    sample("pointer-before", &slot, sizeof slot);
    if (bad) slot = benign_b; /* Both pointers name harmless owned functions. */
    sample("pointer-after", &slot, sizeof slot);
    slot();
    printf("selected_benign_function=%u\n", rs_observed);
    return rs_observed == (bad ? 2u : 1u) ? 0 : 2;
}
int main(int argc, char **argv) {
    if (argc != 3 || (strcmp(argv[2], "good") && strcmp(argv[2], "bad"))) return 64;
    int bad = !strcmp(argv[2], "bad");
    if (!strcmp(argv[1], "buffer")) return buffer_case(bad);
    if (!strcmp(argv[1], "uaf")) return uaf_case(bad);
    if (!strcmp(argv[1], "pointer")) return pointer_case(bad);
    return 64;
}
