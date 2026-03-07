"""Web/API monitoring for ATLAS - uptime, response times, price tracking."""

import asyncio
from datetime import datetime
from typing import List, Optional
import logging

from .monitor import Monitor, Alert, AlertSeverity

logger = logging.getLogger("atlas.monitoring.web")


class WebMonitor(Monitor):
    """Monitor websites and APIs for availability and changes."""

    name = "web"
    check_interval = 900  # 15 minutes

    def __init__(
        self,
        urls: List[dict] = None,
        timeout: int = 30,
        **kwargs
    ):
        """Initialize web monitor.

        Args:
            urls: List of URL configs, each with:
                  - url: The URL to check
                  - name: Friendly name (optional)
                  - expected_status: Expected HTTP status (default 200)
                  - max_response_time: Max acceptable response time in seconds
            timeout: Request timeout in seconds
        """
        super().__init__(**kwargs)
        self.urls = urls or []
        self.timeout = timeout
        self._response_history = {}  # url -> list of response times

    async def check(self) -> List[Alert]:
        """Check all configured URLs.

        Returns:
            List of alerts for any issues
        """
        if not self.urls:
            return []

        alerts = []

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                tasks = [
                    self._check_url(session, url_config)
                    for url_config in self.urls
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Alert):
                        alerts.append(result)
                    elif isinstance(result, Exception):
                        logger.error(f"URL check failed: {result}")

        except ImportError:
            logger.warning("aiohttp not available for web monitoring")

        return alerts

    async def _check_url(self, session, url_config: dict) -> Optional[Alert]:
        """Check a single URL.

        Args:
            session: aiohttp session
            url_config: URL configuration dict

        Returns:
            Alert if issue found, else None
        """
        import aiohttp

        url = url_config.get("url", "")
        name = url_config.get("name", url[:50])
        expected_status = url_config.get("expected_status", 200)
        max_response_time = url_config.get("max_response_time", 10)

        if not url:
            return None

        start_time = datetime.now()

        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                allow_redirects=True,
            ) as response:
                response_time = (datetime.now() - start_time).total_seconds()

                # Track response time history
                if url not in self._response_history:
                    self._response_history[url] = []
                self._response_history[url].append(response_time)
                # Keep last 10
                self._response_history[url] = self._response_history[url][-10:]

                # Check status code
                if response.status != expected_status:
                    return Alert(
                        monitor_name=self.name,
                        severity=AlertSeverity.WARNING,
                        message=f"{name} returned status {response.status} (expected {expected_status}).",
                        data={
                            "url": url,
                            "status": response.status,
                            "expected_status": expected_status,
                            "response_time": response_time,
                        },
                    )

                # Check response time
                if response_time > max_response_time:
                    avg_time = sum(self._response_history[url]) / len(self._response_history[url])
                    return Alert(
                        monitor_name=self.name,
                        severity=AlertSeverity.INFO,
                        message=f"{name} is responding slowly ({response_time:.1f}s, avg {avg_time:.1f}s).",
                        data={
                            "url": url,
                            "response_time": response_time,
                            "average_response_time": avg_time,
                        },
                    )

                return None

        except asyncio.TimeoutError:
            return Alert(
                monitor_name=self.name,
                severity=AlertSeverity.URGENT,
                message=f"{name} timed out after {self.timeout} seconds.",
                action_suggestion="The service may be down. Shall I investigate?",
                data={"url": url, "timeout": self.timeout},
            )

        except aiohttp.ClientError as e:
            return Alert(
                monitor_name=self.name,
                severity=AlertSeverity.WARNING,
                message=f"{name} is unreachable: {str(e)[:100]}",
                data={"url": url, "error": str(e)},
            )

        except Exception as e:
            logger.error(f"Unexpected error checking {url}: {e}")
            return None

    def add_url(self, url: str, name: str = None, **options) -> None:
        """Add a URL to monitor.

        Args:
            url: URL to monitor
            name: Friendly name
            **options: Additional options (expected_status, max_response_time)
        """
        config = {"url": url, "name": name or url[:50], **options}
        self.urls.append(config)

    def remove_url(self, url: str) -> bool:
        """Remove a URL from monitoring.

        Args:
            url: URL to remove

        Returns:
            True if found and removed
        """
        for i, config in enumerate(self.urls):
            if config.get("url") == url:
                del self.urls[i]
                return True
        return False

    def get_url_stats(self, url: str) -> Optional[dict]:
        """Get statistics for a monitored URL.

        Args:
            url: URL to get stats for

        Returns:
            Stats dictionary or None
        """
        if url not in self._response_history:
            return None

        times = self._response_history[url]
        if not times:
            return None

        return {
            "url": url,
            "checks": len(times),
            "avg_response_time": sum(times) / len(times),
            "min_response_time": min(times),
            "max_response_time": max(times),
            "last_response_time": times[-1],
        }


class PriceMonitor(Monitor):
    """Monitor prices and alert on changes (placeholder for future implementation)."""

    name = "price"
    check_interval = 3600  # 1 hour

    def __init__(self, items: List[dict] = None, **kwargs):
        """Initialize price monitor.

        Args:
            items: List of items to track, each with:
                   - url: Product URL
                   - name: Product name
                   - target_price: Price to alert below
        """
        super().__init__(**kwargs)
        self.items = items or []
        self._price_history = {}

    async def check(self) -> List[Alert]:
        """Check prices for configured items.

        Returns:
            List of alerts for price changes
        """
        # Placeholder - price monitoring would require
        # site-specific scraping or API integration
        return []
