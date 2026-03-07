---
title: Smart Home
description: Home Assistant integration
tags:
  - smart-home
  - home-assistant
  - automation
created: 2024-02-10
---

# Smart Home

Control your home with natural language through Home Assistant.

---

## Overview

ATLAS integrates with Home Assistant to:
- Control lights, thermostats, locks
- Query device states
- Execute scenes and automations
- Natural language commands

> "ATLAS, dim the office lights to 50%"
> "Very good, sir. Office lights dimmed."

---

## Requirements

- Home Assistant instance running
- Long-lived access token
- Network access from WSL2 to Home Assistant

---

## Setup

### 1. Get Access Token

1. Open Home Assistant
2. Go to Profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Create Token → Name it "ATLAS"
5. Copy the token

### 2. Configure ATLAS

```yaml
# config/atlas.yaml
integrations:
  home_assistant:
    enabled: true
    url: "http://homeassistant.local:8123"
    token_env: "HA_TOKEN"
    entities:
      office_lights: "light.office"
      bedroom_lights: "light.bedroom"
      living_room: "light.living_room"
      thermostat: "climate.main"
      front_door: "lock.front_door"
```

### 3. Set Environment Variable

```bash
export HA_TOKEN="your-long-lived-token"
```

Or add to `~/.bashrc`:
```bash
echo 'export HA_TOKEN="your-token"' >> ~/.bashrc
```

---

## Commands

### Lights

```
You: Turn on the office lights
[ATLAS] Very good, sir. Office lights are now on.

You: Dim the bedroom lights to 30%
[ATLAS] Bedroom lights dimmed to 30%, sir.

You: Turn off all the lights
[ATLAS] All lights have been turned off, sir.
```

### Thermostat

```
You: Set the temperature to 72
[ATLAS] Thermostat set to 72 degrees, sir.

You: What's the temperature?
[ATLAS] The current temperature is 71 degrees, sir.
The thermostat is set to 72.

You: Turn on the AC
[ATLAS] Air conditioning activated, sir.
```

### Locks

```
You: Lock the front door
[ATLAS] Front door is now locked, sir.

You: Is the front door locked?
[ATLAS] Yes, sir. The front door is secured.
```

### Scenes

```
You: Set movie mode
[ATLAS] Movie mode activated, sir. Lights dimmed,
TV on, and blinds closed.

You: Goodnight mode
[ATLAS] Goodnight, sir. All lights off, doors locked,
thermostat set to 68.
```

---

## Entity Configuration

Map friendly names to Home Assistant entity IDs:

```yaml
entities:
  # Lights
  office_lights: "light.office_main"
  office_lamp: "light.office_desk_lamp"
  bedroom_lights: "light.bedroom_ceiling"

  # Climate
  thermostat: "climate.nest_thermostat"
  bedroom_fan: "fan.bedroom"

  # Locks
  front_door: "lock.front_door_lock"
  back_door: "lock.back_door_lock"

  # Media
  living_room_tv: "media_player.living_room_tv"
  office_speaker: "media_player.office_homepod"

  # Covers
  office_blinds: "cover.office_blinds"
```

---

## Natural Language Processing

ATLAS understands various phrasings:

| You Say | ATLAS Understands |
|---------|-------------------|
| "Turn on the lights" | `light.turn_on` office (default) |
| "Switch off bedroom" | `light.turn_off` bedroom |
| "Dim to 50" | `light.turn_on` brightness 50% |
| "Make it warmer" | Increase thermostat |
| "It's too cold" | Increase thermostat |
| "Lock up" | Lock all locks |

---

## Status Queries

```
You: Home status

[ATLAS] Home status, sir:

🏠 Lights:
  • Office: On (75%)
  • Bedroom: Off
  • Living room: On (100%)

🌡️ Climate:
  • Temperature: 71°F
  • Thermostat: 72°F (cooling)
  • Humidity: 45%

🔒 Security:
  • Front door: Locked
  • Back door: Locked
  • Garage: Closed
```

---

## Troubleshooting

> [!warning] Connection Failed
> Check network connectivity:
> ```bash
> curl -H "Authorization: Bearer $HA_TOKEN" \
>      http://homeassistant.local:8123/api/
> ```

> [!warning] Entity Not Found
> Verify entity ID in Home Assistant:
> 1. Go to Developer Tools → States
> 2. Search for your device
> 3. Copy exact entity_id

> [!tip] Find Entity IDs
> In Home Assistant Developer Tools:
> - States tab shows all entities
> - Filter by domain (light, climate, lock)

---

## See Also

- [[Configuration]] - Integration settings
- [[Voice Interface]] - Voice control for smart home
- [[Learning Engine]] - Automated routines

---

#smart-home #home-assistant #automation
