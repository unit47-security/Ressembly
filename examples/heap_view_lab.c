#include <stdlib.h>
#include <stdint.h>

void *small[9], *large, *guard, *separator, *sort_request;
uintptr_t small_addresses[9], large_address;
volatile int heap_view_stage;
__attribute__((noinline)) void heap_view_checkpoint(void) { __asm__ volatile("" ::: "memory"); }

int main(void) {
    for (int i = 0; i < 9; i++) {
        small[i] = malloc(32);
        if (!small[i]) return 2;
        small_addresses[i] = (uintptr_t)small[i];
    }
    separator = malloc(32);
    large = malloc(0x500);
    guard = malloc(32);
    if (!separator || !large || !guard) return 2;
    large_address = (uintptr_t)large;
    heap_view_stage = 1;
    heap_view_checkpoint();
    for (int i = 0; i < 9; i++) free(small[i]);
    heap_view_stage = 2;
    heap_view_checkpoint();
    free(large);
    heap_view_stage = 3;
    heap_view_checkpoint();
    sort_request = malloc(0x600);
    if (!sort_request) return 2;
    heap_view_stage = 4;
    heap_view_checkpoint();
    free(sort_request);
    free(guard);
    free(separator);
    return 0;
}
