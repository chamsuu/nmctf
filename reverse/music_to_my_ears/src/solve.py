#!/usr/bin/env python3
"""
Full solve script for "Music to My Ears" (chall3).

Given a WAV file containing the music-encoded temporal_vault binary, this
script:
  1. Decodes the WAV back to the binary          (src/wav2bin.py)
  2. Locates the enc_flag[] bytes in the binary  (XOR-prefix scan)
  3. Locates the Roman tempo and the melody      (rodata scan)
  4. Computes the key, XOR-decrypts, prints the flag.

The script does not hardcode any answer; it derives everything from the
binary's static data, the way a human solver would.
"""

import sys
import re
import struct
import subprocess

def step_decode(wav_path: str) -> str:
    out = wav_path.replace(".wav", ".decoded")
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wav2bin = os.path.join(script_dir, "wav2bin.py")
    r = subprocess.run(
        ["python3", wav2bin, wav_path, out],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"[!] wav2bin failed: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    for line in r.stdout.splitlines():
        print(f"    {line}")
    return out

def extract_strings(data, min_len=3):
    """Return all printable strings of length >= min_len."""
    out = []
    cur = b""
    for b in data:
        if 0x20 <= b < 0x7f:
            cur += bytes([b])
        else:
            if len(cur) >= min_len:
                out.append(cur.decode("latin-1"))
            cur = b""
    if len(cur) >= min_len:
        out.append(cur.decode("latin-1"))
    return out

def find_roman_tempo(strings):
    """Find a Roman numeral that decodes to a number 1..3999."""
    ROMAN_VAL = {'I':1, 'V':5, 'X':10, 'L':50, 'C':100, 'D':500, 'M':1000}
    def from_roman(s):
        total, prev = 0, 0
        for c in reversed(s):
            v = ROMAN_VAL.get(c, 0)
            total += -v if v < prev else v
            prev = v
        return total if 1 <= total <= 3999 else 0
    for s in strings:
        if re.fullmatch(r"[IVXLCDM]+", s) and 1 < len(s) <= 9:
            v = from_roman(s)
            if v:
                return s, v
    return None, 0

def find_melody_candidates(data):
    """Find all 8-pointer arrays of single A..G characters."""
    candidates = []
    for off in range(0, len(data) - 64, 8):
        notes = []
        valid = True
        for i in range(8):
            ptr = struct.unpack_from("<Q", data, off + i * 8)[0]
            if ptr >= len(data) - 1 or data[ptr] not in b'ABCDEFG' or data[ptr+1] != 0:
                valid = False
                break
            notes.append(chr(data[ptr]))
        if valid and len(set(notes)) >= 5:
            candidates.append((off, ''.join(notes)))
    return candidates

def find_enc_flag_offset(data, key):
    """Find the byte offset where bytes XORed with the 8-byte key give 'nmctf{' prefix.
    Returns (offset, length) or (-1, 0)."""
    kb = key.to_bytes(8, "little")
    expected_prefix = b"nmctf{"
    for off in range(len(data) - 10):
        if all((data[off + i] ^ kb[i]) == expected_prefix[i] for i in range(5)):
            # scan forward to find end of flag ('}' after decryption)
            for length in range(10, 128):
                if off + length > len(data):
                    break
                if (data[off + length - 1] ^ kb[(length - 1) % 8]) == ord('}'):
                    return off, length
    return -1, 0

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <music.wav>", file=sys.stderr)
        sys.exit(1)
    wav = sys.argv[1]

    print("== Step 1: decode music -> binary ==")
    binary = step_decode(wav)
    with open(binary, "rb") as f:
        data = f.read()
    print(f"    Binary size: {len(data)} bytes")

    print("\n== Step 2: extract strings ==")
    strings = extract_strings(data)
    print(f"    Found {len(strings)} strings (len >= 3).")

    print("\n== Step 3: find the Roman tempo ==")
    tempo_str, tempo_val = find_roman_tempo(strings)
    print(f"    Roman tempo: {tempo_str} = {tempo_val}")

    print("\n== Step 4: find melody candidates ==")
    cands = find_melody_candidates(data)
    if not cands:
        print("    No melody candidates found.", file=sys.stderr)
        sys.exit(1)
    for off, m in cands:
        s = sum(ord(c) for c in m)
        print(f"    offset 0x{off:04x}: {m!r}  (sum = {s})")

    print("\n== Step 5: try each melody as the key, look for the flag ==")
    best = None
    for off, melody in cands:
        note_sum = sum(ord(c) for c in melody)
        key = (note_sum * tempo_val) & 0xFFFFFFFFFFFFFFFF
        enc_off, enc_len = find_enc_flag_offset(data, key)
        if enc_off >= 0:
            enc = data[enc_off:enc_off + enc_len]
            kb = key.to_bytes(8, "little")
            flag = bytes([b ^ kb[i % 8] for i, b in enumerate(enc)])
            try:
                flag_s = flag.decode()
            except UnicodeDecodeError:
                continue
            if flag_s.startswith("nmctf{") and (best is None or enc_len > best[2]):
                best = (melody, key, enc_len, enc_off, flag_s)
                print(f"    [*] Melody {melody!r} (key=0x{key:016x}) -> {flag_s!r}")
    if best:
        melody, key, enc_len, enc_off, flag_s = best
        print(f"\n    [+] Best: melody {melody!r} at offset 0x{enc_off:x}, length {enc_len}")
        print(f"\n== FLAG: {flag_s} ==")
        return
    print("    No candidate produced a valid flag.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
