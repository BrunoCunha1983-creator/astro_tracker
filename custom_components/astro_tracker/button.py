"""Button platform for Astro Tracker."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AstroTrackerCoordinator
from .entity import AstroTrackerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the manual refresh button."""
    coordinator: AstroTrackerCoordinator = entry.runtime_data
    async_add_entities([AstroTrackerRefreshButton(coordinator, entry)])


class AstroTrackerRefreshButton(AstroTrackerEntity, ButtonEntity):
    """Request an immediate refresh."""

    _attr_name = "Atualizar dados astronómicos"
    _attr_icon = "mdi:refresh"

    def __init__(
        self, coordinator: AstroTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, "refresh")

    async def async_press(self) -> None:
        """Refresh all data."""
        await self.coordinator.async_request_refresh()
