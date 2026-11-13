#define _GNU_SOURCE
#include <stdint.h>
#include <stddef.h>
#include <sys/mman.h>
#include <unistd.h>
unsigned char lab_bytes[64] = "abcabcabc--owned-memory--";
uintptr_t lab_chain[3];
void *lab_guard;
size_t lab_page;
volatile unsigned lab_stage;
__attribute__((noinline)) void debug_stop(void) { __asm__ volatile("" ::: "memory"); }
int main(void) {
    lab_page = (size_t)sysconf(_SC_PAGESIZE);
    lab_guard = mmap(NULL, lab_page * 2, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (lab_guard == MAP_FAILED) return 2;
    ((unsigned char *)lab_guard)[lab_page - 2] = 'a';
    ((unsigned char *)lab_guard)[lab_page - 1] = 'b';
    if (mprotect((char *)lab_guard + lab_page, lab_page, PROT_NONE)) return 3;
    lab_chain[0] = (uintptr_t)&lab_chain[1];
    lab_chain[1] = (uintptr_t)&lab_chain[2];
    lab_chain[2] = (uintptr_t)&lab_chain[0];
    lab_stage = 1;
    debug_stop();
    lab_bytes[0] = 'z';
    lab_chain[2] = 0;
    lab_stage = 2;
    debug_stop();
    munmap(lab_guard, lab_page * 2);
    return 0;
}
