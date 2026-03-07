"""Home Assistant integration for ATLAS - smart home control."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("atlas.integrations.home_assistant")


class HomeAssistantClient:
    """Client for Home Assistant REST API."""

    def __init__(
        self,
        url: str = None,
        token: str = None,
        token_env: str = "HA_TOKEN",
        token_file: str = None,
    ):
        """Initialize Home Assistant client.

        Args:
            url: Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: Long-lived access token
            token_env: Environment variable containing token
            token_file: File containing token
        """
        self.url = url or os.environ.get("HA_URL", "http://homeassistant.local:8123")
        self.url = self.url.rstrip("/")

        # Get token from various sources
        self.token = token
        if not self.token:
            self.token = os.environ.get(token_env)
        if not self.token and token_file:
            token_path = Path(token_file).expanduser()
            if token_path.exists():
                self.token = token_path.read_text().strip()

        self._session = None

    def is_configured(self) -> bool:
        """Check if Home Assistant is configured.

        Returns:
            True if URL and token are set
        """
        return bool(self.url and self.token)

    def _get_headers(self):
        """Get headers for Home Assistant API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _create_session(self):
        """Create a new aiohttp session with headers."""
        import aiohttp
        return aiohttp.ClientSession(headers=self._get_headers())

    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def test_connection(self) -> bool:
        """Test connection to Home Assistant.

        Returns:
            True if connection successful
        """
        if not self.is_configured():
            return False

        try:
            import aiohttp

            async with self._create_session() as session:
                async with session.get(
                    f"{self.url}/api/",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Home Assistant connection failed: {e}")
            return False

    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity state.

        Args:
            entity_id: Entity ID (e.g., light.office)

        Returns:
            State dictionary or None
        """
        if not self.is_configured():
            return None

        try:
            import aiohttp

            async with self._create_session() as session:
                async with session.get(
                    f"{self.url}/api/states/{entity_id}",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.warning(f"Entity not found: {entity_id}")
                    return None
        except Exception as e:
            logger.error(f"Failed to get state for {entity_id}: {e}")
            return None

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str = None,
        **data
    ) -> bool:
        """Call a Home Assistant service.

        Args:
            domain: Service domain (e.g., light, switch, climate)
            service: Service name (e.g., turn_on, turn_off)
            entity_id: Target entity ID
            **data: Additional service data

        Returns:
            True if successful
        """
        if not self.is_configured():
            logger.warning("Home Assistant not configured")
            return False

        try:
            import aiohttp

            payload = dict(data)
            if entity_id:
                payload["entity_id"] = entity_id

            async with self._create_session() as session:
                async with session.post(
                    f"{self.url}/api/services/{domain}/{service}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    success = response.status in (200, 201)
                    if not success:
                        text = await response.text()
                        logger.error(f"Service call failed: {response.status} - {text}")
                    return success
        except Exception as e:
            logger.error(f"Failed to call service {domain}.{service}: {e}")
            return False

    async def get_all_states(self) -> List[Dict[str, Any]]:
        """Get all entity states.

        Returns:
            List of state dictionaries
        """
        if not self.is_configured():
            return []

        try:
            import aiohttp

            async with self._create_session() as session:
                async with session.get(
                    f"{self.url}/api/states",
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return []
        except Exception as e:
            logger.error(f"Failed to get all states: {e}")
            return []

    async def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all entities for a domain.

        Args:
            domain: Entity domain (e.g., light, switch)

        Returns:
            List of state dictionaries
        """
        all_states = await self.get_all_states()
        return [
            s for s in all_states
            if s.get("entity_id", "").startswith(f"{domain}.")
        ]

    # Convenience methods for common operations

    async def turn_on(self, entity_id: str, **kwargs) -> bool:
        """Turn on an entity.

        Args:
            entity_id: Entity to turn on
            **kwargs: Additional parameters (brightness, color, etc.)

        Returns:
            True if successful
        """
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "turn_on", entity_id, **kwargs)

    async def turn_off(self, entity_id: str) -> bool:
        """Turn off an entity.

        Args:
            entity_id: Entity to turn off

        Returns:
            True if successful
        """
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "turn_off", entity_id)

    async def toggle(self, entity_id: str) -> bool:
        """Toggle an entity.

        Args:
            entity_id: Entity to toggle

        Returns:
            True if successful
        """
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "toggle", entity_id)

    async def set_brightness(self, entity_id: str, brightness_pct: int) -> bool:
        """Set light brightness.

        Args:
            entity_id: Light entity ID
            brightness_pct: Brightness percentage (0-100)

        Returns:
            True if successful
        """
        # Convert percentage to 0-255
        brightness = int((brightness_pct / 100) * 255)
        return await self.call_service("light", "turn_on", entity_id, brightness=brightness)

    async def set_temperature(self, entity_id: str, temperature: float) -> bool:
        """Set thermostat temperature.

        Args:
            entity_id: Climate entity ID
            temperature: Target temperature

        Returns:
            True if successful
        """
        return await self.call_service("climate", "set_temperature", entity_id, temperature=temperature)

    async def lock(self, entity_id: str) -> bool:
        """Lock a lock entity.

        Args:
            entity_id: Lock entity ID

        Returns:
            True if successful
        """
        return await self.call_service("lock", "lock", entity_id)

    async def unlock(self, entity_id: str) -> bool:
        """Unlock a lock entity.

        Args:
            entity_id: Lock entity ID

        Returns:
            True if successful
        """
        return await self.call_service("lock", "unlock", entity_id)
