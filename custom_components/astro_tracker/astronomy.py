"""Local astronomical calculations for Astro Tracker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
import math
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from skyfield import almanac, eclipselib
from skyfield.api import Loader, wgs84
from skyfield_data import get_skyfield_data_path

from .const import (
    EVENT_TYPE_LUNAR_ECLIPSE,
    EVENT_TYPE_METEOR_SHOWER,
    EVENT_TYPE_MOON_PHASE,
    EVENT_TYPE_SEASON,
)
from .models import AstroEvent

MOON_PHASE_NAMES = (
    "Lua Nova",
    "Quarto Crescente",
    "Lua Cheia",
    "Quarto Minguante",
)

SEASON_NAMES_NORTH = (
    "Equinócio de primavera",
    "Solstício de verão",
    "Equinócio de outono",
    "Solstício de inverno",
)

SEASON_NAMES_SOUTH = (
    "Equinócio de outono",
    "Solstício de inverno",
    "Equinócio de primavera",
    "Solstício de verão",
)

LUNAR_ECLIPSE_NAMES = (
    "Eclipse lunar penumbral",
    "Eclipse lunar parcial",
    "Eclipse lunar total",
)

# Peak dates are intentionally marked as approximate. Exact peaks can shift by hours.
METEOR_SHOWERS = (
    ("Quadrântidas", 1, 3, 120),
    ("Líridas", 4, 22, 18),
    ("Eta Aquáridas", 5, 6, 50),
    ("Delta Aquáridas do Sul", 7, 30, 25),
    ("Perseidas", 8, 12, 100),
    ("Oriónidas", 10, 21, 20),
    ("Táuridas do Sul", 11, 5, 5),
    ("Táuridas do Norte", 11, 12, 5),
    ("Leónidas", 11, 17, 15),
    ("Gemínidas", 12, 14, 120),
    ("Úrsidas", 12, 22, 10),
)

PLANETS = (
    ("Mercúrio", "mercury"),
    ("Vénus", "venus"),
    ("Marte", "mars"),
    ("Júpiter", "jupiter barycenter"),
    ("Saturno", "saturn barycenter"),
)


@lru_cache(maxsize=1)
def _resources() -> tuple[Any, Any, Any]:
    """Load Skyfield resources from the packaged ephemeris."""
    loader = Loader(get_skyfield_data_path(), expire=False)
    ephemeris = loader("de421.bsp")
    timescale = loader.timescale(builtin=True)
    return loader, timescale, ephemeris


def _as_utc(value: Any) -> datetime:
    """Convert a Skyfield Time scalar to an aware UTC datetime."""
    dt_value = value.utc_datetime()
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=UTC)
    return dt_value.astimezone(UTC)


def _phase_name(angle: float) -> str:
    """Return an eight-step Portuguese moon phase name."""
    angle %= 360.0
    if angle < 22.5 or angle >= 337.5:
        return "Lua Nova"
    if angle < 67.5:
        return "Crescente"
    if angle < 112.5:
        return "Quarto Crescente"
    if angle < 157.5:
        return "Gibosa Crescente"
    if angle < 202.5:
        return "Lua Cheia"
    if angle < 247.5:
        return "Gibosa Minguante"
    if angle < 292.5:
        return "Quarto Minguante"
    return "Minguante"


def _light_phase(sun_altitude: float) -> str:
    """Classify daylight using standard solar altitude bands."""
    if sun_altitude >= 0:
        return "dia"
    if sun_altitude >= -6:
        return "crepúsculo civil"
    if sun_altitude >= -12:
        return "crepúsculo náutico"
    if sun_altitude >= -18:
        return "crepúsculo astronómico"
    return "noite astronómica"


def _next_real_crossing(
    observer: Any,
    target: Any,
    timescale: Any,
    start: datetime,
    end: datetime,
    rising: bool,
) -> datetime | None:
    """Return the next actual rising or setting event."""
    t0 = timescale.from_datetime(start)
    t1 = timescale.from_datetime(end)
    finder = almanac.find_risings if rising else almanac.find_settings
    times, real_crossings = finder(observer, target, t0, t1)
    for item, is_real in zip(times, real_crossings, strict=False):
        candidate = _as_utc(item)
        if bool(is_real) and candidate > start:
            return candidate
    return None


def _meteor_events(
    now_utc: datetime,
    horizon_end: datetime,
    timezone_name: str,
) -> list[AstroEvent]:
    """Build approximate annual meteor-shower peak events."""
    try:
        local_tz = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        local_tz = UTC

    events: list[AstroEvent] = []
    start_year = now_utc.astimezone(local_tz).year
    end_year = horizon_end.astimezone(local_tz).year
    for year in range(start_year, end_year + 1):
        for name, month, day, zhr in METEOR_SHOWERS:
            local_start = datetime(year, month, day, 22, 0, tzinfo=local_tz)
            local_end = local_start + timedelta(hours=8)
            start = local_start.astimezone(UTC)
            end = local_end.astimezone(UTC)
            if end <= now_utc or start >= horizon_end:
                continue
            events.append(
                AstroEvent(
                    start=start,
                    end=end,
                    summary=f"Pico das {name}",
                    event_type=EVENT_TYPE_METEOR_SHOWER,
                    description=(
                        "Pico anual aproximado. A hora e a atividade real podem variar; "
                        f"taxa zenital típica até cerca de {zhr} meteoros/hora."
                    ),
                    attributes={"zhr_tipica": zhr, "pico_aproximado": True},
                )
            )
    return events


def compute_astronomy(
    latitude: float,
    longitude: float,
    now_utc: datetime,
    horizon_days: int,
    timezone_name: str,
    include_meteor_showers: bool,
) -> tuple[dict[str, Any], list[AstroEvent]]:
    """Calculate current astronomical state and future events."""
    _, timescale, ephemeris = _resources()
    now_utc = now_utc.astimezone(UTC)
    horizon_end = now_utc + timedelta(days=horizon_days)

    earth = ephemeris["earth"]
    sun = ephemeris["sun"]
    moon = ephemeris["moon"]
    observer = earth + wgs84.latlon(latitude, longitude)
    now_t = timescale.from_datetime(now_utc)

    sun_apparent = observer.at(now_t).observe(sun).apparent()
    sun_alt, sun_az, _ = sun_apparent.altaz()
    moon_apparent = observer.at(now_t).observe(moon).apparent()
    moon_alt, moon_az, moon_distance = moon_apparent.altaz()

    phase_angle = float(almanac.moon_phase(ephemeris, now_t).degrees)
    illumination = (1.0 - math.cos(math.radians(phase_angle))) * 50.0
    moon_age = (phase_angle / 360.0) * 29.530588

    short_end = now_utc + timedelta(days=3)
    next_sunrise = _next_real_crossing(
        observer, sun, timescale, now_utc, short_end, True
    )
    next_sunset = _next_real_crossing(
        observer, sun, timescale, now_utc, short_end, False
    )
    next_moonrise = _next_real_crossing(
        observer, moon, timescale, now_utc, short_end, True
    )
    next_moonset = _next_real_crossing(
        observer, moon, timescale, now_utc, short_end, False
    )

    events: list[AstroEvent] = []

    search_start = timescale.from_datetime(now_utc)
    search_end = timescale.from_datetime(horizon_end)

    phase_times, phase_codes = almanac.find_discrete(
        search_start, search_end, almanac.moon_phases(ephemeris)
    )
    for phase_time, phase_code in zip(phase_times, phase_codes, strict=False):
        start = _as_utc(phase_time)
        name = MOON_PHASE_NAMES[int(phase_code)]
        events.append(
            AstroEvent(
                start=start,
                end=start + timedelta(minutes=1),
                summary=name,
                event_type=EVENT_TYPE_MOON_PHASE,
                description="Fase lunar principal calculada localmente com efemérides JPL.",
                attributes={"phase_code": int(phase_code)},
            )
        )

    season_names = SEASON_NAMES_NORTH if latitude >= 0 else SEASON_NAMES_SOUTH
    season_times, season_codes = almanac.find_discrete(
        search_start, search_end, almanac.seasons(ephemeris)
    )
    for season_time, season_code in zip(
        season_times, season_codes, strict=False
    ):
        start = _as_utc(season_time)
        name = season_names[int(season_code)]
        events.append(
            AstroEvent(
                start=start,
                end=start + timedelta(minutes=1),
                summary=name,
                event_type=EVENT_TYPE_SEASON,
                description="Evento sazonal calculado para o hemisfério da localização atual.",
                attributes={"hemisphere": "norte" if latitude >= 0 else "sul"},
            )
        )

    eclipse_times, eclipse_codes, eclipse_details = eclipselib.lunar_eclipses(
        search_start, search_end, ephemeris
    )
    for index, (eclipse_time, eclipse_code) in enumerate(
        zip(eclipse_times, eclipse_codes, strict=False)
    ):
        start = _as_utc(eclipse_time)
        altitude = float(
            observer.at(eclipse_time).observe(moon).apparent().altaz()[0].degrees
        )
        code = int(eclipse_code)
        attrs: dict[str, Any] = {
            "visible_from_tracker": altitude > 0,
            "moon_altitude_at_maximum": round(altitude, 2),
        }
        for key in ("umbral_magnitude", "penumbral_magnitude"):
            detail_values = eclipse_details.get(key)
            if detail_values is not None:
                attrs[key] = round(float(detail_values[index]), 4)
        name = LUNAR_ECLIPSE_NAMES[code]
        events.append(
            AstroEvent(
                start=start - timedelta(hours=2),
                end=start + timedelta(hours=2),
                summary=name,
                event_type=EVENT_TYPE_LUNAR_ECLIPSE,
                description=(
                    "Máximo do eclipse calculado localmente. "
                    + (
                        "A Lua estará acima do horizonte nesta localização."
                        if altitude > 0
                        else "A Lua estará abaixo do horizonte nesta localização."
                    )
                ),
                attributes=attrs,
            )
        )

    if include_meteor_showers:
        events.extend(_meteor_events(now_utc, horizon_end, timezone_name))

    planet_data: dict[str, dict[str, Any]] = {}
    visible_planets: list[str] = []
    for display_name, ephemeris_name in PLANETS:
        target = ephemeris[ephemeris_name]
        apparent = observer.at(now_t).observe(target).apparent()
        altitude, azimuth, distance = apparent.altaz()
        altitude_value = float(altitude.degrees)
        is_visible = float(sun_alt.degrees) < -6 and altitude_value >= 10
        if is_visible:
            visible_planets.append(display_name)
        planet_data[display_name] = {
            "altitude": round(altitude_value, 2),
            "azimuth": round(float(azimuth.degrees), 2),
            "distance_au": round(float(distance.au), 4),
            "above_horizon": altitude_value > 0,
            "observing_candidate": is_visible,
        }

    events.sort(key=lambda event: event.start)
    next_event = next((event for event in events if event.end > now_utc), None)
    next_phase = next(
        (
            event
            for event in events
            if event.event_type == EVENT_TYPE_MOON_PHASE and event.start > now_utc
        ),
        None,
    )
    next_lunar_eclipse = next(
        (
            event
            for event in events
            if event.event_type == EVENT_TYPE_LUNAR_ECLIPSE
            and event.end > now_utc
        ),
        None,
    )
    next_season = next(
        (
            event
            for event in events
            if event.event_type == EVENT_TYPE_SEASON and event.start > now_utc
        ),
        None,
    )

    values: dict[str, Any] = {
        "sun_elevation": round(float(sun_alt.degrees), 2),
        "sun_azimuth": round(float(sun_az.degrees), 2),
        "sun_above_horizon": float(sun_alt.degrees) >= 0,
        "light_phase": _light_phase(float(sun_alt.degrees)),
        "day_night": "dia" if float(sun_alt.degrees) >= -0.8333 else "noite",
        "next_sunrise": next_sunrise,
        "next_sunset": next_sunset,
        "moon_elevation": round(float(moon_alt.degrees), 2),
        "moon_azimuth": round(float(moon_az.degrees), 2),
        "moon_distance_km": round(float(moon_distance.km), 0),
        "moon_above_horizon": float(moon_alt.degrees) >= 0,
        "moon_phase": _phase_name(phase_angle),
        "moon_phase_angle": round(phase_angle, 2),
        "moon_illumination": round(illumination, 1),
        "moon_age": round(moon_age, 2),
        "next_moonrise": next_moonrise,
        "next_moonset": next_moonset,
        "visible_planets": visible_planets,
        "planet_positions": planet_data,
        "next_event": next_event,
        "next_moon_phase": next_phase,
        "next_lunar_eclipse": next_lunar_eclipse,
        "next_season": next_season,
    }
    return values, events
