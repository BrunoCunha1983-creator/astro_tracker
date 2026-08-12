"""Real-time local solar eclipse calculations for Astro Tracker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
import math
from typing import Any

from skyfield.api import wgs84

from .astronomy import _resources

SUN_RADIUS_KM = 695700.0
MOON_RADIUS_KM = 1737.4
SUN_HORIZON_LIMIT_DEG = -0.8333
NEAR_ECLIPSE_SEPARATION_DEG = 1.5
CIRCUMSTANCES_SEARCH_SEPARATION_DEG = 3.0


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a floating point value."""
    return max(low, min(high, value))


def _circle_overlap_fraction(sun_radius: float, moon_radius: float, separation: float) -> float:
    """Return the fraction of the apparent solar disc covered by the Moon."""
    if sun_radius <= 0 or moon_radius <= 0:
        return 0.0
    if separation >= sun_radius + moon_radius:
        return 0.0
    if separation <= abs(sun_radius - moon_radius):
        overlap_area = math.pi * min(sun_radius, moon_radius) ** 2
        return _clamp(overlap_area / (math.pi * sun_radius**2), 0.0, 1.0)

    first = math.acos(
        _clamp(
            (separation**2 + sun_radius**2 - moon_radius**2)
            / (2.0 * separation * sun_radius),
            -1.0,
            1.0,
        )
    )
    second = math.acos(
        _clamp(
            (separation**2 + moon_radius**2 - sun_radius**2)
            / (2.0 * separation * moon_radius),
            -1.0,
            1.0,
        )
    )
    radicand = (
        (-separation + sun_radius + moon_radius)
        * (separation + sun_radius - moon_radius)
        * (separation - sun_radius + moon_radius)
        * (separation + sun_radius + moon_radius)
    )
    overlap_area = (
        sun_radius**2 * first
        + moon_radius**2 * second
        - 0.5 * math.sqrt(max(0.0, radicand))
    )
    return _clamp(overlap_area / (math.pi * sun_radius**2), 0.0, 1.0)


def _geometry(latitude: float, longitude: float, moment: datetime) -> dict[str, Any]:
    """Calculate instantaneous topocentric Sun/Moon eclipse geometry."""
    _, timescale, ephemeris = _resources()
    moment = moment.astimezone(UTC)
    t = timescale.from_datetime(moment)

    earth = ephemeris["earth"]
    sun = ephemeris["sun"]
    moon = ephemeris["moon"]
    observer = earth + wgs84.latlon(latitude, longitude)

    sun_apparent = observer.at(t).observe(sun).apparent()
    moon_apparent = observer.at(t).observe(moon).apparent()
    sun_alt, sun_az, sun_distance = sun_apparent.altaz()
    moon_alt, moon_az, moon_distance = moon_apparent.altaz()

    separation = float(sun_apparent.separation_from(moon_apparent).degrees)
    sun_radius = math.degrees(
        math.asin(_clamp(SUN_RADIUS_KM / float(sun_distance.km), -1.0, 1.0))
    )
    moon_radius = math.degrees(
        math.asin(_clamp(MOON_RADIUS_KM / float(moon_distance.km), -1.0, 1.0))
    )
    obscuration = _circle_overlap_fraction(sun_radius, moon_radius, separation)
    geometric_active = separation < (sun_radius + moon_radius)
    sun_visible = float(sun_alt.degrees) >= SUN_HORIZON_LIMIT_DEG
    visible = geometric_active and sun_visible

    magnitude = 0.0
    if geometric_active:
        magnitude = max(
            0.0,
            (sun_radius + moon_radius - separation) / (2.0 * sun_radius),
        )

    if not geometric_active:
        phase = "fora do eclipse"
    elif separation <= abs(moon_radius - sun_radius):
        phase = "total" if moon_radius >= sun_radius else "anular"
    else:
        phase = "parcial"

    return {
        "solar_eclipse_phase": phase,
        "solar_eclipse_geometric_active": geometric_active,
        "solar_eclipse_visible": visible,
        "solar_eclipse_totality": visible and phase == "total",
        "solar_eclipse_annularity": visible and phase == "anular",
        "solar_eclipse_obscuration": round(obscuration * 100.0, 3),
        "solar_eclipse_magnitude": round(magnitude, 5),
        "solar_eclipse_separation": round(separation, 5),
        "solar_eclipse_sun_angular_radius": round(sun_radius, 6),
        "solar_eclipse_moon_angular_radius": round(moon_radius, 6),
        "solar_eclipse_sun_altitude": round(float(sun_alt.degrees), 3),
        "solar_eclipse_sun_azimuth": round(float(sun_az.degrees), 3),
        "solar_eclipse_moon_altitude": round(float(moon_alt.degrees), 3),
        "solar_eclipse_moon_azimuth": round(float(moon_az.degrees), 3),
        "solar_eclipse_nearby": separation <= NEAR_ECLIPSE_SEPARATION_DEG,
        "solar_eclipse_updated_at": moment,
    }


