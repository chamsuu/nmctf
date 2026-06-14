int validate_checksum(unsigned int *buf, int len) {
    unsigned int sum = 0;
    for (int i = 0; i < len; i++) sum ^= buf[i];
    return sum;
}

// Force Thumb mode function to generate gadgets
__attribute__((noinline))
int thumb_gadget_maker(int a, int b, int c, int d) {
    volatile int sum = a + b + c + d;
    return sum;
}