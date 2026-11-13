/* Owned single-thread teaching program, no allocator event markers. */
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <sys/mman.h>
volatile unsigned char *hist_p, *hist_other;
volatile uintptr_t hist_old;
volatile size_t hist_huge = SIZE_MAX;
volatile int hist_stage;
volatile uint64_t hist_slots[4];
void *(*volatile hist_realloc)(void *,size_t)=realloc;
void *(*volatile hist_calloc)(size_t,size_t)=calloc;
__attribute__((noinline)) void hist_ready(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline)) void hist_initialized(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline)) void hist_resized(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline)) void hist_moved(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline)) void hist_failed(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline)) void hist_done(void) { __asm__ volatile("" ::: "memory"); }
int main(int argc,char **argv) {
    hist_ready();
    if(argc>1 && strcmp(argv[1],"signal")==0) raise(SIGUSR1);
    hist_p=hist_calloc(4,8);
    hist_other=malloc(32);
    if(!hist_p || !hist_other) return 1;
    memset((void*)hist_other,0,32);
    if(argc>1 && strcmp(argv[1],"unreadable")==0) {
        uintptr_t page=(uintptr_t)hist_p & ~((uintptr_t)sysconf(_SC_PAGESIZE)-1);
        if(munmap((void*)page,(size_t)sysconf(_SC_PAGESIZE))) return 2;
        hist_initialized();
        return 0;
    }
    hist_stage=1; hist_initialized();
    hist_p[0]='A'; hist_p[8]='B'; hist_other[0]='C'; hist_p[0]='A';
    hist_old=(uintptr_t)hist_p;
    void *q=hist_realloc((void*)hist_p,16);
    if(!q) return 3;
    hist_p=q;
    hist_stage=2; hist_resized();
    hist_old=(uintptr_t)hist_p;
    q=hist_realloc((void*)hist_p,1024*1024);
    if(!q) return 4;
    hist_p=q;
    hist_stage=3; hist_moved();
    hist_old=(uintptr_t)hist_p;
    q=hist_realloc((void*)hist_p,hist_huge);
    if(q) { free(q); return 5; }
    hist_stage=4; hist_failed();
    q=hist_realloc((void*)hist_p,0);
    if(q) { free(q); return 6; }
    hist_p=NULL;
    free((void*)hist_other); hist_other=NULL;
    q=hist_calloc(hist_huge,2);
    if(q) { free(q); return 7; }
    q=hist_calloc(0,8); free(q);
    q=hist_realloc(NULL,32); if(!q) return 8; free(q);
    q=hist_realloc(NULL,0); free(q);
    q=hist_realloc(NULL,hist_huge); if(q) { free(q); return 9; }
    hist_stage=5; hist_done();
    return 0;
}
