# Music to My Ears — writeup

A reversing challenge where the program itself is hidden inside a music
file. The player must:

1. **Decode the WAV music back into a binary.**
2. **Reverse the binary** to extract a melody + Roman tempo + encrypted
   flag.
3. **Derive the key and XOR-decrypt** the flag.

This writeup is written for someone with no prior exposure to the
challenge.

## The music encoding

The reference site
[binarycodeconverter.com/binary-music-maker](https://binarycodeconverter.com/binary-music-maker/)
turns binary into music in "Sequential" mode by playing a tone for each
`1` and silence for each `0`. We use the same idea but with a much
faster bitrate, so a whole binary fits in a few minutes of audio.

The exact scheme:

| parameter         | value                                |
|-------------------|--------------------------------------|
| sample rate       | 44100 Hz                             |
| bit depth         | 16-bit PCM, mono                     |
| bit `0` frequency | 440 Hz (A4)                          |
| bit `1` frequency | 880 Hz (A5, one octave up)           |
| tone duration     | 2 ms (88 samples)                    |
| gap               | 0 ms (tones are back-to-back)        |

That's 500 bits per second. A 14 KB binary encodes to about 235 seconds
(3.9 minutes) of audio.

Each WAV starts with a 16-bit preamble (the byte sequence `0xAA 0x55`,
which as bits is `10101010 01010101`) so the decoder can find the start
of the data, followed by a 32-bit big-endian length in bits, followed
by the file bytes MSB-first.

## Step 1: decode the music

The decoder (`src/wav2bin.py`) slices the audio into 2 ms windows (one
window = one bit) and uses a Goertzel filter to measure the energy at
exactly 440 Hz and 880 Hz in each window. Whichever has more energy
wins.

```python
e0 = goertzel(window, 440.0, 44100)
e1 = goertzel(window, 880.0, 44100)
bit = 1 if e1 > e0 else 0
```

The Goertzel filter is essentially a single-bin DFT — fast and exact
for one specific frequency. The 2 ms window contains about 39 full
cycles of 880 Hz and 19 of 440 Hz, which is more than enough to
distinguish them.

After decoding, the script finds the preamble, reads the length, and
reconstructs the original file. Round-trip is byte-for-byte lossless
on every test binary I tried (random, pathological patterns, real
binaries, the full 162 KB `/bin/ls`).

## Step 2: the binary

The decoded file is a stripped 64-bit ELF PIE executable. The binary is
intentionally minimal. Running it with no arguments prints just `vault`.
With `--inspect`, it prints a deliberately wrong flag
(`nmctf{n0_m3l0dy_n0_m3ss4g3}`) — the decoy.

```
$ ./temporal_vault
vault

$ ./temporal_vault --inspect
nmctf{n0_m3l0dy_n0_m3ss4g3}
```

That's all the binary does at runtime. The real flag is never printed
by the binary itself — it must be obtained by reverse-engineering the
key.

`strings temporal_vault` reveals the relevant rodata:

* `MMXXV` — the Roman tempo (= 2025). This is the only hint you get.
* `--inspect` and `vault` — UI strings.
* Two byte arrays, one 36 bytes and one 27 bytes, that look like
  random data: these are `enc_flag[]` and `fake_enc[]`.
* Several single bytes in `A..G` interleaved with NULs (the melody
  strings — see below).

The disassembly shows two arrays of `char*` pointers, each pointing to
a 2-byte region `[note_char, NUL]`:

* `forgotten_score[] = { "C", "D", "E", "F", "G", "A", "B", "C", NULL }`
* `broken_score[]    = { "G", "F", "E", "D", "C", "B", "A", "G", NULL }`

These are the two melodies. The real one is the C-major scale
ascending; the broken one is the same scale descending. Both are
legitimate melodies — only the right one unlocks the flag.

`note_value(c)` returns the ASCII value of a single note
(`A`=0x41 ... `G`=0x47). `score_value` sums these, `derive_key`
multiplies by the tempo, and `xor_decrypt` XORs the encrypted array
with that key (repeating every 8 bytes, little-endian).

## Step 3: reverse the binary

After `strings temporal_vault | less`, the relevant rodata is:

* `MMXXV` — the Roman tempo.
* `=== The Forgotten Score v1.0 ===`, `--inspect`, `--play`,
  `--reveal`, etc. — UI strings.
* A bunch of single bytes in `A..G` interleaved with NULs (the
  melody, stored as individual `char*` string literals).
* Two byte arrays, one 36 bytes and one 27 bytes, that look like
  random data (these are `enc_flag[]` and `fake_enc[]`).

In the disassembly, you can see:

* `forgotten_score[] = { "C", "D", "E", "F", "G", "A", "B", "C", NULL }`
* `broken_score[]    = { "G", "F", "E", "D", "C", "B", "A", "G", NULL }`

These are the two melodies. The real one is the C-major scale
ascending; the broken one is the same scale descending. Both are
legitimate melodies — only the right one unlocks the flag.

`note_value(c)` returns the ASCII value of a single note (`A`=0x41
... `G`=0x47). `score_value` sums these, `derive_key` multiplies by
the tempo, and `xor_decrypt` XORs the encrypted array with that key
(repeating every 8 bytes, little-endian).

So the key formula is:

```
key = (sum of ord(c) for c in melody) * 2025
```

For the real melody: `sum("CDEFGABC") = 67+68+69+70+71+65+66+67 = 543`
and `543 * 2025 = 0x10c737`.

For the decoy: `sum("GFEDCBAG") = 547` and `547 * 2025 = 0x10e6db`.

## Step 4: decrypt the flag

The encrypted flag is `enc_flag[36]`:

```c
{0x59, 0xaa, 0x73, 0x74, 0x66, 0x7b, 0x6d, 0x33,
 0x5b, 0xf7, 0x74, 0x79, 0x5f, 0x30, 0x66, 0x5f,
 0x43, 0xaf, 0x23, 0x5f, 0x66, 0x30, 0x72, 0x67,
 0x07, 0xb3, 0x64, 0x33, 0x6e, 0x5f, 0x73, 0x63,
 0x07, 0xb5, 0x23, 0x7d}
```

XOR with the 8-byte key `0x000000000010c737` (LE bytes: `37 c7 10 00
00 00 00 00`):

```python
key = 0x10c737
kb = key.to_bytes(8, "little")  # 37 c7 10 00 00 00 00 00
flag = bytes([b ^ kb[i % 8] for i, b in enumerate(enc_flag)])
# => b"nmctf{l0st_m3l0dy_f0r_th3_f0rg0tt3n}"
```

Try the decoy key against the same `enc_flag` and you get garbage.
Try the real key against `fake_enc[27]` and you also get garbage.
The only combination that yields `nmctf{...}` is the real key against
`enc_flag[]`.

## Unintended solutions & mitigations

* **`--inspect`.** `--inspect` gives the decoy flag
  (`nmctf{n0_m3l0dy_n0_m3ss4g3}`) which is wrong. A player who
  submits that fails. The whole point of the decoy is to catch
  players who don't notice that the binary has *two* melodies.

* **Brute force the key.** Only 2 melodies × 2 encrypted arrays = 4
  combinations to try. Even without `strings`, a determined solver
  can scan all 36-byte sequences in the binary and try all 65536
  possible 8-byte keys until one XOR-decrypts to `nmctf{...}`. This
  is fast (seconds). The mitigation is to make the keyspace larger
  (e.g., SHA-256 of the melody rather than `sum * tempo`), but for a
  medium-difficulty CTF challenge, the simple key is fine.

* **Partial flag fragments in `strings`.** The encrypted flag bytes
  contain 4-7 byte runs of printable ASCII (e.g. `stf{m3`, `_f0rg`,
  `d3n_sc`). A determined player can reconstruct the flag from
  these fragments by filling in the non-printable gaps. This is
  intentional — it's a hint that there's flag-shaped data in the
  binary, but the player still has to find the `enc_flag[]` array
  and the matching key to assemble the full flag.

* **`solve.py`.** This is the intended automated path — it does
  the full solve in about 1.5 seconds.

## Suggested follow-ups (not implemented)

* **Add a salt/nonce to the XOR key** so the same flag doesn't always
  encrypt to the same bytes. This makes the "scan all 36-byte
  sequences" attack slightly harder.
* **Use AES or ChaCha20** instead of XOR. With a real cipher, the
  player can't brute-force the key.
* **Compress the binary first** (gzip) before encoding as music.
  The output WAV is then ~2x smaller, and the player has to
  decompress after decoding.
* **Use 4 frequencies** (2 bits per tone) to make the WAV half as
  long. This is purely a quality-of-life improvement.

## Files

```
chall3/
  description              - the original challenge description
  README.md                - challenge overview and hints
  WRITEUP.md               - this file
  handout/
    music_to_my_ears.wav    - the music-encoded binary
  challenge/               - source for the reversing binary
    chall.c
    build_flag.py
    flag_data.h
    Makefile
    temporal_vault         - the binary (rebuild with `make`)
  src/
    bin2wav.py             - binary -> WAV encoder
    wav2bin.py             - WAV -> binary decoder
  solve.py                 - full automated solve
  test/                    - round-trip tests, scratch files
```