def _gap(latitude: float, longitude: float, moment: datetime, inner: bool) -> float:
    """Return contact gap; zero is a geometric contact."""
    geometry = _geometry(latitude, longitude, moment)
    separation = float(geometry["solar_eclipse_separation"])
    sun_radius = float(geometry["solar_eclipse_sun_angular_radius"])
    moon_radius = float(geometry["solar_eclipse_moon_angular_radius"])
    limit = abs(moon_radius - sun_radius) if inner else sun_radius + moon_radius
    return separation - limit


def _bisect_contact(
    latitude: float,
    longitude: float,
    start: datetime,
    end: datetime,
    inner: bool,
) -> datetime:
    """Refine an eclipse contact time by bisection."""
    left = start
    right = end
    left_value = _gap(latitude, longitude, left, inner)
    for _ in range(32):
        middle = left + (right - left) / 2
        middle_value = _gap(latitude, longitude, middle, inner)
        if (left_value <= 0) == (middle_value <= 0):
            left = middle
            left_value = middle_value
        else:
            right = middle
    return left + (right - left) / 2


def _refine_maximum(
    latitude: float,
    longitude: float,
    start: datetime,
    end: datetime,
) -> tuple[datetime, dict[str, Any]]:
    """Refine the instant of maximum obscuration with ternary search."""
    left = start
    right = end
    for _ in range(28):
        span = right - left
        first = left + span / 3
        second = right - span / 3
        first_value = float(
            _geometry(latitude, longitude, first)["solar_eclipse_obscuration"]
        )
        second_value = float(
            _geometry(latitude, longitude, second)["solar_eclipse_obscuration"]
        )
        if first_value < second_value:
            left = first
        else:
            right = second
    maximum = left + (right - left) / 2
    return maximum, _geometry(latitude, longitude, maximum)


