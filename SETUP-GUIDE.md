# ATLAS Platform Setup Guide

Complete step-by-step instructions for configuring all ATLAS integrations.

---

## Status Overview

| Platform | Status | Priority | Cost |
|----------|--------|----------|------|
| GitHub | Configured | - | Free |
| OpenAI | Not configured | High | Pay per use |
| Anthropic | Not configured | High | Pay per use |
| Gemini | Not configured | Medium | Free tier available |
| Slack | Not configured | Low | Free |
| Canva | Not configured | Medium | Free tier |
| Figma | Not configured | Low | Free tier |
| Google Docs | Not configured | Medium | Free |
| Vercel | Not configured | Medium | Free tier |
| npm | Not configured | Low | Free |
| PyPI | Not configured | Low | Free |
| App Store | Not configured | Low | $99/year |
| Play Store | Not configured | Low | $25 one-time |

---

## Priority 1: AI Providers

### OpenAI
**What it enables:** GPT-4 for code generation, analysis, and complex tasks

**Steps:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Name it "ATLAS"
4. Copy the key (starts with `sk-`)
5. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

**Cost:** ~$0.01-0.03 per 1K tokens (GPT-4)

---

### Anthropic (Claude)
**What it enables:** Claude for nuanced reasoning and long-context tasks

**Steps:**
1. Go to https://console.anthropic.com/
2. Navigate to API Keys
3. Click "Create Key"
4. Copy the key (starts with `sk-ant-`)
5. Add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

**Cost:** ~$0.015 per 1K tokens (Claude 3.5 Sonnet)

---

### Google Gemini
**What it enables:** Gemini for multimodal tasks and free tier usage

**Steps:**
1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Select or create a Google Cloud project
4. Copy the key
5. Add to `.env`:
   ```
   GEMINI_API_KEY=your-key-here
   ```

**Cost:** Free tier: 60 requests/minute, then pay per use

---

## Priority 2: Design & Documents

### Canva
**What it enables:** Auto-generate app icons, book covers, social graphics

**Steps:**
1. Go to https://www.canva.com/developers/
2. Create a developer account (or sign in)
3. Create a new app in the Developer Portal
4. Go to app settings and copy the API key
5. Add to `.env`:
   ```
   CANVA_API_KEY=your-key-here
   ```

**Cost:** Free tier available, Pro for advanced features

---

### Figma
**What it enables:** UI design exports, design system integration

**Steps:**
1. Go to https://www.figma.com/developers/api
2. Click "Get a personal access token"
3. Name it "ATLAS"
4. Copy the token (starts with `figd_`)
5. Add to `.env`:
   ```
   FIGMA_API_TOKEN=figd_your-token-here
   ```

**Cost:** Free

---

### Google Docs
**What it enables:** Create formatted documents, books, manuscripts

**Steps:**
1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable "Google Docs API" and "Google Drive API"
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Download the credentials JSON file
6. Save it to your ATLAS directory (e.g., `config/google-credentials.json`)
7. Run the OAuth flow to get an access token:
   ```bash
   ./scripts/atlas-auth google
   ```
8. Add to `.env`:
   ```
   GOOGLE_CREDENTIALS_PATH=/home/mcrawson/ai-workspace/atlas/config/google-credentials.json
   GOOGLE_ACCESS_TOKEN=ya29.your-token-here
   ```

**Cost:** Free

**Note:** Access tokens expire. May need to implement refresh token flow.

---

## Priority 3: Deployment

### Vercel
**What it enables:** One-click web app deployment

**Steps:**
1. Go to https://vercel.com/account/tokens
2. Click "Create Token"
3. Name it "ATLAS"
4. Copy the token
5. Add to `.env`:
   ```
   VERCEL_TOKEN=your-token-here
   ```

**Cost:** Free tier: 100 deployments/day

---

## Priority 4: Package Registries

### npm
**What it enables:** Publish JavaScript/TypeScript packages

**Steps:**
1. Go to https://www.npmjs.com/settings/~/tokens
2. Click "Generate New Token" → "Classic Token"
3. Select "Automation" type
4. Copy the token (starts with `npm_`)
5. Add to `.env`:
   ```
   NPM_TOKEN=npm_your-token-here
   ```

**Cost:** Free

---

### PyPI
**What it enables:** Publish Python packages

**Steps:**
1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Name it "ATLAS"
4. Scope: "Entire account" (or specific project)
5. Copy the token (starts with `pypi-`)
6. Add to `.env`:
   ```
   PYPI_TOKEN=pypi-your-token-here
   ```

**Cost:** Free

**Tip:** Use TestPyPI first: https://test.pypi.org/manage/account/token/

---

## Priority 5: Communication

### Slack
**What it enables:** Notifications, two-way chat with ATLAS

**Steps:**
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name it "ATLAS", select your workspace
4. Go to "OAuth & Permissions"
5. Add Bot Token Scopes:
   - `chat:write`
   - `channels:history`
   - `channels:read`
   - `app_mentions:read`
6. Install to workspace
7. Copy "Bot User OAuth Token" (starts with `xoxb-`)
8. Go to "Basic Information" → copy "Signing Secret"
9. Add to `.env`:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token-here
   SLACK_SIGNING_SECRET=your-secret-here
   ```

**Cost:** Free

---

## Priority 6: App Stores (When Ready to Publish)

### Apple App Store
**What it enables:** Publish iOS apps

**Prerequisites:**
- Apple Developer Program membership ($99/year)
- macOS for building (or use cloud build service)

**Steps:**
1. Go to https://appstoreconnect.apple.com/access/api
2. Click "Generate API Key"
3. Name: "ATLAS", Access: "App Manager"
4. Download the .p8 key file
5. Note the Key ID and Issuer ID
6. Save .p8 file to `config/AuthKey_XXXX.p8`
7. Add to `.env`:
   ```
   APP_STORE_ISSUER_ID=your-issuer-id
   APP_STORE_KEY_ID=your-key-id
   APP_STORE_PRIVATE_KEY_PATH=/home/mcrawson/ai-workspace/atlas/config/AuthKey_XXXX.p8
   ```

**Cost:** $99/year

---

### Google Play Store
**What it enables:** Publish Android apps

**Prerequisites:**
- Google Play Developer account ($25 one-time)

**Steps:**
1. Go to https://play.google.com/console/developers
2. Setup → API access → Create service account
3. Download the service account JSON file
4. Grant "Release manager" permissions to the service account
5. Save JSON to `config/play-store-service-account.json`
6. Add to `.env`:
   ```
   GOOGLE_PLAY_SERVICE_ACCOUNT=/home/mcrawson/ai-workspace/atlas/config/play-store-service-account.json
   ANDROID_PACKAGE_NAME=com.yourcompany.yourapp
   ```

**Cost:** $25 one-time

---

## Quick Setup Order

For fastest time to value:

1. **AI Providers** (at least one) - Core functionality
2. **Vercel** - Deploy web projects immediately
3. **Canva** - Generate visual assets
4. **Google Docs** - Create documents/books
5. **npm/PyPI** - Publish libraries
6. **Slack** - Get notifications
7. **App Stores** - When you have an app ready

---

## After Configuration

Restart ATLAS to pick up new env vars:

```bash
cd ~/ai-workspace/atlas
source .venv/bin/activate
./scripts/atlas-web
```

Check setup page: http://localhost:8080/setup
