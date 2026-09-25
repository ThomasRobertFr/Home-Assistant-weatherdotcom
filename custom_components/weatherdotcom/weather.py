"""
Support for Weather.com weather service.
For more details about this platform, please refer to the documentation at
https://github.com/jaydeethree/Home-Assistant-weatherdotcom
"""

import time

from . import WeatherUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from .const import (
    DOMAIN,

    TEMPUNIT,
    LENGTHUNIT,
    SPEEDUNIT,
    PRESSUREUNIT,

    FIELD_CLOUD_COVER,
    FIELD_DEW_POINT,
    FIELD_FEELS_LIKE,
    FIELD_HUMIDITY,
    FIELD_ICONCODE,
    FIELD_PRECIPCHANCE,
    FIELD_PRESSURE,
    FIELD_QPF,
    FIELD_TEMP,
    FIELD_TEMPERATUREMAX,
    FIELD_TEMPERATUREMIN,
    FIELD_UV_INDEX,
    FIELD_VALIDTIMEUTC,
    FIELD_VISIBILITY,
    FIELD_WINDDIR,
    FIELD_WINDDIRECTIONCARDINAL,
    FIELD_WINDGUST,
    FIELD_WINDSPEED,

    HIGH_TEMP_TODAY_STORAGE,
    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE,
    LOW_TEMP_NIGHTS_STORAGE
)
from .store import WeatherDotComStorage

import logging

