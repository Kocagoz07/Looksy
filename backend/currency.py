"""
Live currency conversion for Looksy.

Uses exchangerate.host (no API key) to fetch USD→EUR daily. Cached in memory
with a 1-hour TTL. A background refresh task (started on FastAPI startup)
keeps the rate fresh, so the SYNC `usd_to_eur` callers always read a recent
in-memory value without blocking.
"""

import os
import asyncio
import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Fallback when API + env are both unavailable
_DEFAULT_RATE = 0.92
_CACHE_TTL = timedelta(hours=1)
_API_URL = "https://open.er-api.com/v6/latest/USD"


class CurrencyConverter:
    def __init__(self):
        self._rate: float = float(os.environ.get("USD_TO_EUR_RATE", _DEFAULT_RATE))
        self._fetched_at: Optional[datetime] = None
        self._source: str = "env-or-default"
        self._task: Optional[asyncio.Task] = None

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def info(self) -> dict:
        return {
            "rate": self._rate,
            "source": self._source,
            "fetched_at": self._fetched_at.isoformat() if self._fetched_at else None,
            "ttl_hours": _CACHE_TTL.total_seconds() / 3600,
        }

    async def refresh(self) -> float:
        """Fetch the latest USD→EUR rate. Returns the new rate (cached on success)."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(_API_URL)
            resp.raise_for_status()
            data = resp.json()
            rate = float(data.get("rates", {}).get("EUR", 0))
            if rate <= 0:
                raise ValueError(f"invalid rate in response: {data}")
            self._rate = round(rate, 4)
            self._fetched_at = datetime.now(timezone.utc)
            self._source = "open.er-api.com"
            logger.info(f"USD→EUR rate refreshed: {self._rate}")
            return self._rate
        except Exception as e:
            logger.warning(f"Currency refresh failed ({e}); keeping rate={self._rate} ({self._source})")
            return self._rate

    def _is_stale(self) -> bool:
        if not self._fetched_at:
            return True
        return datetime.now(timezone.utc) - self._fetched_at > _CACHE_TTL

    async def _refresh_loop(self):
        while True:
            await self.refresh()
            await asyncio.sleep(_CACHE_TTL.total_seconds())

    def start_background_refresh(self):
        """Start a fire-and-forget refresh loop (call once on startup)."""
        if self._task is None or self._task.done():
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self._refresh_loop())

    def convert(self, usd_amount: float) -> float:
        return round(usd_amount * self._rate, 2)


# Singleton
_converter = CurrencyConverter()


def get_converter() -> CurrencyConverter:
    return _converter


def usd_to_eur(usd_amount: float) -> float:
    """Synchronous helper kept for backwards-compat with existing callers."""
    return _converter.convert(usd_amount)
