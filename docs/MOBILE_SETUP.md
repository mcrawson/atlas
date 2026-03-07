# ATLAS Mobile Setup Guide

Access ATLAS from your phone as a native-like app using Tailscale VPN and PWA.

---

## Prerequisites

- ATLAS server running on your desktop
- Tailscale installed on desktop and phone
- Same Tailscale account on both devices

---

## Server Details

| Setting | Value |
|---------|-------|
| **Tailscale IP** | `100.106.60.5` |
| **Port** | `8080` |
| **Full URL** | `http://100.106.60.5:8080` |
| **Desktop Name** | `desktop-3cq6qb8` |

---

## Step 1: Start ATLAS Server

On your desktop, run:

```bash
cd ~/ai-workspace/atlas
source .venv/bin/activate
./scripts/atlas-web --no-browser
```

The server will start on `http://0.0.0.0:8080`

---

## Step 2: Install Tailscale on Phone

### iPhone
1. Open **App Store**
2. Search for "Tailscale"
3. Install the app

### Android
1. Open **Play Store**
2. Search for "Tailscale"
3. Install the app

---

## Step 3: Connect Phone to Tailscale

1. Open the Tailscale app
2. Sign in with your Google account: `mikecrawson791@gmail.com`
3. Toggle **Connected** to ON
4. Your phone is now on the same private network as your desktop

---

## Step 4: Access ATLAS

1. Open your phone's browser:
   - **iPhone**: Use Safari
   - **Android**: Use Chrome

2. Go to: `http://100.106.60.5:8080`

3. You should see the ATLAS dashboard

---

## Step 5: Install as App (PWA)

### iPhone (Safari)

1. Tap the **Share** button (square with arrow pointing up)
2. Scroll down the share sheet
3. Tap **"Add to Home Screen"**
4. (Optional) Edit the name to "ATLAS"
5. Tap **"Add"**

### Android (Chrome)

1. Tap the **menu** button (⋮ three dots)
2. Tap **"Add to Home screen"** or **"Install app"**
3. (Optional) Edit the name to "ATLAS"
4. Tap **"Add"**

---

## Using the App

After installation:

- ATLAS appears on your home screen with a green "A" icon
- Opens in standalone mode (no browser chrome)
- Works offline for viewing cached projects
- Receives push notifications (future feature)

---

## Troubleshooting

### Can't connect to ATLAS

1. **Check Tailscale is connected** on both devices
   ```bash
   tailscale status
   ```

2. **Verify server is running**
   ```bash
   curl http://localhost:8080
   ```

3. **Check firewall** isn't blocking port 8080

### App not installing

- **iPhone**: Must use Safari (Chrome doesn't support PWA install on iOS)
- **Android**: Make sure you're using Chrome or Edge
- Clear browser cache and try again

### Slow connection

- Tailscale uses direct connections when possible
- If going through relay, connection may be slower
- Check `tailscale status` for "direct" vs "relay"

---

## Network Diagram

```
┌─────────────────┐         ┌─────────────────┐
│   Your Phone    │         │    Desktop      │
│                 │         │                 │
│  Tailscale IP:  │◄───────►│  Tailscale IP:  │
│  100.83.60.xx   │  VPN    │  100.106.60.5   │
│                 │ Tunnel  │                 │
│  ATLAS PWA App  │         │  ATLAS Server   │
│                 │         │  Port 8080      │
└─────────────────┘         └─────────────────┘
```

---

## Quick Reference

| Action | Command/URL |
|--------|-------------|
| Start server | `./scripts/atlas-web --no-browser` |
| Access from phone | `http://100.106.60.5:8080` |
| Check Tailscale | `tailscale status` |
| View server logs | `tail -f /tmp/atlas.log` |

---

## PWA Features

- **Offline Support**: View cached projects without internet
- **Home Screen Icon**: Green "A" ATLAS logo
- **Standalone Mode**: No browser UI, feels like native app
- **Push Notifications**: Ready for future agent updates
- **App Shortcuts**: Quick access to New Project, All Projects

---

*Last updated: February 2025*
