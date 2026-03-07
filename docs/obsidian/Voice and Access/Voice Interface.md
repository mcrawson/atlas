---
title: Voice Interface
description: Whisper STT and Piper TTS setup
tags:
  - voice
  - whisper
  - piper
  - tts
  - stt
created: 2024-02-10
---

# Voice Interface

Speak to ATLAS and hear responses with a British voice.

---

## Components

| Component | Purpose | Type |
|-----------|---------|------|
| Whisper | Speech-to-Text | OpenAI model |
| Piper | Text-to-Speech | Local TTS |

---

## Installation

### Install Dependencies

```bash
pip install openai-whisper piper-tts sounddevice numpy
```

### Download British Voice

```bash
mkdir -p ~/ai-workspace/atlas/models/piper

# Download from Piper releases
# Get: en_GB-alan-medium.onnx
# Place in: models/piper/
```

> [!info] Voice Options
> Piper offers multiple British voices. `en_GB-alan-medium` provides a refined butler-like voice.

---

## WSL2 Audio Setup

Voice requires audio passthrough from WSL2 to Windows.

### Option 1: WSLg (Windows 11)

WSLg provides automatic audio support:

```bash
# Check if WSLg is available
ls /mnt/wslg/

# If directory exists, audio should work automatically
```

### Option 2: PulseAudio Bridge

For Windows 10 or manual setup:

**On Windows:**
1. Install PulseAudio for Windows
2. Configure `default.pa` for network access

**In WSL2:**
```bash
export PULSE_SERVER=tcp:$(hostname).local:4713
```

---

## Enable Voice Mode

### Configuration

```yaml
# config/atlas.yaml
voice:
  enabled: true
  whisper_model: "base.en"
  piper_voice: "en_GB-alan-medium"
```

### Whisper Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny.en | 39 MB | Fast | Good |
| base.en | 74 MB | Medium | Better |
| small.en | 244 MB | Slower | Best |

> [!tip] Recommended
> `base.en` offers the best balance of speed and accuracy.

---

## Using Voice Mode

### Start Voice Mode

```bash
./scripts/atlas voice
```

Or from within ATLAS:
```
You: /voice

[ATLAS] Voice mode activated, sir. Speak when ready.
```

### Push-to-Talk

- **Hold Space** to speak
- **Release** to process
- ATLAS responds with voice

### Voice Commands

Speak naturally:
- "What's on my calendar today?"
- "Turn on the office lights"
- "Write a function to sort a list"

---

## Voice Feedback

ATLAS speaks responses using Piper:

```
You: (spoken) "What time is it?"

[ATLAS] (spoken) "It's half past two in the afternoon, sir."
```

Long responses are truncated for voice but shown in full on screen.

---

## Configuration Options

```yaml
voice:
  enabled: true
  whisper_model: "base.en"
  piper_voice: "en_GB-alan-medium"

  # Advanced options
  silence_threshold: 0.03    # Mic sensitivity
  max_record_seconds: 30     # Max recording length
  speak_responses: true      # TTS for responses
```

---

## Troubleshooting

> [!warning] No Audio Input
> Check microphone permissions:
> ```bash
> arecord -l  # List recording devices
> ```

> [!warning] No Audio Output
> Test speakers:
> ```bash
> speaker-test -t wav
> ```

> [!tip] Test Whisper
> ```python
> import whisper
> model = whisper.load_model("base.en")
> result = model.transcribe("test.wav")
> print(result["text"])
> ```

---

## See Also

- [[Installation]] - Initial setup
- [[Configuration]] - Voice settings
- [[Hotkey Activation]] - Quick access

---

#voice #whisper #piper #tts #stt
