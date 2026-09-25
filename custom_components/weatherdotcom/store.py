"""Persistent storage for the Weather.com component."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import slugify

from .const import (
    DOMAIN,

    HIGH_TEMP_TODAY_STORAGE,
    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE,
    LOW_TEMP_NIGHTS_STORAGE
)

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
            STORAGE_KEY.format(domain=DOMAIN, location_name=slugify(location_name)),
        )
        self._data: dict[str, Any] | None = None

    async def async_load(self) -> dict[str, Any]:
        if self._data is None:
            self._data = await self._store.async_load() or {}
        return self._data

    async def async_save(
        self,
        high_temp_today: int | float | None = None,
        high_temp_today_timestamp: int | None = None,
        low_temp_night: int | float | None = None,
        low_temp_night_valid_time: int | None = None,
    ) -> None:
        """Merge the given values into what is already stored."""
        current = await self.async_load()
        data_to_save = dict(current)
        if high_temp_today is not None and high_temp_today_timestamp is not None:
            data_to_save[HIGH_TEMP_TODAY_STORAGE] = high_temp_today
            data_to_save[HIGH_TEMP_TODAY_TIMESTAMP_STORAGE] = high_temp_today_timestamp
        if low_temp_night is not None and low_temp_night_valid_time is not None:
            nights = dict(current.get(LOW_TEMP_NIGHTS_STORAGE) or {})
            nights[str(low_temp_night_valid_time)] = low_temp_night
            data_to_save[LOW_TEMP_NIGHTS_STORAGE] = dict(
                sorted(nights.items(), key=lambda kv: int(kv[0]))[-MAX_STORED_NIGHTS:])
        if data_to_save == current:
            return
        self._data = data_to_save
        await self._store.async_save(data_to_save)

    async def async_remove(self) -> None:
        self._data = None
        await self._store.async_remove()
