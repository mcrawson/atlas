---
title: Installation
description: How to install and set up ATLAS
tags:
  - setup
  - installation
  - getting-started
created: 2024-02-10
---

# Installation

Get ATLAS running on your system.

> [!info] Prerequisites
> - Python 3.12+
> - WSL2 (for Windows users)
> - Git

---

## Step 1: Clone and Setup

```bash
cd ~/ai-workspace
git clone <your-atlas-repo> atlas
cd atlas

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure API Keys

ATLAS uses multiple AI providers. Configure the ones you have:

### OpenAI (GPT)
```bash
export OPENAI_API_KEY="sk-..."
```

### Google Gemini
```bash
export GEMINI_API_KEY="..."

# Or save to file:
mkdir -p ~/.gemini
echo "your-key" > ~/.gemini/api_key
```

### Anthropic Claude
> [!note] Claude Authentication
> If using Claude Code, no additional setup needed - uses existing authentication.

---

## Step 3: Configure Ollama (Local Models)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended models
ollama pull llama3
ollama pull codellama:13b

# Start Ollama service
ollama serve
```

> [!tip] Background Ollama
> Run Ollama in background:
> ```bash
> nohup ollama serve > /dev/null 2>&1 &
> ```

---

## Step 4: Verify Installation

```bash
./scripts/atlas
```

You should see:
```
[ATLAS] Good morning, sir. How may I be of service?
```

---

## Optional: Voice Setup

See [[Voice Interface]] for Whisper and Piper installation.

---

## Optional: Daemon Setup

See [[Background Tasks#Daemon Installation]] for systemd service setup.

---

## Next Steps

- [[Quick Start]] - Your first conversation
- [[Configuration]] - Customize settings

---

#installation #setup #getting-started
