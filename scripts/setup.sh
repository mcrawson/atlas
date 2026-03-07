#!/bin/bash
# ATLAS Setup Script
# Installs dependencies and configures the system

set -e

ATLAS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ATLAS_DIR"

echo "=========================================="
echo "  ATLAS Setup"
echo "=========================================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Create/update virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install core dependencies
echo ""
echo "Installing core dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Create directories
echo ""
echo "Creating directories..."
mkdir -p memory/{conversations,decisions,projects,briefings}
mkdir -p data
mkdir -p models/piper

# Install systemd service (optional)
read -p "Install systemd user service? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p ~/.config/systemd/user
    cp services/atlas.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    echo "Service installed. Enable with: systemctl --user enable atlas"
fi

# Voice dependencies (optional)
echo ""
read -p "Install voice dependencies (Whisper, Piper)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing voice dependencies (this may take a while)..."
    pip install --quiet openai-whisper sounddevice numpy

    # Try to install piper-tts
    if pip install --quiet piper-tts 2>/dev/null; then
        echo "Piper TTS installed successfully"
    else
        echo "Note: piper-tts requires additional setup. See https://github.com/rhasspy/piper"
    fi
fi

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "To start ATLAS:"
echo "  $ATLAS_DIR/scripts/atlas"
echo ""
echo "To enable the background daemon:"
echo "  systemctl --user enable --now atlas"
echo ""
echo "For Windows hotkey setup:"
echo "  1. Install AutoHotkey v2"
echo "  2. Run scripts/atlas-hotkey.ahk"
echo ""
