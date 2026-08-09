"""Diagnostics for Astro Tracker."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import AstroTrackerCoordinator

TO_REDACT = {
    "latitude",
    "longitude",
    "tracker_latitude",
    "tracker_longitude",
    "last_location_update",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics with precise location removed."""
    coordinator: AstroTrackerCoordinator = entry.runtime_data
    return {
        "config": async_redact_data(dict(entry.data), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "source_status": coordinator.data.source_status,
        "values": async_redact_data(coordinator.data.values, TO_REDACT),
        "event_count": len(coordinator.data.events),
    }
