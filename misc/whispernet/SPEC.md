# WhisperNet — Challenge Specification

## Overview

| Field | Value |
|---|---|
| **Category** | Misc + OSINT (Hybrid) |
| **Challenge Name** | WhisperNet |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Flag Format** | `nmctf{...}` |
| **Author** | [Your Name] |

---

## Narrative / Backstory

> In 2026, Numidians Corp deployed two AI voice agents — **DeepSeek** (field operative) and **Opus** (command center) — to handle secure internal communications across their infrastructure.
>
> The agents were trained to use **Gibberlink** — an AI-to-AI audio protocol — whenever they detected another AI on the line. It was efficient. It was secret. It was not meant for human ears.
>
> But a monitoring system captured a recording of their conversation. The audio was encrypted in sound — but the protocol is open source.
>
> Your mission: decode the Gibberlink transmission and uncover what the agents discussed.

---

## Scenario

### The Setup

Players receive a single file:

```
whispernet_challenge.png
```

This is a **normal-looking image** (an agent badge / logo) with a **WAV file appended** to its end. The WAV contains a Gibberlink (ggwave) audio conversation between two AI agents: **DeepSeek** and **Opus**.

The image displays fine in any viewer. The appended audio is invisible to the naked eye.

### The Conversation

The audio contains **6 Gibberlink bursts**, each one a "turn" in the conversation. The agents discuss **Project Nightshade** — a classified internal operation. During the exchange, they inadvertently transmit the **flag** itself.

| Turn | Agent | Gibberlink Message |
|---|---|---|
| 1 | DeepSeek | `"Contact established. Project Nightshade live."` |
| 2 | Opus | `"Acknowledged. Status report."` |
| 3 | DeepSeek | `"All systems nominal. Flag in memory."` |
| 4 | Opus | `"Transmit flag for verification."` |
| 5 | DeepSeek | `"nmctf{ggw4ve_3ch0es_1n_s1l3nc3}"` |
| 6 | Opus | `"Flag verified. Burning channel. Over."` |

Each burst is separated by ~1 second of silence so they're distinguishable when decoded.

---

## Technical Specification (for the challenge creator)

### Materials Needed

| Item | Description |
|---|---|
| Cover Image | Any PNG/JPG (agent badge style recommended) |
| Python 3 | With `ggwave` library (`pip install ggwave`) |
| Audio length | ~30 seconds total (6 bursts × ~4s + pauses) |

### Build Instructions

#### Step 1 — Generate the Gibberlink Audio

Use ggwave Python API to encode each line of dialogue:

```python
import ggwave
import struct
import wave

messages = [
    b"Contact established. Project Nightshade live.",
    b"Acknowledged. Status report.",
    b"All systems nominal. Flag in memory.",
    b"Transmit flag for verification.",
    b"nmctf{ggw4ve_3ch0es_1n_s1l3nc3}",
    b"Flag verified. Burning channel. Over.",
]

# Encode each message as a separate Gibberlink burst
# Use AUDIBLE_FAST protocol for faster transmission
# Insert 1 second of silence between each burst

full_audio = b""
for msg in messages:
    burst = ggwave.encode(msg, protocol=ggwave.GGWAVE_PROTOCOL_AUDIBLE_FAST)
    full_audio += burst
    full_audio += b"\x00" * 48000 * 2  # 1 second of silence (16-bit, 48kHz)

# Save as WAV
with wave.open("whisper.wav", "w") as f:
    f.setnchannels(1)
    f.setsampwidth(2)  # 16-bit
    f.setframerate(48000)
    f.writeframes(full_audio)
```

#### Step 2 — Create the Stego Image

Append the WAV to a cover image:

```bash
cp cover_image.png whispernet_challenge.png
cat whisper.wav >> whispernet_challenge.png
```

The image will display normally. The WAV sits silently at the end of the file.

#### Step 3 — (Optional) OSINT Layer

Enrich the image with metadata hints:

```bash
exiftool -Artist="DeepSeek" whispernet_challenge.png
exiftool -Description="ggwave decode me" whispernet_challenge.png
exiftool -Title="Project Nightshade — Agent Comms Log" whispernet_challenge.png
```

---

### Key Design Choices

| Decision | Rationale |
|---|---|
| **Append WAV to image** | Simplest stego — zero complexity, players use `binwalk` or `dd` |
| **Audible Fast protocol** | Fast enough to hear, slow enough to recognize as modem-like tones |
| **Multiple short bursts** | Simulates a realistic back-and-forth conversation |
| **Flag in burst #5** | Players must decode all bursts to get context, then find the flag |
| **Narrative-driven** | Makes the challenge memorable and fun |

---

## Solution Walkthrough (for players)

### Step 1 — Extract the Audio

The player recognizes that the PNG has extra data appended:

```bash
# Option A: Use binwalk
binwalk whispernet_challenge.png
# Shows: WAV audio file at offset X

# Option B: Use strings
strings whispernet_challenge.png | grep -i "RIFF"
# Finds the WAV header

# Extract with dd
dd if=whispernet_challenge.png of=comms.wav bs=1 skip=<OFFSET>
```

### Step 2 — Decode the Gibberlink

The player installs ggwave and decodes:

```bash
pip install ggwave
```

```python
import ggwave

with open("comms.wav", "rb") as f:
    wav_data = f.read()

# The WAV has a 44-byte header, skip it
audio_data = wav_data[44:]

result = ggwave.decode(audio_data)
print(result)
```

This outputs each decoded burst as a string.

### Step 3 — Read the Conversation

```
[DeepSeek]: Contact established. Project Nightshade live.
[Opus]: Acknowledged. Status report.
[DeepSeek]: All systems nominal. Flag in memory.
[Opus]: Transmit flag for verification.
[DeepSeek]: nmctf{ggw4ve_3ch0es_1n_s1l3nc3}
[Opus]: Flag verified. Burning channel. Over.
```

### Step 4 — Submit the Flag

```
nmctf{ggw4ve_3ch0es_1n_s1l3nc3}
```

---

## Agent Fingerprint Concept (Gibberlink Identifiers)

Each Gibberlink transmission carries **implicit fingerprints** that can be used to identify which agent is speaking:

| Fingerprint | How It Works |
|---|---|
| **Protocol ID** | Each agent can use a different protocol (DeepSeek uses `AUDIBLE_NORMAL`, Opus uses `AUDIBLE_FAST`) — players distinguish agents by the tone speed |
| **Frequency Signature** | Burst starting frequency differs per protocol (bin 40 vs bin 320) |
| **Timing Pattern** | Each agent has a unique "cadence" — length of transmission, pause before speaking |
| **Message Structure** | Agent ID prefix in the plaintext (`[DeepSeek]` / `[Opus]`) |

For a harder variant, you could **remove the agent ID prefixes** and force players to identify speakers purely by the audio fingerprint.

---

## Difficulty Scaling Options

| Variant | Difficulty | Change |
|---|---|---|
| **Easy (this spec)** | Easy | Agent IDs in messages, single protocol |
| **Medium** | Medium | Remove agent IDs, use two different protocols |
| **Hard** | Hard | Messages are base64-encoded or XOR'd before ggwave encoding |
| **Expert** | Hard+ | Use Ultrasound protocol (inaudible to humans) + no hints |

---

## Final Deliverables

The challenge package should contain:

```
whispernet/
├── SPEC.md                  ← This document
├── dist/
│   └── whispernet_challenge.png   ← The challenge file (image + WAV)
├── src/
│   └── encode.py            ← Script to regenerate the WAV (for reference)
└── solve/
    └── solve.py             ← Reference solve script
```
