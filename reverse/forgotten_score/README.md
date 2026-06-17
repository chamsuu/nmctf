# The Forgotten Score

**Category:** Reverse Engineering
**Difficulty:** Medium-Hard
**Flag format:** `nmctf{...}`

## Description

A 14 KB reversing binary, encoded as a 20 MB WAV music file using a
1-bit-per-tone scheme. Decode the music back into a binary, then
reverse-engineer the binary to find the flag.

The vault is keyed by a **forgotten musical score** (a sequence of
note names) combined with a **Roman-numeral tempo**. Two melodies
are in the binary: the real one and a decoy. Only the right melody
unlocks the real flag.

The binary is intentionally minimal. It just prints `vault` unless
given `--inspect`, in which case it shows a decoy flag. The real
flag is never printed by the binary itself.

## Files (handout)

- `forgotten_score.wav` — the music-encoded binary

## Hints (in increasing order of obviousness)

1. The encoding is the same scheme as the
   [binary-music-maker](https://binarycodeconverter.com/binary-music-maker/)
   in "sequential" mode with two distinct pitches.
2. Each bit is a single 2 ms tone. `0` = 440 Hz, `1` = 880 Hz.
3. The WAV starts with a 16-bit preamble (`0xAA55`), then a 32-bit
   big-endian length, then the file bytes.
4. The binary contains a Roman numeral tempo and two melodies stored
   as arrays of `char*` pointers to single-letter strings.

## Solution outline

1. **Decode the WAV** to recover the binary. Each 2 ms slice of audio
   is one bit — `0` if the dominant frequency is closer to 440 Hz,
   `1` if it's closer to 880 Hz. The `wav2bin.py` script does this
   with a Goertzel filter.
2. **Reverse the binary.** Find:
   - The Roman tempo string `MMXXV` (= 2025) in rodata.
   - Two melody arrays: 8 `char*` pointers each pointing to a single
     letter in `A..G`. One is `CDEFGABC` (real), the other `GFEDCBAG`
     (decoy).
   - Two encrypted byte arrays: `enc_flag[]` (36 bytes) and
     `fake_enc[]` (27 bytes). Find them by looking for arrays of
     high-entropy bytes near the melodies.
3. **Derive the key** for each melody:
   `key = sum(ord(note) for note in melody) * 2025`
   - Real: `sum("CDEFGABC") * 2025 = 543 * 2025 = 0x10c737`
   - Decoy: `sum("GFEDCBAG") * 2025 = 547 * 2025 = 0x10e6db`
4. **XOR-decrypt** each encrypted array with the corresponding key.
   The one that starts with `nmctf{` is the real flag.
5. The flag is `nmctf{m3l0dy_0f_th3_f0rg0tt3n_sc0r3}`.

## Files in this directory

```
chall3/
  description            - the original challenge description
  README.md              - this file
  handout/
    forgotten_score.wav  - the music-encoded binary (the challenge)
  challenge/             - the source for the reversing binary
    chall.c
    build_flag.py
    flag_data.h          - generated; do not edit
    Makefile
    temporal_vault       - the binary (rebuild with `make`)
  src/
    bin2wav.py           - encoder
    wav2bin.py           - decoder
  solve.py               - full automated solve (uses src/wav2bin.py)
  WRITEUP.md             - detailed writeup
```
