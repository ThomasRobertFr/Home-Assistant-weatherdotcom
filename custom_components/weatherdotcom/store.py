"""Persistent storage for the Weather.com component."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,

    HIGH_TEMP_TODAY_STORAGE,
    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE,
    LOW_TEMP_NIGHTS_STORAGE
)

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = '{domain}.{location_name}'
STORAGE_VERSION = 1

# Only the previous night is ever read back; keep a few for safety.
MAX_STORED_NIGHTS = 3


class WeatherDotComStorage:
    """Persistent storage for Weather.com data."""

    def __init__(self, hass: HomeAssistant, location_name: str) -> None:
        self._store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY.format(domain=DOMAIN, location_name=location_name.lower()),
        )

    async def async_load(self) -> dict[str, Any] | None:
        return await self._store.async_load() or {}

    async def async_save(
            self,
            high_temp_today=None,
            high_temp_today_timestamp=None,
            low_temp_night=None,
            low_temp_night_valid_time=None,
    ) -> None:
        """Merge the given values into what is already stored."""
        data_to_save = await self.async_load()
        if high_temp_today is not None:
            data_to_save[HIGH_TEMP_TODAY_STORAGE] = high_temp_today
            data_to_save[HIGH_TEMP_TODAY_TIMESTAMP_STORAGE] = high_temp_today_timestamp
        if low_temp_night is not None and low_temp_night_valid_time is not None:
            nights = data_to_save.get(LOW_TEMP_NIGHTS_STORAGE, {})
            nights[str(low_temp_night_valid_time)] = low_temp_night
            data_to_save[LOW_TEMP_NIGHTS_STORAGE] = dict(
                sorted(nights.items(), key=lambda kv: int(kv[0]))[-MAX_STORED_NIGHTS:])
        await self._store.async_save(data_to_save)
