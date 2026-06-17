#!/usr/bin/env python3
"""
Build script: encrypts flag with a key derived from a "forgotten musical score".

The score is a melody (sequence of note names A..G) whose ASCII values are
summed and then multiplied by a Roman-numeral tempo offset, forming the
64-bit little-endian XOR key.

Real melody:  CDEFGABC  (C-major scale ascending, then a leading tone)
Roman offset: MMXXV = 2025 (a "tempo" or "time" multiplier)
Key formula:  sum(ord(note) for note in melody) * 2025

Decoy:  same Roman offset but with a different melody (descending scale)
        -> wrong key -> "nmctf{n0_m3l0dy_n0_m3ss4g3}"
"""

FLAG     = b"nmctf{m3l0dy_0f_th3_f0rg0tt3n_sc0r3}"
FAKE_FLAG = b"nmctf{n0_m3l0dy_n0_m3ss4g3}"

# Real melody: ascending C major scale then a leading tone back to C
REAL_MELODY = b"CDEFGABC"
# Decoy: descending scale (same notes, but reversed -- a "wrong" interpretation)
FAKE_MELODY = b"GFEDCBAG"

# Roman numeral tempo offset
TEMPO = 2025  # MMXXV

def derive_key(melody: bytes, tempo: int) -> int:
    return (sum(melody) * tempo) & 0xFFFFFFFFFFFFFFFF

def xor_encrypt(data: bytes, key: int) -> bytes:
    kb = key.to_bytes(8, 'little')
    return bytes([b ^ kb[i % 8] for i, b in enumerate(data)])

def to_c_array(name, data):
    hex_vals = ', '.join(f'0x{b:02x}' for b in data)
    return (f"__attribute__((used)) static const uint8_t {name}[] = {{{hex_vals}}};\n"
            f"static const int {name}_len = {len(data)};")

real_key = derive_key(REAL_MELODY, TEMPO)
fake_key = derive_key(FAKE_MELODY, TEMPO)
enc      = xor_encrypt(FLAG,     real_key)
fake_enc = xor_encrypt(FAKE_FLAG, fake_key)

with open("flag_data.h", "w") as f:
    f.write("// Auto-generated -- do not edit\n")
    f.write(f"// Real melody ({REAL_MELODY!r}) + Roman tempo (MMXXV = {TEMPO}) => XOR key for the real flag\n")
    f.write(f"// key = 0x{real_key:016x}\n")
    f.write(to_c_array("enc_flag", enc) + "\n")
    f.write(f"// Decoy melody ({FAKE_MELODY!r}) + same tempo => different key (decoy flag)\n")
    f.write(f"// key = 0x{fake_key:016x}\n")
    f.write(to_c_array("fake_enc", fake_enc) + "\n")

assert xor_encrypt(enc, real_key) == FLAG
assert xor_encrypt(fake_enc, fake_key) == FAKE_FLAG
print(f"[+] Real flag: {FLAG.decode()}")
print(f"[+] Real key:  0x{real_key:016x}")
print(f"[+] Decoy flag: {FAKE_FLAG.decode()}")
print(f"[+] Decoy key:  0x{fake_key:016x}")
print("[+] Written to flag_data.h")
