/* A small symbol for static review in ELF and COFF artifact files. */
int review_counter(int value) {
    return value < 0 ? 0 : value;
}
