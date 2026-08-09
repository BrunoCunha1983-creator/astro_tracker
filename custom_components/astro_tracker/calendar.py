"""Calendar platform for Astro Tracker."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import AstroTrackerCoordinator
from .entity import AstroTrackerEntity
from .models import AstroEvent


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the astronomical events calendar."""
    coordinator: AstroTrackerCoordinator = entry.runtime_data
    async_add_entities([AstroTrackerCalendar(coordinator, entry)])


def _to_calendar_event(event: AstroEvent) -> CalendarEvent:
    """Convert an internal event to a Home Assistant calendar event."""
    description = event.description
    if event.attributes:
        details = ", ".join(f"{key}: {value}" for key, value in event.attributes.items())
        description = f"{description}\n\n{details}" if description else details
    return CalendarEvent(
        start=event.start,
        end=event.end,
        summary=event.summary,
        description=description or None,
        location=event.location or None,
    )


class AstroTrackerCalendar(AstroTrackerEntity, CalendarEntity):
    """Calendar of astronomical phenomena."""

    _attr_name = "Fenómenos astronómicos"
    _attr_icon = "mdi:calendar-star"

    def __init__(
        self, coordinator: AstroTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, entry, "astronomical_events")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the active or next event."""
        now = dt_util.utcnow()
        event = next(
            (item for item in self.coordinator.data.events if item.end > now), None
        )
        return _to_calendar_event(event) if event else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events in a date range."""
        return [
            _to_calendar_event(event)
            for event in self.coordinator.data.events
            if event.end > start_date and event.start < end_date
        ]
