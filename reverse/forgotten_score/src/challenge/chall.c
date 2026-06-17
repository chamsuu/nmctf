/*
 * chall.c -- a stripped-down reversing challenge.
 *
 * The binary holds:
 *   - two static arrays of char* pointers pointing to single-character
 *     strings (one set is the "real" melody, the other a decoy);
 *   - two static byte arrays of encrypted data (one is the real flag,
 *     the other a decoy);
 *   - a small piece of code that decrypts one of the arrays when
 *     invoked with the right key.
 *
 * The key is derived from one of the melody arrays and a tempo
 * constant. Neither is printed by the binary at runtime.
 *
 * A `--inspect` mode decrypts the decoy using the decoy melody,
 * giving a fake flag. The real flag is never printed by the binary
 * itself -- it must be obtained by reverse-engineering the key.
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>

#include "flag_data.h"

/* Tempo constant (a Roman-numeral year, but we just hardcode the value
 * to make the binary smaller). The Roman form is in a string for
 * reverse engineers to find. */
__attribute__((used)) static const char tempo_str[] = "MMXXV";
#define TEMPO_VALUE 2025

/* Two melodies, both valid C-major-scale fragments, but only one
 * produces the real flag. */
__attribute__((used)) static const char *score_a[] = { "C", "D", "E", "F", "G", "A", "B", "C", NULL };
__attribute__((used)) static const char *score_b[] = { "G", "F", "E", "D", "C", "B", "A", "G", NULL };

static int nv(char c) {
    if (c >= 'A' && c <= 'G') return (int)(unsigned char)c;
    return 0;
}

static int sv(const char **s) {
    int t = 0, i = 0;
    while (s[i]) { t += nv(s[i][0]); i++; }
    return t;
}

static uint64_t dk(const char **s) {
    return (uint64_t)((uint64_t)sv(s) * (uint64_t)TEMPO_VALUE);
}

static void dx(const uint8_t *e, int n, uint64_t k, char *o) {
    uint8_t kb[8];
    for (int i = 0; i < 8; i++) kb[i] = (uint8_t)((k >> (i * 8)) & 0xFF);
    for (int i = 0; i < n; i++) o[i] = (char)(e[i] ^ kb[i % 8]);
    o[n] = '\0';
}

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--inspect") == 0) {
        uint64_t k = dk(score_b);
        char buf[64] = {0};
        dx(fake_enc, fake_enc_len, k, buf);
        printf("%s\n", buf);
    } else {
        printf("vault\n");
    }
    return 0;
}
