#include <stdio.h>
#include <stddef.h>

unsigned char experiment_input[16];
size_t experiment_count;
volatile unsigned int experiment_stage;

__attribute__((noinline)) void experiment_checkpoint(void) {
    __asm__ volatile("" ::: "memory");
}

int main(void) {
    experiment_count = fread(experiment_input, 1, sizeof experiment_input, stdin);
    if (ferror(stdin)) return 1;
    experiment_stage = 1;
    experiment_checkpoint();
    experiment_stage = 2;
    experiment_checkpoint();
    return 0;
}
