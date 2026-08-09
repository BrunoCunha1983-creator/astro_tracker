"""Data coordinator for Astro Tracker."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
import math
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .astronomy import compute_astronomy
from .const import (
    CONF_ENABLE_METEOR_SHOWERS,
    CONF_ENABLE_SPACE_WEATHER,
    CONF_ENABLE_WEATHER,
    CONF_EVENT_HORIZON_DAYS,
    CONF_MOVEMENT_THRESHOLD,
    CONF_TRACKER_ENTITY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ENABLE_METEOR_SHOWERS,
    DEFAULT_ENABLE_SPACE_WEATHER,
    DEFAULT_ENABLE_WEATHER,
    DEFAULT_EVENT_HORIZON_DAYS,
    DEFAULT_MOVEMENT_THRESHOLD,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    EVENT_TYPE_SOLAR_ECLIPSE,
    NOAA_ALERTS_URL,
    NOAA_KP_URL,
    OPEN_METEO_URL,
    REQUEST_TIMEOUT,
    USNO_SOLAR_ECLIPSES_URL,
)
from .models import AstroEvent, AstroTrackerData

_LOGGER = logging.getLogger(__name__)


def _haversine_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """Calculate great-circle distance in kilometres."""
    radius = 6371.0088
    phi_1 = math.radians(latitude_1)
    phi_2 = math.radians(latitude_2)
    delta_phi = math.radians(latitude_2 - latitude_1)
    delta_lambda = math.radians(longitude_2 - longitude_1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _solar_eclipse_title(raw_event: str) -> str:
    """Translate common USNO solar eclipse descriptions."""
    lowered = raw_event.lower()
    if "total" in lowered:
        return "Eclipse solar total"
    if "annular" in lowered:
        return "Eclipse solar anular"
    if "hybrid" in lowered:
        return "Eclipse solar híbrido"
    if "partial" in lowered:
        return "Eclipse solar parcial"
    return "Eclipse solar"


class AstroTrackerCoordinator(DataUpdateCoordinator[AstroTrackerData]):
    """Coordinate local calculations and online sources."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self.tracker_entity = str(entry.data[CONF_TRACKER_ENTITY])
        self.movement_threshold_km = float(
            entry.data.get(CONF_MOVEMENT_THRESHOLD, DEFAULT_MOVEMENT_THRESHOLD)
        )
        self.event_horizon_days = int(
            entry.data.get(CONF_EVENT_HORIZON_DAYS, DEFAULT_EVENT_HORIZON_DAYS)
        )
        self.enable_weather = bool(
            entry.data.get(CONF_ENABLE_WEATHER, DEFAULT_ENABLE_WEATHER)
        )
        self.enable_space_weather = bool(
            entry.data.get(CONF_ENABLE_SPACE_WEATHER, DEFAULT_ENABLE_SPACE_WEATHER)
        )
        self.enable_meteor_showers = bool(
            entry.data.get(
                CONF_ENABLE_METEOR_SHOWERS, DEFAULT_ENABLE_METEOR_SHOWERS
            )
        )
        self.last_coordinates: tuple[float, float] | None = None
        self._solar_eclipse_cache: tuple[datetime, list[AstroEvent]] | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=int(
                    entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                )
            ),
            always_update=False,
        )

    def tracker_moved_enough(self, state: State | None) -> bool:
        """Return whether a tracker update warrants immediate refresh."""
        if state is None:
            return False
        latitude = state.attributes.get("latitude")
        longitude = state.attributes.get("longitude")
        try:
            new_coordinates = (float(latitude), float(longitude))
        except (TypeError, ValueError):
            return False
        if self.last_coordinates is None:
            return True
        distance = _haversine_km(*self.last_coordinates, *new_coordinates)
        return distance >= self.movement_threshold_km

    async def _async_get_json(
        self, url: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Fetch JSON with common timeout and error handling."""
        session = async_get_clientsession(self.hass)
        timeout = ClientTimeout(total=REQUEST_TIMEOUT)
        async with session.get(url, params=params, timeout=timeout) as response:
            response.raise_for_status()
            return await response.json(content_type=None)

    async def _async_fetch_weather(
        self, latitude: float, longitude: float
    ) -> tuple[dict[str, Any], str]:
        """Fetch current cloud and visibility conditions from Open-Meteo."""
        payload = await self._async_get_json(
            OPEN_METEO_URL,
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "cloud_cover,visibility,weather_code,precipitation",
                "daily": "sunrise,sunset,daylight_duration,sunshine_duration",
                "timezone": "auto",
                "forecast_days": 1,
            },
        )
        current = payload.get("current", {})
        daily = payload.get("daily", {})
        values = {
            "cloud_cover": current.get("cloud_cover"),
            "visibility_m": current.get("visibility"),
            "weather_code": current.get("weather_code"),
            "precipitation": current.get("precipitation"),
            "daylight_duration_s": (daily.get("daylight_duration") or [None])[0],
            "sunshine_duration_s": (daily.get("sunshine_duration") or [None])[0],
            "weather_sunrise_local": (daily.get("sunrise") or [None])[0],
            "weather_sunset_local": (daily.get("sunset") or [None])[0],
            "tracker_timezone": payload.get("timezone") or "UTC",
            "utc_offset_seconds": payload.get("utc_offset_seconds", 0),
        }
        return values, "online"

    async def _async_fetch_space_weather(self) -> tuple[dict[str, Any], str]:
        """Fetch current Kp and recent official NOAA alerts."""
        kp_payload, alerts_payload = await asyncio.gather(
            self._async_get_json(NOAA_KP_URL),
            self._async_get_json(NOAA_ALERTS_URL),
        )

        kp_value: float | None = None
        kp_time: str | None = None
        if isinstance(kp_payload, list) and len(kp_payload) > 1:
            headers = kp_payload[0]
            for row in reversed(kp_payload[1:]):
                if not isinstance(row, list):
                    continue
                record = dict(zip(headers, row, strict=False))
                raw_kp = record.get("Kp") or record.get("kp_index")
                try:
                    kp_value = float(raw_kp)
                    kp_time = record.get("time_tag") or record.get("time_tag_a")
                    break
                except (TypeError, ValueError):
                    continue

        alerts: list[dict[str, Any]] = []
        if isinstance(alerts_payload, list):
            for item in alerts_payload[-10:]:
                if isinstance(item, dict):
                    alerts.append(item)

        status = "quiet"
        if kp_value is not None:
            if kp_value >= 7:
                status = "strong_storm"
            elif kp_value >= 5:
                status = "geomagnetic_storm"
            elif kp_value >= 4:
                status = "active"

        return (
            {
                "kp_index": kp_value,
                "kp_time": kp_time,
                "geomagnetic_status": status,
                "space_weather_alerts": alerts,
            },
            "online",
        )

    async def _async_fetch_solar_eclipses(self, now_utc: datetime) -> list[AstroEvent]:
        """Fetch and cache global solar eclipse dates from USNO."""
        if self._solar_eclipse_cache is not None:
            cached_at, cached_events = self._solar_eclipse_cache
            if now_utc - cached_at < timedelta(hours=24):
                return cached_events

        last_year = min(2050, now_utc.year + max(2, self.event_horizon_days // 365 + 1))
        requests = [
            self._async_get_json(USNO_SOLAR_ECLIPSES_URL, {"year": year})
            for year in range(now_utc.year, last_year + 1)
        ]
        responses = await asyncio.gather(*requests, return_exceptions=True)

        events: list[AstroEvent] = []
        for response in responses:
            if isinstance(response, Exception) or not isinstance(response, dict):
                continue
            for item in response.get("eclipses_in_year", []):
                try:
                    event_date = datetime(
                        int(item["year"]),
                        int(item["month"]),
                        int(item["day"]),
                        12,
                        0,
                        tzinfo=UTC,
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                if event_date < now_utc - timedelta(days=1):
                    continue
                raw_event = str(item.get("event", "Solar eclipse"))
                events.append(
                    AstroEvent(
                        start=event_date - timedelta(hours=6),
                        end=event_date + timedelta(hours=6),
                        summary=_solar_eclipse_title(raw_event),
                        event_type=EVENT_TYPE_SOLAR_ECLIPSE,
                        description=(
                            "Data global fornecida pelo U.S. Naval Observatory. "
                            "A visibilidade exata no local ainda não é determinada nesta versão."
                        ),
                        attributes={
                            "usno_event": raw_event,
                            "visibility_scope": "global",
                        },
                    )
                )

        events.sort(key=lambda event: event.start)
        self._solar_eclipse_cache = (now_utc, events)
        return events

    @staticmethod
    def _calculate_observing_score(values: dict[str, Any]) -> int:
        """Calculate a practical 0-100 night-sky observing score."""
        sun_elevation = float(values.get("sun_elevation", 90))
        if sun_elevation > -6:
            return 0

        cloud_cover = values.get("cloud_cover")
        visibility_m = values.get("visibility_m")
        precipitation = values.get("precipitation")
        moon_illumination = float(values.get("moon_illumination", 0))
        moon_above = bool(values.get("moon_above_horizon"))

        score = 100.0
        if cloud_cover is not None:
            score -= min(100.0, float(cloud_cover)) * 0.75
        if visibility_m is not None:
            visibility_km = max(0.0, float(visibility_m) / 1000.0)
            if visibility_km < 5:
                score -= 30
            elif visibility_km < 10:
                score -= 15
        if precipitation is not None and float(precipitation) > 0:
            score -= 35
        if moon_above:
            score -= moon_illumination * 0.25
        if sun_elevation > -18:
            score -= (sun_elevation + 18) * 3

        return max(0, min(100, round(score)))

    async def _async_update_data(self) -> AstroTrackerData:
        """Fetch all data and merge it into a single payload."""
        tracker_state = self.hass.states.get(self.tracker_entity)
        if tracker_state is None:
            raise UpdateFailed(f"Tracker not found: {self.tracker_entity}")

        try:
            latitude = float(tracker_state.attributes["latitude"])
            longitude = float(tracker_state.attributes["longitude"])
        except (KeyError, TypeError, ValueError) as err:
            raise UpdateFailed(
                f"Tracker {self.tracker_entity} has no valid latitude/longitude"
            ) from err

        self.last_coordinates = (latitude, longitude)
        now_utc = dt_util.utcnow()
        source_status: dict[str, str] = {"skyfield": "local"}
        online_values: dict[str, Any] = {}

        timezone_name = self.hass.config.time_zone or "UTC"
        if self.enable_weather:
            try:
                weather_values, source_status["open_meteo"] = (
                    await self._async_fetch_weather(latitude, longitude)
                )
                online_values.update(weather_values)
                timezone_name = str(weather_values.get("tracker_timezone") or timezone_name)
            except (ClientError, asyncio.TimeoutError, ValueError, KeyError) as err:
                _LOGGER.warning("Open-Meteo update failed: %s", err)
                source_status["open_meteo"] = f"error: {type(err).__name__}"
        else:
            source_status["open_meteo"] = "disabled"

        try:
            local_values, events = await self.hass.async_add_executor_job(
                compute_astronomy,
                latitude,
                longitude,
                now_utc,
                self.event_horizon_days,
                timezone_name,
                self.enable_meteor_showers,
            )
        except Exception as err:  # Skyfield errors should fail this update.
            raise UpdateFailed(f"Astronomical calculation failed: {err}") from err

        values = {**local_values, **online_values}

        try:
            solar_events = await self._async_fetch_solar_eclipses(now_utc)
            events.extend(solar_events)
            source_status["usno"] = "online"
        except (ClientError, asyncio.TimeoutError, ValueError, KeyError) as err:
            _LOGGER.warning("USNO eclipse update failed: %s", err)
            source_status["usno"] = f"error: {type(err).__name__}"

        if self.enable_space_weather:
            try:
                space_values, source_status["noaa_swpc"] = (
                    await self._async_fetch_space_weather()
                )
                values.update(space_values)
            except (ClientError, asyncio.TimeoutError, ValueError, KeyError) as err:
                _LOGGER.warning("NOAA SWPC update failed: %s", err)
                source_status["noaa_swpc"] = f"error: {type(err).__name__}"
        else:
            source_status["noaa_swpc"] = "disabled"

        events.sort(key=lambda event: event.start)
        next_event = next((event for event in events if event.end > now_utc), None)
        next_solar_eclipse = next(
            (
                event
                for event in events
                if event.event_type == EVENT_TYPE_SOLAR_ECLIPSE
                and event.end > now_utc
            ),
            None,
        )
        values.update(
            {
                "latitude": latitude,
                "longitude": longitude,
                "tracker_entity": self.tracker_entity,
                "tracker_name": tracker_state.name,
                "tracker_timezone": timezone_name,
                "last_location_update": tracker_state.last_updated,
                "next_event": next_event,
                "next_solar_eclipse": next_solar_eclipse,
                "observing_score": self._calculate_observing_score(values),
                "source_status": source_status,
                "updated_at": now_utc,
            }
        )
        values["good_observing_conditions"] = values["observing_score"] >= 65
        values["geomagnetic_storm"] = (
            values.get("kp_index") is not None and float(values["kp_index"]) >= 5
        )
        values["event_within_24h"] = bool(
            next_event and next_event.start <= now_utc + timedelta(hours=24)
        )

        return AstroTrackerData(
            values=values,
            events=events,
            source_status=source_status,
        )
