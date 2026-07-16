import asyncio
from collections.abc import Callable
from typing import TypeVar

import httpx
from loguru import logger

from sky_radar.api.exceptions import TLEFetchError

T = TypeVar("T")


class CelesTrakClient:
    def __init__(self, base_url: str = "https://celestrak.org"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.max_retries = 3
        self.base_delay = 1.0

    async def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> T:
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2**attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")

        raise last_exception

    async def fetch_tle_group(self, group: str) -> list[tuple[str, str, str]]:
        url = f"{self.base_url}/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
        logger.info(f"Fetching TLE group: {group}")

        async def _fetch():
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text

        try:
            text = await self._retry_with_backoff(_fetch)
        except Exception as e:
            raise TLEFetchError(group, str(e)) from e
        return self._parse_tle(text)

    def _parse_tle(self, text: str) -> list[tuple[str, str, str]]:
        lines = text.strip().split("\n")
        satellites = []

        i = 0
        while i < len(lines) - 2:
            name = lines[i].strip()
            line1 = lines[i + 1].strip()
            line2 = lines[i + 2].strip()

            if line1.startswith("1 ") and line2.startswith("2 "):
                satellites.append((name, line1, line2))
                i += 3
            else:
                i += 1

        return satellites

    async def close(self):
        await self.client.aclose()