from homeassistant.components.weather import (
    ATTR_FORECAST_CLOUD_COVERAGE,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_NATIVE_APPARENT_TEMP,
    ATTR_FORECAST_NATIVE_DEW_POINT,
    ATTR_FORECAST_NATIVE_WIND_GUST_SPEED,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_UV_INDEX,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
    Forecast,
    DOMAIN as WEATHER_DOMAIN
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

ENTITY_ID_FORMAT = WEATHER_DOMAIN + ".{}"


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add weather entity."""
    coordinator: WeatherUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        WeatherDotComForecast(coordinator),
    ])


class WeatherDotCom(SingleCoordinatorWeatherEntity):

    @property
    def native_temperature(self) -> float:
        """
        Return the platform temperature in native units
        (i.e. not converted).
        """
        return self.coordinator.get_current(FIELD_TEMP)

    @property
    def native_temperature_unit(self) -> str:
        """Return the native unit of measurement for temperature."""
        return self.coordinator.units_of_measurement[TEMPUNIT]

    @property
    def native_pressure(self) -> float:
        """Return the pressure in native units."""
        return self.coordinator.get_current(FIELD_PRESSURE)

    @property
    def native_pressure_unit(self) -> str:
        """Return the native unit of measurement for pressure."""
        return self.coordinator.units_of_measurement[PRESSUREUNIT]

    @property
    def humidity(self) -> float:
        """Return the relative humidity in native units."""
        return self.coordinator.get_current(FIELD_HUMIDITY)

    @property
    def native_wind_speed(self) -> float:
        """Return the wind speed in native units."""
        return self.coordinator.get_current(FIELD_WINDSPEED)

    @property
    def native_wind_speed_unit(self) -> str:
        """Return the native unit of measurement for wind speed."""
        return self.coordinator.units_of_measurement[SPEEDUNIT]

    @property
    def wind_bearing(self) -> str:
        """Return the wind bearing."""
        return self.coordinator.get_current(FIELD_WINDDIR)

    @property
    def native_visibility(self) -> float:
        """Return the visibility in native units."""
        return self.coordinator.get_current(FIELD_VISIBILITY)

    @property
    def native_visibility_unit(self) -> str:
        """Return the native unit of measurement for visibility."""
        return self.coordinator.visibility_unit

    @property
    def native_precipitation_unit(self) -> str:
        """
        Return the native unit of measurement for accumulated precipitation.
        """
        return self.coordinator.units_of_measurement[LENGTHUNIT]

    @property
    def condition(self) -> str:
        """Return the current condition."""
        icon = self.coordinator.get_current(FIELD_ICONCODE)
        return self.coordinator._iconcode_to_condition(icon)

    @property
    def native_apparent_temperature(self) -> float:
        """Return the 'feels like' temperature."""
        return self.coordinator.get_current(FIELD_FEELS_LIKE)

    @property
    def native_dew_point(self) -> float:
        """Return the dew point."""
        return self.coordinator.get_current(FIELD_DEW_POINT)

    @property
    def native_wind_gust_speed(self) -> float:
        """Return the wind gust speed."""
        return self.coordinator.get_current(FIELD_WINDGUST)

    @property
    def uv_index(self) -> float:
        """Return the UV index."""
        return self.coordinator.get_current(FIELD_UV_INDEX)


class WeatherDotComForecast(WeatherDotCom):

    def __init__(
            self,
            coordinator: WeatherUpdateCoordinator
    ):
        super().__init__(coordinator)
        """Initialize the sensor."""
        self.hass = coordinator.hass
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, f"{coordinator.location_name}", hass=self.hass
        )
        self._attr_unique_id = f"{coordinator.location_name},{WEATHER_DOMAIN}".lower()
        self._attr_device_info = coordinator.device_info
        self._store = WeatherDotComStorage(self.hass, coordinator.location_name)
        self._stored_data = {}

    @property
    def supported_features(self) -> WeatherEntityFeature:
        return (WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY)

    async def async_forecast_daily(self) -> list[Forecast] | None:
        self._stored_data = await self._store.async_load()
        return self.forecast_daily

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        return self.forecast_hourly
    
    @property
    def forecast_daily(self) -> list[Forecast]:
        """Return the daily forecast in native units."""
        days = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        if self.coordinator.get_forecast_daily('temperature', 0) is None:
            days[0] += 1

        forecast = []
        for period in days:
            # After 15:00 local time the Weather.com API returns None for the
            # high temperature. When this happens, return the last known high
            # temperature instead of None.
            temperature_max = self.coordinator.get_forecast_daily(FIELD_TEMPERATUREMAX, period)
            if period in [0, 1] and temperature_max == None:
                # This is 14 hours in seconds.
                max_time_difference = 14 * 60 * 60
                # If the API returns None, attempt to use the value that's in
                # storage.
                if (
                    HIGH_TEMP_TODAY_TIMESTAMP_STORAGE in self._stored_data
                    and
                    HIGH_TEMP_TODAY_STORAGE in self._stored_data
                    and
                    round(time.time()) - self._stored_data[HIGH_TEMP_TODAY_TIMESTAMP_STORAGE] < max_time_difference
                ):
                    temperature_max = self._stored_data[HIGH_TEMP_TODAY_STORAGE]
                else:
                    _LOGGER.debug(
                        'Stored value for maximum temperature is old or missing'
                        ' and the API is not returning this data - maximum'
                        ' temperature data in the daily forecast will be'
                        ' missing for today for: %s', self.entity_id)

            forecast.append(Forecast({
                ATTR_FORECAST_CLOUD_COVERAGE:
                    self.coordinator.get_forecast_daily(FIELD_CLOUD_COVER, period),
                ATTR_FORECAST_CONDITION:
                    self.coordinator._iconcode_to_condition(
                        self.coordinator.get_forecast_daily(
                            FIELD_ICONCODE, period)
                    ),
                ATTR_FORECAST_HUMIDITY:
                    self.coordinator.get_forecast_daily(FIELD_HUMIDITY, period),
                ATTR_FORECAST_PRECIPITATION:
                    self.coordinator.get_forecast_daily(FIELD_QPF, period),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY:
                    self.coordinator.get_forecast_daily(FIELD_PRECIPCHANCE, period),

                ATTR_FORECAST_TEMP:
                    temperature_max,
                ATTR_FORECAST_TEMP_LOW:
                    self._low_temp_for_day(period // 2),

                ATTR_FORECAST_TIME:
                    self.coordinator._format_timestamp(
                        self.coordinator.get_forecast_daily(
                            FIELD_VALIDTIMEUTC, period)),
                ATTR_FORECAST_UV_INDEX:
                    self.coordinator.get_forecast_daily(FIELD_UV_INDEX, period),
                ATTR_FORECAST_WIND_BEARING:
                    self.coordinator.get_forecast_daily(
                        FIELD_WINDDIR, period),
                ATTR_FORECAST_WIND_SPEED: self.coordinator.get_forecast_daily(
                    FIELD_WINDSPEED, period)
            }))
        return forecast

    def _low_temp_for_day(self, day: int) -> float | None:
        """
        Return the low of the night *before* the given day.

        Weather.com days run 7am to 7am, so temperatureMin for a day is the
        night that follows it. Most providers and observation networks call
        the morning low the day's low, so report the previous day's value.
        """
        if day > 0:
            return self.coordinator.get_forecast_daily(
                FIELD_TEMPERATUREMIN, 2 * (day - 1))

        # Last night is no longer in the API response: use the value stored
        # while it was still "tonight".
        valid_time = self.coordinator.get_forecast_daily(FIELD_VALIDTIMEUTC, 0)
        if valid_time is not None:
            nights = self._stored_data.get(LOW_TEMP_NIGHTS_STORAGE, {})
            for night_valid_time, low in nights.items():
                # One day earlier, give or take a DST change
                if abs(valid_time - int(night_valid_time) - 24 * 60 * 60) <= 2 * 60 * 60:
                    return low
        _LOGGER.debug(
            'No stored value for last night\'s low - minimum temperature'
            ' data in the daily forecast will be missing for today for: %s',
            self.entity_id)
        return None

    @property
    def forecast_hourly(self) -> list[Forecast]:
        """Return the hourly forecast in native units."""

        forecast = []
        for hour in range(0, 360, 1):
            forecast.append(Forecast({
                ATTR_FORECAST_CLOUD_COVERAGE:
                    self.coordinator.get_forecast_hourly(FIELD_CLOUD_COVER, hour),
                ATTR_FORECAST_CONDITION:
                    self.coordinator._iconcode_to_condition(
                        self.coordinator.get_forecast_hourly(
                            FIELD_ICONCODE, hour)
                    ),
                ATTR_FORECAST_HUMIDITY:
                    self.coordinator.get_forecast_hourly(FIELD_HUMIDITY, hour),
                ATTR_FORECAST_NATIVE_APPARENT_TEMP:
                    self.coordinator.get_forecast_hourly(FIELD_FEELS_LIKE, hour),
                ATTR_FORECAST_NATIVE_DEW_POINT:
                    self.coordinator.get_forecast_hourly(FIELD_DEW_POINT, hour),
                ATTR_FORECAST_NATIVE_WIND_GUST_SPEED:
                    self.coordinator.get_forecast_hourly(FIELD_WINDGUST, hour),
                ATTR_FORECAST_PRECIPITATION:
                    self.coordinator.get_forecast_hourly(FIELD_QPF, hour),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY:
                    self.coordinator.get_forecast_hourly(FIELD_PRECIPCHANCE, hour),
                ATTR_FORECAST_TEMP:
                    self.coordinator.get_forecast_hourly(FIELD_TEMP, hour),
                ATTR_FORECAST_TIME:
                    self.coordinator._format_timestamp(
                        self.coordinator.get_forecast_hourly(
                            FIELD_VALIDTIMEUTC, hour)),
                ATTR_FORECAST_UV_INDEX:
                    self.coordinator.get_forecast_hourly(FIELD_UV_INDEX, hour),
                ATTR_FORECAST_WIND_BEARING:
                    self.coordinator.get_forecast_hourly(
                        FIELD_WINDDIR, hour),
                ATTR_FORECAST_WIND_SPEED: self.coordinator.get_forecast_hourly(
                    FIELD_WINDSPEED, hour)
            }))
        return forecast
