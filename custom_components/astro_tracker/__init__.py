"""Astro Tracker integration."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import PLATFORMS
from .coordinator import AstroTrackerCoordinator
from .models import AstroTrackerData
from .solar_eclipse import compute_solar_eclipse_realtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Astro Tracker from a config entry."""
    coordinator = AstroTrackerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    realtime_running = False

    async def _async_refresh_solar_eclipse(force: bool = False) -> None:
        """Refresh only local eclipse geometry without polling cloud services."""
        nonlocal realtime_running
        if realtime_running or coordinator.data is None:
            return

        previous_values = coordinator.data.values
        now_utc = dt_util.utcnow()
        last_update = previous_values.get("solar_eclipse_updated_at")
        if not force and isinstance(last_update, datetime):
            if bool(previous_values.get("solar_eclipse_geometric_active")):
                minimum_interval = 1
            elif bool(previous_values.get("solar_eclipse_nearby")):
                minimum_interval = 5
            else:
                minimum_interval = 10
            if (now_utc - last_update).total_seconds() < minimum_interval:
                return

        tracker_state = hass.states.get(coordinator.tracker_entity)
        if tracker_state is None:
            return
        try:
            latitude = float(tracker_state.attributes["latitude"])
            longitude = float(tracker_state.attributes["longitude"])
        except (KeyError, TypeError, ValueError):
            return

        realtime_running = True
        try:
            eclipse_values = await hass.async_add_executor_job(
                compute_solar_eclipse_realtime,
                latitude,
                longitude,
                now_utc,
            )
            values = dict(coordinator.data.values)
            values.update(eclipse_values)
            values["latitude"] = latitude
            values["longitude"] = longitude

            source_status = dict(coordinator.data.source_status)
            source_status["solar_eclipse_realtime"] = "local"
            values["source_status"] = source_status

            coordinator.async_set_updated_data(
                AstroTrackerData(
                    values=values,
                    events=coordinator.data.events,
                    source_status=source_status,
                )
            )
        finally:
            realtime_running = False

    await _async_refresh_solar_eclipse(force=True)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _handle_tracker_update(event) -> None:
        """Refresh quickly after meaningful movement."""
        new_state = event.data.get("new_state")
        if coordinator.tracker_moved_enough(new_state):
            hass.async_create_task(coordinator.async_request_refresh())
            hass.async_create_task(_async_refresh_solar_eclipse(force=True))

    entry.async_on_unload(
        async_track_state_change_event(
            hass, [coordinator.tracker_entity], _handle_tracker_update
        )
    )

    @callback
    def _handle_realtime_tick(_now) -> None:
        """Run the adaptive local eclipse refresh loop."""
        hass.async_create_task(_async_refresh_solar_eclipse())

    entry.async_on_unload(
        async_track_time_interval(
            hass,
            _handle_realtime_tick,
            timedelta(seconds=1),
        )
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
