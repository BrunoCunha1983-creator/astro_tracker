"""Base entity for Astro Tracker."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import AstroTrackerCoordinator


class AstroTrackerEntity(CoordinatorEntity[AstroTrackerCoordinator]):
    """Base Astro Tracker entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AstroTrackerCoordinator,
        entry: ConfigEntry,
        entity_key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_key = entity_key
        self._attr_unique_id = f"{entry.entry_id}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="BC Home Assistant",
            model=NAME,
            sw_version=VERSION,
        )
