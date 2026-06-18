#!/usr/bin/env python3
"""
WhisperNet — Gibberlink Audio Generator
Generates a multi-burst GGWave-encoded WAV file simulating
a conversation between two AI agents.
"""

import ggwave
import wave

# ── The Conversation (6 bursts) ──────────────────────────────
messages = [
    b"Contact established. Project Nightshade live.",
    b"Acknowledged. Status report.",
    b"All systems nominal. Flag in memory.",
    b"Transmit flag for verification.",
    b"nmctf{ggw4ve_3ch0es_1n_s1l3nc3}",
    b"Flag verified. Burning channel. Over.",
]

# ── Audio Parameters ─────────────────────────────────────────
PROTOCOL     = 1         # GGWAVE_PROTOCOL_AUDIBLE_FAST
VOLUME       = 20
SAMPLE_RATE  = 48000
SILENCE_SEC  = 2          # seconds of silence between bursts

# ── Encode ───────────────────────────────────────────────────
full_audio = b""
for i, msg in enumerate(messages):
    print(f"[{i+1}/{len(messages)}] Encoding: {msg.decode()}")
    waveform = ggwave.encode(msg, protocolId=PROTOCOL, volume=VOLUME)
    full_audio += waveform
    # Add clean silence gap
    gap = b"\x00" * (SAMPLE_RATE * 2 * SILENCE_SEC)
    full_audio += gap

# ── Save WAV ─────────────────────────────────────────────────
OUTPUT = "whisper.wav"
with wave.open(OUTPUT, "w") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(SAMPLE_RATE)
    f.writeframes(full_audio)

duration = len(full_audio) / (SAMPLE_RATE * 2)
print(f"\n✅ WAV saved: {OUTPUT}")
print(f"   Duration: {duration:.1f}s")
print(f"   Size: {len(full_audio)} bytes")
