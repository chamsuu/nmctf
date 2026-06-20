#!/usr/bin/env python3
# bin2wav.py - Encode a binary file as a music file (WAV).
#
# Encoding scheme (1 bit per tone):
#   - bit 0 -> 440 Hz (A4)
#   - bit 1 -> 880 Hz (A5)
#   - 2 ms tone, 0 ms gap (tones are back-to-back)
#   - 16-bit PCM mono, 44100 Hz
#   - 16-bit preamble (alternating 0/1) for sync, then 32-bit length
#     (in bits, big-endian), then the file bits.
#
# This is the same scheme as the binary-music-maker reference site
# (https://binarycodeconverter.com/binary-music-maker/) in "Sequential" mode
# with two distinct pitches, but at a much higher bit rate so whole binaries
# fit in a few minutes of audio.
#
# Usage: bin2wav.py <input_file> <output.wav>

import sys
import wave
import struct
import numpy as np

SAMPLE_RATE = 44100
F0 = 440.0   # bit 0 (A4)
F1 = 880.0   # bit 1 (A5)
TONE_MS = 2  # 88 samples per bit
AMPLITUDE = 0.6
PREAMBLE = b"\xAA\x55"  # 10101010 01010101

def synth_tones(bits):
    """Generate audio samples for a list of bits using vectorized numpy."""
    tone_n = int(SAMPLE_RATE * TONE_MS / 1000)
    t = np.arange(tone_n) / SAMPLE_RATE
    freqs = np.where(np.array(bits) == 1, F1, F0).astype(np.float64)
    waves = np.sin(2 * np.pi * freqs[:, None] * t[None, :])
    # 0.5 ms attack/release to avoid clicks
    attack = max(1, int(SAMPLE_RATE * 0.0005))
    env = np.ones(tone_n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-attack:] = np.linspace(1, 0, attack)
    waves *= env[None, :]
    waves *= AMPLITUDE
    samples = (waves * 32767).astype(np.int16)
    return samples.flatten()

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_file> <output.wav>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        data = f.read()
    out_path = sys.argv[2]

    # Build bit stream: preamble (16 bits) + length (32 bits BE) + data
    bits = []
    for b in PREAMBLE:
        for k in range(7, -1, -1):
            bits.append((b >> k) & 1)
    n = len(data) * 8
    for k in range(31, -1, -1):
        bits.append((n >> k) & 1)
    for b in data:
        for k in range(7, -1, -1):
            bits.append((b >> k) & 1)

    samples = synth_tones(bits)

    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(samples.tobytes())

    total_bits = len(bits)
    print(f"Encoded {len(data)} bytes ({n} data bits + 16 preamble + 32 length = {total_bits} bits) into {out_path}")
    print(f"  Duration: {len(samples) / SAMPLE_RATE:.2f} s, {len(samples)} samples")

if __name__ == "__main__":
    main()
