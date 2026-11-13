/* Owned non-vulnerable program: compile with different ELF/stack flags. */
#include <stdio.h>
__attribute__((noinline)) int lab_copy(int value) {
    volatile char buffer[32] = {0};
    buffer[0] = (char)value;
    return buffer[0];
}
int main(void) {
    printf("lab=%d\n", lab_copy(7));
    return 0;
}
