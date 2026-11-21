/* Export aggregate statistics from a small owned allocation. */
#include <jemalloc/jemalloc.h>
#include <stdio.h>

static void write_stats(void *destination, const char *chunk) {
    fputs(chunk, destination);
}

int main(void) {
    void *block = mallocx(4096, 0);
    if (block == NULL) {
        return 1;
    }
    malloc_stats_print(write_stats, stdout, "Jmdablxe");
    dallocx(block, 0);
    return fflush(stdout) == EOF || ferror(stdout);
}
