#!/usr/bin/env python3
# wav2bin.py - Decode a music file (WAV) back to the original binary.
#
# Strategy:
#   1. Read the WAV samples.
#   2. Slice the audio into windows of TONE_MS ms each. One bit per window.
#   3. For each window, compute the energy at f0 and f1 using a Goertzel-like
#      single-frequency DFT. The bit is 1 if f1 has more energy, else 0.
#   4. Find the 16-bit preamble, then read the 32-bit length, then the data bits.
#
# Usage: wav2bin.py <input.wav> <output_file>

import sys
import wave
import struct
import math

SAMPLE_RATE = 44100
F0 = 440.0
F1 = 880.0
TONE_MS = 2
PREAMBLE = b"\xAA\x55"  # 10101010 01010101
PREAMBLE_BITS = "1010101001010101"

def goertzel(samples, target_freq, sample_rate):
    """Goertzel algorithm: magnitude of the DFT at target_freq."""
    N = len(samples)
    k = int(0.5 + N * target_freq / sample_rate)
    w = 2.0 * math.pi * k / N
    coeff = 2.0 * math.cos(w)
    s0 = s1 = s2 = 0.0
    for x in samples:
        s0 = x + coeff * s1 - s2
        s2 = s1
        s1 = s0
    return math.sqrt(s1 * s1 + s2 * s2 - coeff * s1 * s2)

def decode_bits(samples):
    """Decode the bit stream from raw samples (one bit per TONE_MS window)."""
    tone_n = int(SAMPLE_RATE * TONE_MS / 1000)
    n_samples = len(samples)
    n_bits = n_samples // tone_n

    bits = []
    for i in range(n_bits):
        window = samples[i * tone_n : (i + 1) * tone_n]
        e0 = goertzel(window, F0, SAMPLE_RATE)
        e1 = goertzel(window, F1, SAMPLE_RATE)
        bits.append(1 if e1 > e0 else 0)
    return bits

def find_preamble(bits):
    """Find the start of the data: look for the 16-bit preamble pattern."""
    target = PREAMBLE_BITS
    s = "".join(str(b) for b in bits)
    idx = s.find(target)
    return idx

def bits_to_bytes(bits):
    """Convert a list of bits (MSB first) to bytes."""
    out = bytearray()
    n = (len(bits) // 8) * 8
    for i in range(0, n, 8):
        b = 0
        for k in range(8):
            b = (b << 1) | bits[i + k]
        out.append(b)
    return bytes(out)

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.wav> <output_file>", file=sys.stderr)
        sys.exit(1)

    in_wav = sys.argv[1]
    out_file = sys.argv[2]

    with wave.open(in_wav, "rb") as w:
        nchan = w.getnchannels()
        sw = w.getsampwidth()
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        print(f"Expected 16-bit WAV, got sampwidth={sw}", file=sys.stderr)
        sys.exit(2)
    if sr != SAMPLE_RATE:
        print(f"Expected sample rate {SAMPLE_RATE}, got {sr}", file=sys.stderr)
        sys.exit(2)
    if nchan != 1:
        samples = struct.unpack(f"<{n*nchan}h", raw)
        mono = []
        for i in range(n):
            s = 0
            for c in range(nchan):
                s += samples[i*nchan + c]
            mono.append(s // nchan)
        samples = mono
    else:
        samples = list(struct.unpack(f"<{n}h", raw))

    print(f"Read {n} samples ({n / SAMPLE_RATE:.2f} s, {nchan} ch, {sw}B, {sr} Hz)")

    bits = decode_bits(samples)
    print(f"Decoded {len(bits)} raw bits")

    pre_idx = find_preamble(bits)
    if pre_idx < 0:
        print("Preamble not found!", file=sys.stderr)
        sys.exit(3)
    print(f"Preamble at bit {pre_idx}")

    data_start = pre_idx + 16
    if data_start + 32 > len(bits):
        print("Truncated length", file=sys.stderr)
        sys.exit(3)
    n_data_bits = 0
    for k in range(32):
        n_data_bits = (n_data_bits << 1) | bits[data_start + k]
    print(f"Payload: {n_data_bits} bits = {n_data_bits // 8} bytes")

    payload_start = data_start + 32
    payload_end = payload_start + n_data_bits
    if payload_end > len(bits):
        print(f"Truncated payload (have {len(bits) - payload_start} bits, need {n_data_bits})", file=sys.stderr)
        sys.exit(3)
    payload = bits_to_bytes(bits[payload_start:payload_end])

    with open(out_file, "wb") as f:
        f.write(payload)
    print(f"Decoded {len(payload)} bytes to {out_file}")

if __name__ == "__main__":
    main()