@lru_cache(maxsize=64)
def _circumstances_cached(
    latitude_key: float,
    longitude_key: float,
    six_hour_bucket: int,
) -> dict[str, Any]:
    """Calculate and cache local contact times around a nearby eclipse."""
    latitude = float(latitude_key)
    longitude = float(longitude_key)
    center = datetime.fromtimestamp(six_hour_bucket * 21600, tz=UTC)
    search_start = center - timedelta(hours=8)
    search_end = center + timedelta(hours=8)
    step = timedelta(minutes=2)

    samples: list[tuple[datetime, dict[str, Any]]] = []
    moment = search_start
    while moment <= search_end:
        samples.append((moment, _geometry(latitude, longitude, moment)))
        moment += step

    outer_contacts: list[datetime] = []
    inner_contacts: list[datetime] = []
    for index in range(1, len(samples)):
        previous_time, previous = samples[index - 1]
        current_time, current = samples[index]

        previous_outer = float(previous["solar_eclipse_separation"]) - (
            float(previous["solar_eclipse_sun_angular_radius"])
            + float(previous["solar_eclipse_moon_angular_radius"])
        )
        current_outer = float(current["solar_eclipse_separation"]) - (
            float(current["solar_eclipse_sun_angular_radius"])
            + float(current["solar_eclipse_moon_angular_radius"])
        )
        if (previous_outer <= 0) != (current_outer <= 0):
            outer_contacts.append(
                _bisect_contact(
                    latitude, longitude, previous_time, current_time, False
                )
            )

        previous_inner = float(previous["solar_eclipse_separation"]) - abs(
            float(previous["solar_eclipse_moon_angular_radius"])
            - float(previous["solar_eclipse_sun_angular_radius"])
        )
        current_inner = float(current["solar_eclipse_separation"]) - abs(
            float(current["solar_eclipse_moon_angular_radius"])
            - float(current["solar_eclipse_sun_angular_radius"])
        )
        if (previous_inner <= 0) != (current_inner <= 0):
            inner_contacts.append(
                _bisect_contact(latitude, longitude, previous_time, current_time, True)
            )

    best_index = max(
        range(len(samples)),
        key=lambda idx: float(samples[idx][1]["solar_eclipse_obscuration"]),
    )
    best_time, best_geometry = samples[best_index]
    if float(best_geometry["solar_eclipse_obscuration"]) <= 0:
        return {}

    refine_start = max(search_start, best_time - step)
    refine_end = min(search_end, best_time + step)
    maximum, maximum_geometry = _refine_maximum(
        latitude, longitude, refine_start, refine_end
    )

    start = outer_contacts[0] if outer_contacts else None
    end = outer_contacts[-1] if len(outer_contacts) >= 2 else None
    second_contact = inner_contacts[0] if inner_contacts else None
    third_contact = inner_contacts[-1] if len(inner_contacts) >= 2 else None

    return {
        "solar_eclipse_start": start,
        "solar_eclipse_second_contact": second_contact,
        "solar_eclipse_maximum": maximum,
        "solar_eclipse_third_contact": third_contact,
        "solar_eclipse_end": end,
        "solar_eclipse_max_obscuration": maximum_geometry.get(
            "solar_eclipse_obscuration"
        ),
        "solar_eclipse_max_magnitude": maximum_geometry.get(
            "solar_eclipse_magnitude"
        ),
        "solar_eclipse_local_type": maximum_geometry.get("solar_eclipse_phase"),
        "solar_eclipse_sun_altitude_at_maximum": maximum_geometry.get(
            "solar_eclipse_sun_altitude"
        ),
        "solar_eclipse_visible_at_maximum": (
            float(maximum_geometry.get("solar_eclipse_sun_altitude", -90))
            >= SUN_HORIZON_LIMIT_DEG
        ),
    }


def compute_solar_eclipse_realtime(
    latitude: float,
    longitude: float,
    now_utc: datetime,
) -> dict[str, Any]:
    """Calculate current local eclipse state and nearby local circumstances."""
    now_utc = now_utc.astimezone(UTC)
    values = _geometry(latitude, longitude, now_utc)

    separation = float(values["solar_eclipse_separation"])
    if separation <= CIRCUMSTANCES_SEARCH_SEPARATION_DEG:
        bucket = int(now_utc.timestamp() // 21600)
        circumstances = _circumstances_cached(
            round(latitude, 3), round(longitude, 3), bucket
        )
        values.update(circumstances)

    maximum = values.get("solar_eclipse_maximum")
    if isinstance(maximum, datetime):
        seconds = (maximum - now_utc).total_seconds()
        values["solar_eclipse_seconds_to_maximum"] = max(0, round(seconds))
    else:
        values["solar_eclipse_seconds_to_maximum"] = None

    start = values.get("solar_eclipse_start")
    end = values.get("solar_eclipse_end")
    if isinstance(start, datetime) and isinstance(end, datetime) and end > start:
        elapsed = (now_utc - start).total_seconds()
        duration = (end - start).total_seconds()
        values["solar_eclipse_progress"] = round(
            _clamp(elapsed / duration, 0.0, 1.0) * 100.0, 2
        )
    else:
        values["solar_eclipse_progress"] = None

    values["solar_eclipse_source"] = "Skyfield/JPL local"
    return values
