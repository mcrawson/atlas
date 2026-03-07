---
title: Troubleshooting
description: Common issues and solutions
tags:
  - troubleshooting
  - help
  - errors
created: 2024-02-10
---

# Troubleshooting

Common issues and how to fix them.

---

## Startup Issues

### ATLAS Won't Start

**Symptom:** Error when running `./scripts/atlas`

**Check virtual environment:**
```bash
cd ~/ai-workspace/atlas
source .venv/bin/activate
python --version  # Should be 3.12+
```

**Check dependencies:**
```bash
pip install -r requirements.txt
```

**Check config file:**
```bash
python -c "import yaml; yaml.safe_load(open('config/atlas.yaml'))"
```

---

### Module Not Found

**Symptom:** `ModuleNotFoundError: No module named 'atlas'`

**Fix:** Ensure you're in the correct directory and venv is active:
```bash
cd ~/ai-workspace/atlas
source .venv/bin/activate
```

---

## Provider Issues

### OpenAI API Error

**Symptom:** `openai.AuthenticationError`

**Fix:** Check API key:
```bash
echo $OPENAI_API_KEY  # Should show your key
export OPENAI_API_KEY="sk-..."
```

---

### Gemini API Error

**Symptom:** `google.api_core.exceptions.PermissionDenied`

**Fix:** Check API key:
```bash
# From environment
echo $GEMINI_API_KEY

# Or from file
cat ~/.gemini/api_key
```

---

### Ollama Not Responding

**Symptom:** `Connection refused to localhost:11434`

**Fix:** Start Ollama:
```bash
ollama serve
```

**Check status:**
```bash
curl http://localhost:11434/api/tags
```

**Run in background:**
```bash
nohup ollama serve > /dev/null 2>&1 &
```

---

### All Providers Failing

**Symptom:** Every query fails

**Check network:**
```bash
curl https://api.openai.com  # Should connect
```

**Check quotas:**
```
/status
```

If quotas exceeded, wait until tomorrow or use Ollama.

---

## Daemon Issues

### Daemon Won't Start

**Symptom:** `systemctl --user start atlas` fails

**Check logs:**
```bash
journalctl --user -u atlas -n 50
```

**Verify service file:**
```bash
cat ~/.config/systemd/user/atlas.service
```

**Reload systemd:**
```bash
systemctl --user daemon-reload
```

---

### Background Tasks Not Processing

**Symptom:** Tasks stay in "pending" state

**Check daemon is running:**
```bash
systemctl --user status atlas
```

**Check task queue:**
```bash
sqlite3 ~/ai-workspace/atlas/data/tasks.db "SELECT * FROM tasks"
```

---

## Voice Issues

### No Microphone Input

**Symptom:** Voice mode doesn't hear anything

**List audio devices:**
```bash
arecord -l
```

**Test recording:**
```bash
arecord -d 5 test.wav && aplay test.wav
```

**WSL2:** Ensure WSLg or PulseAudio bridge is configured.

---

### No Audio Output

**Symptom:** ATLAS doesn't speak

**Test speakers:**
```bash
speaker-test -t wav
```

**Check Piper installation:**
```bash
pip show piper-tts
```

---

### Whisper Model Not Found

**Symptom:** `RuntimeError: Model not found`

**Download model:**
```python
import whisper
whisper.load_model("base.en")  # Downloads if missing
```

---

## Integration Issues

### Home Assistant Connection Failed

**Symptom:** `aiohttp.ClientConnectorError`

**Check connectivity:**
```bash
curl -H "Authorization: Bearer $HA_TOKEN" \
     http://homeassistant.local:8123/api/
```

**Check token:**
```bash
echo $HA_TOKEN
```

---

### Google OAuth Failed

**Symptom:** OAuth flow doesn't complete

**Check credentials file:**
```bash
cat ~/.config/atlas/google_credentials.json | python -m json.tool
```

**Clear tokens and retry:**
```bash
rm ~/.config/atlas/google_tokens.json
./scripts/atlas setup-google
```

---

### Calendar Shows No Events

**Symptom:** Empty calendar despite having events

**Check API enabled:**
1. Google Cloud Console
2. APIs & Services → Enabled APIs
3. Verify "Google Calendar API" is listed

**Check scopes:**
```yaml
scopes:
  - calendar.readonly
```

---

## Notification Issues

### Windows Toast Not Working

**Symptom:** No Windows notifications from WSL2

**Test PowerShell:**
```bash
powershell.exe -Command "Write-Host 'Test'"
```

**Check execution policy:**
```powershell
# In PowerShell
Get-ExecutionPolicy
# If restricted:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Memory Issues

### Conversations Not Saving

**Symptom:** Previous conversations lost

**Check memory directory:**
```bash
ls -la ~/ai-workspace/atlas/memory/conversations/
```

**Check permissions:**
```bash
chmod 755 ~/ai-workspace/atlas/memory
```

---

### Patterns Not Learning

**Symptom:** No patterns after extended use

**Check learning enabled:**
```yaml
anticipation:
  learning: true
```

**View pattern file:**
```bash
cat ~/.config/atlas/patterns.yaml
```

---

## Performance Issues

### Slow Responses

**Possible causes:**
1. Network latency to API providers
2. Large Whisper model (switch to `tiny.en`)
3. Ollama model too large

**Try faster Ollama model:**
```yaml
ollama:
  models:
    fast: "llama3.2:3b"
```

---

### High Memory Usage

**Check which model is loaded:**
```bash
ollama ps
```

**Unload unused models:**
```bash
ollama stop llama3
```

---

## Debug Mode

Enable verbose logging:

```
/debug on
```

Or in config:
```yaml
atlas:
  debug: true
```

View logs:
```bash
tail -f ~/ai-workspace/atlas/data/atlas.log
```

---

## Getting Help

If issues persist:

1. Check logs: `journalctl --user -u atlas`
2. Enable debug: `/debug on`
3. Verify config: Review [[Configuration Reference]]
4. Check GitHub issues

---

#troubleshooting #help #errors
