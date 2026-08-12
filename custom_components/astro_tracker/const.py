"""Constants for Astro Tracker."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "astro_tracker"
NAME = "Astro Tracker"
VERSION = "0.2.0"

PLATFORMS = ["sensor", "binary_sensor", "calendar", "button"]

CONF_TRACKER_ENTITY = "tracker_entity"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_MOVEMENT_THRESHOLD = "movement_threshold_km"
CONF_EVENT_HORIZON_DAYS = "event_horizon_days"
CONF_ENABLE_WEATHER = "enable_weather"
CONF_ENABLE_SPACE_WEATHER = "enable_space_weather"
CONF_ENABLE_METEOR_SHOWERS = "enable_meteor_showers"

DEFAULT_UPDATE_INTERVAL = 30
DEFAULT_MOVEMENT_THRESHOLD = 5.0
DEFAULT_EVENT_HORIZON_DAYS = 370
DEFAULT_ENABLE_WEATHER = True
DEFAULT_ENABLE_SPACE_WEATHER = True
DEFAULT_ENABLE_METEOR_SHOWERS = True

MIN_UPDATE_INTERVAL = 10
MAX_UPDATE_INTERVAL = 360
MIN_EVENT_HORIZON_DAYS = 30
MAX_EVENT_HORIZON_DAYS = 730

REQUEST_TIMEOUT = 20
COORDINATOR_UPDATE_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
NOAA_ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"
USNO_MOON_PHASES_URL = "https://aa.usno.navy.mil/api/moon/phases/date"
USNO_SEASONS_URL = "https://aa.usno.navy.mil/api/seasons"
USNO_SOLAR_ECLIPSES_URL = "https://aa.usno.navy.mil/api/eclipses/solar/year"

ATTR_SOURCE_STATUS = "source_status"
ATTR_TRACKER_ENTITY = "tracker_entity"
ATTR_TRACKER_LATITUDE = "tracker_latitude"
ATTR_TRACKER_LONGITUDE = "tracker_longitude"
ATTR_TRACKER_TIMEZONE = "tracker_timezone"
ATTR_LAST_LOCATION_UPDATE = "last_location_update"

EVENT_TYPE_MOON_PHASE = "moon_phase"
EVENT_TYPE_LUNAR_ECLIPSE = "lunar_eclipse"
EVENT_TYPE_SOLAR_ECLIPSE = "solar_eclipse"
EVENT_TYPE_SEASON = "season"
EVENT_TYPE_METEOR_SHOWER = "meteor_shower"
EVENT_TYPE_SPACE_WEATHER = "space_weather"
