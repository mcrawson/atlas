"""Unified smart home controller for ATLAS - natural language interface."""

import re
from typing import Optional, Tuple, Dict, Any, List
import logging

from .home_assistant import HomeAssistantClient

logger = logging.getLogger("atlas.integrations.smart_home")


class SmartHomeController:
    """Natural language interface for smart home control."""

    # Command patterns for parsing
    PATTERNS = {
        # Lights
        r"(turn|switch)\s+(on|off)\s+(the\s+)?(.+?)(\s+lights?)?$": "light_toggle",
        r"(dim|set)\s+(the\s+)?(.+?)\s+(lights?\s+)?to\s+(\d+)\s*%?": "light_brightness",
        r"(brighten|bright)\s+(the\s+)?(.+?)(\s+lights?)?": "light_brighten",

        # Temperature/Climate
        r"set\s+(the\s+)?(temp|temperature|thermostat)\s+to\s+(\d+)": "climate_set",
        r"(what('?s| is)\s+(the\s+)?(temp|temperature))": "climate_query",
        r"(turn|switch)\s+(on|off)\s+(the\s+)?(heat|heating|ac|air\s*conditioning|hvac)": "climate_toggle",

        # Locks
        r"(lock|unlock)\s+(the\s+)?(.+?)(\s+door)?$": "lock_control",
        r"(are\s+)?(the\s+)?doors?\s+(locked|unlocked)": "lock_query",

        # General
        r"(turn|switch)\s+(on|off)\s+(the\s+)?(.+)$": "entity_toggle",
    }

    def __init__(
        self,
        ha_client: HomeAssistantClient = None,
        entity_aliases: Dict[str, str] = None,
    ):
        """Initialize smart home controller.

        Args:
            ha_client: Home Assistant client
            entity_aliases: Dict mapping friendly names to entity IDs
        """
        self.ha = ha_client or HomeAssistantClient()
        self.aliases = entity_aliases or {}

        # Default aliases for common entities
        self.default_aliases = {
            "office": "light.office",
            "office lights": "light.office",
            "bedroom": "light.bedroom",
            "bedroom lights": "light.bedroom",
            "living room": "light.living_room",
            "living room lights": "light.living_room",
            "kitchen": "light.kitchen",
            "kitchen lights": "light.kitchen",
            "all lights": "group.all_lights",
            "thermostat": "climate.main",
            "front door": "lock.front_door",
            "back door": "lock.back_door",
        }

    def is_available(self) -> bool:
        """Check if smart home control is available.

        Returns:
            True if Home Assistant is configured
        """
        return self.ha.is_configured()

    def _resolve_entity(self, name: str) -> Optional[str]:
        """Resolve a friendly name to an entity ID.

        Args:
            name: Friendly name or partial entity ID

        Returns:
            Entity ID or None
        """
        name = name.lower().strip()

        # Check user aliases first
        if name in self.aliases:
            return self.aliases[name]

        # Check default aliases
        if name in self.default_aliases:
            return self.default_aliases[name]

        # If it looks like an entity ID already, return it
        if "." in name:
            return name

        # Try common patterns
        for prefix in ["light.", "switch.", "lock.", "climate."]:
            entity = f"{prefix}{name.replace(' ', '_')}"
            return entity

        return None

    def parse_command(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Parse a natural language command.

        Args:
            text: Natural language command

        Returns:
            Tuple of (command_type, parameters) or None
        """
        text = text.lower().strip()

        for pattern, cmd_type in self.PATTERNS.items():
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                return cmd_type, self._extract_params(cmd_type, groups)

        return None

    def _extract_params(self, cmd_type: str, groups: tuple) -> Dict[str, Any]:
        """Extract parameters from regex groups.

        Args:
            cmd_type: Command type
            groups: Regex match groups

        Returns:
            Parameters dictionary
        """
        params = {}

        if cmd_type == "light_toggle":
            params["action"] = groups[1]  # on/off
            params["entity_name"] = groups[3]

        elif cmd_type == "light_brightness":
            params["entity_name"] = groups[2]
            params["brightness"] = int(groups[4])

        elif cmd_type == "light_brighten":
            params["entity_name"] = groups[2]
            params["brightness"] = 100  # Max brightness

        elif cmd_type == "climate_set":
            params["temperature"] = int(groups[2])

        elif cmd_type == "climate_toggle":
            params["action"] = groups[1]  # on/off
            params["system"] = groups[3]  # heat/ac

        elif cmd_type == "lock_control":
            params["action"] = groups[0]  # lock/unlock
            params["entity_name"] = groups[2]

        elif cmd_type == "entity_toggle":
            params["action"] = groups[1]  # on/off
            params["entity_name"] = groups[3]

        return params

    async def execute(self, text: str) -> Tuple[bool, str]:
        """Execute a natural language command.

        Args:
            text: Natural language command

        Returns:
            Tuple of (success, butler_response)
        """
        if not self.is_available():
            return False, "Smart home control is not configured, sir."

        parsed = self.parse_command(text)
        if not parsed:
            return False, "I'm afraid I didn't understand that command, sir."

        cmd_type, params = parsed

        try:
            if cmd_type == "light_toggle":
                return await self._execute_light_toggle(params)
            elif cmd_type == "light_brightness":
                return await self._execute_light_brightness(params)
            elif cmd_type == "light_brighten":
                params["brightness"] = 100
                return await self._execute_light_brightness(params)
            elif cmd_type == "climate_set":
                return await self._execute_climate_set(params)
            elif cmd_type == "climate_query":
                return await self._execute_climate_query()
            elif cmd_type == "lock_control":
                return await self._execute_lock_control(params)
            elif cmd_type == "lock_query":
                return await self._execute_lock_query()
            elif cmd_type == "entity_toggle":
                return await self._execute_entity_toggle(params)
            else:
                return False, "I understand the command but cannot execute it, sir."

        except Exception as e:
            logger.error(f"Smart home command failed: {e}")
            return False, f"I'm afraid something went wrong, sir: {str(e)[:100]}"

    async def _execute_light_toggle(self, params: dict) -> Tuple[bool, str]:
        """Execute light on/off command."""
        entity = self._resolve_entity(params["entity_name"])
        if not entity:
            return False, f"I couldn't find a light called '{params['entity_name']}', sir."

        action = params["action"]
        if action == "on":
            success = await self.ha.turn_on(entity)
            response = f"The {params['entity_name']} lights are now on, sir." if success else "I was unable to turn on the lights, sir."
        else:
            success = await self.ha.turn_off(entity)
            response = f"The {params['entity_name']} lights are now off, sir." if success else "I was unable to turn off the lights, sir."

        return success, response

    async def _execute_light_brightness(self, params: dict) -> Tuple[bool, str]:
        """Execute light brightness command."""
        entity = self._resolve_entity(params["entity_name"])
        if not entity:
            return False, f"I couldn't find a light called '{params['entity_name']}', sir."

        brightness = params["brightness"]
        success = await self.ha.set_brightness(entity, brightness)

        if success:
            return True, f"I've set the {params['entity_name']} lights to {brightness}%, sir."
        return False, "I was unable to adjust the brightness, sir."

    async def _execute_climate_set(self, params: dict) -> Tuple[bool, str]:
        """Execute thermostat set command."""
        entity = self._resolve_entity("thermostat")
        if not entity:
            return False, "I couldn't find the thermostat, sir."

        temp = params["temperature"]
        success = await self.ha.set_temperature(entity, temp)

        if success:
            return True, f"I've set the thermostat to {temp} degrees, sir."
        return False, "I was unable to adjust the temperature, sir."

    async def _execute_climate_query(self) -> Tuple[bool, str]:
        """Query current temperature."""
        entity = self._resolve_entity("thermostat")
        if not entity:
            return False, "I couldn't find the thermostat, sir."

        state = await self.ha.get_state(entity)
        if state:
            current_temp = state.get("attributes", {}).get("current_temperature")
            target_temp = state.get("attributes", {}).get("temperature")
            if current_temp:
                response = f"The current temperature is {current_temp} degrees, sir."
                if target_temp:
                    response += f" The thermostat is set to {target_temp}."
                return True, response

        return False, "I was unable to read the temperature, sir."

    async def _execute_lock_control(self, params: dict) -> Tuple[bool, str]:
        """Execute lock/unlock command."""
        entity = self._resolve_entity(params["entity_name"])
        if not entity:
            return False, f"I couldn't find a lock called '{params['entity_name']}', sir."

        action = params["action"]
        if action == "lock":
            success = await self.ha.lock(entity)
            response = f"The {params['entity_name']} is now locked, sir." if success else "I was unable to lock it, sir."
        else:
            success = await self.ha.unlock(entity)
            response = f"The {params['entity_name']} is now unlocked, sir." if success else "I was unable to unlock it, sir."

        return success, response

    async def _execute_lock_query(self) -> Tuple[bool, str]:
        """Query lock status."""
        locks = await self.ha.get_entities_by_domain("lock")
        if not locks:
            return False, "I couldn't find any locks to check, sir."

        locked = []
        unlocked = []

        for lock in locks:
            name = lock.get("attributes", {}).get("friendly_name", lock.get("entity_id", "Unknown"))
            state = lock.get("state")
            if state == "locked":
                locked.append(name)
            else:
                unlocked.append(name)

        if not unlocked:
            return True, "All doors are locked, sir."
        elif not locked:
            return True, "All doors are currently unlocked, sir."
        else:
            return True, f"Locked: {', '.join(locked)}. Unlocked: {', '.join(unlocked)}."

    async def _execute_entity_toggle(self, params: dict) -> Tuple[bool, str]:
        """Execute generic entity toggle."""
        entity = self._resolve_entity(params["entity_name"])
        if not entity:
            return False, f"I couldn't find '{params['entity_name']}', sir."

        action = params["action"]
        if action == "on":
            success = await self.ha.turn_on(entity)
        else:
            success = await self.ha.turn_off(entity)

        if success:
            return True, f"Very good, sir. The {params['entity_name']} is now {action}."
        return False, f"I was unable to turn {action} the {params['entity_name']}, sir."

    async def get_summary(self) -> str:
        """Get a summary of smart home status.

        Returns:
            Status summary string
        """
        if not self.is_available():
            return "Smart home is not configured, sir."

        summary_parts = []

        # Lights
        lights = await self.ha.get_entities_by_domain("light")
        on_lights = [l for l in lights if l.get("state") == "on"]
        if on_lights:
            names = [l.get("attributes", {}).get("friendly_name", "Unknown")[:20] for l in on_lights[:3]]
            summary_parts.append(f"Lights on: {', '.join(names)}" + (" and more" if len(on_lights) > 3 else ""))
        else:
            summary_parts.append("All lights are off")

        # Climate
        climate = await self.ha.get_entities_by_domain("climate")
        if climate:
            c = climate[0]
            temp = c.get("attributes", {}).get("current_temperature")
            if temp:
                summary_parts.append(f"Temperature: {temp}°")

        # Locks
        locks = await self.ha.get_entities_by_domain("lock")
        unlocked = [l for l in locks if l.get("state") != "locked"]
        if unlocked:
            summary_parts.append(f"{len(unlocked)} door(s) unlocked")
        elif locks:
            summary_parts.append("All doors locked")

        return ". ".join(summary_parts) + "."
