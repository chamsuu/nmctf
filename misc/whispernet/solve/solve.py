#!/usr/bin/env python3
"""
WhisperNet — Solve Script
Extracts the Gibberlink audio from the challenge image
and decodes it using ggwave.
"""

import ggwave
import wave
import sys
import os

CHALLENGE_FILE = "whispernet_challenge.png"

def find_wav_offset(data: bytes) -> int:
    """Find the RIFF header offset in the appended data."""
    idx = data.find(b"RIFF")
    if idx == -1:
        raise ValueError("No WAV (RIFF) header found in the challenge file!")
    return idx

def extract_wav(data: bytes, output: str = "extracted.wav") -> str:
    """Extract WAV data from the challenge file."""
    offset = find_wav_offset(data)
    wav_data = data[offset:]

    with open(output, "wb") as f:
        f.write(wav_data)

    print(f"[+] WAV extracted at offset {offset} (0x{offset:x})")
    print(f"[+] Saved to: {output}")
    return output

def decode_wav(wav_file: str):
    """Decode all Gibberlink messages from the WAV file."""
    with wave.open(wav_file, "r") as f:
        frames = f.readframes(f.getnframes())
        sample_rate = f.getframerate()

    print(f"[+] WAV: {sample_rate} Hz, {len(frames)} frames")

    # Feed audio in chunks to decode all bursts
    instance = ggwave.init()
    ggwave.disableLog()

    chunk_size = 4096
    messages = []

    for i in range(0, len(frames), chunk_size):
        chunk = frames[i:i + chunk_size]
        if len(chunk) < 256:
            continue
        result = ggwave.decode(instance, chunk)
        if result:
            try:
                msg = result.decode("utf-8")
                messages.append(msg)
                print(f"  📡 Decoded: {msg}")
            except UnicodeDecodeError:
                print(f"  📡 Decoded (raw): {result.hex()}")

    ggwave.free(instance)
    return messages

def find_flag(messages: list) -> str:
    """Extract the flag from decoded messages."""
    import re
    for msg in messages:
        match = re.search(r'nmctf\{[^}]+\}', msg)
        if match:
            return match.group(0)
    return None

def main():
    if not os.path.exists(CHALLENGE_FILE):
        print(f"[-] {CHALLENGE_FILE} not found!")
        print(f"    Place it in the current directory or provide path.")
        sys.exit(1)

    print(f"[*] Loading: {CHALLENGE_FILE}")

    with open(CHALLENGE_FILE, "rb") as f:
        data = f.read()

    # Step 1: Extract WAV
    wav_file = extract_wav(data)

    # Step 2: Decode Gibberlink
    messages = decode_wav(wav_file)

    # Step 3: Find the flag
    flag = find_flag(messages)
    if flag:
        print(f"\n{'='*50}")
        print(f"🏁 FLAG: {flag}")
        print(f"{'='*50}")
    else:
        print("\n[-] No flag found in decoded messages.")
        print("    Here are all decoded messages:")
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. {msg}")

if __name__ == "__main__":
    main()
