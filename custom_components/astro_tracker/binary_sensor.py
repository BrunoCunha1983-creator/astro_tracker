"""Binary sensor platform for Astro Tracker."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AstroTrackerCoordinator
from .entity import AstroTrackerEntity

ValueFn = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True, kw_only=True)
class AstroBinaryDescription(BinarySensorEntityDescription):
    """Describe an Astro Tracker binary sensor."""

    value_fn: ValueFn


BINARY_SENSORS: tuple[AstroBinaryDescription, ...] = (
    AstroBinaryDescription(
        key="sun_above_horizon",
        name="Sol acima do horizonte",
        icon="mdi:white-balance-sunny",
        value_fn=lambda v: bool(v.get("sun_above_horizon")),
    ),
    AstroBinaryDescription(
        key="moon_above_horizon",
        name="Lua acima do horizonte",
        icon="mdi:moon-waxing-crescent",
        value_fn=lambda v: bool(v.get("moon_above_horizon")),
    ),
    AstroBinaryDescription(
        key="good_observing_conditions",
        name="Boas condições de observação",
        icon="mdi:telescope",
        value_fn=lambda v: bool(v.get("good_observing_conditions")),
    ),
    AstroBinaryDescription(
        key="geomagnetic_storm",
        name="Tempestade geomagnética",
        icon="mdi:aurora",
        value_fn=lambda v: bool(v.get("geomagnetic_storm")),
    ),
    AstroBinaryDescription(
        key="event_within_24h",
        name="Fenómeno nas próximas 24 horas",
        icon="mdi:calendar-alert",
        value_fn=lambda v: bool(v.get("event_within_24h")),
    ),
    AstroBinaryDescription(
        key="solar_eclipse_active",
        name="Eclipse solar geométrico ativo",
        icon="mdi:eclipse",
        value_fn=lambda v: bool(v.get("solar_eclipse_geometric_active")),
    ),
    AstroBinaryDescription(
        key="solar_eclipse_visible",
        name="Eclipse solar visível",
        icon="mdi:weather-sunny-off",
        value_fn=lambda v: bool(v.get("solar_eclipse_visible")),
    ),
    AstroBinaryDescription(
        key="solar_eclipse_totality",
        name="Totalidade do eclipse solar",
        icon="mdi:circle-opacity",
        value_fn=lambda v: bool(v.get("solar_eclipse_totality")),
    ),
    AstroBinaryDescription(
        key="solar_eclipse_annularity",
        name="Anularidade do eclipse solar",
        icon="mdi:circle-outline",
        value_fn=lambda v: bool(v.get("solar_eclipse_annularity")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Astro Tracker binary sensors."""
    coordinator: AstroTrackerCoordinator = entry.runtime_data
    async_add_entities(
        AstroTrackerBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class AstroTrackerBinarySensor(AstroTrackerEntity, BinarySensorEntity):
    """Representation of an Astro Tracker binary sensor."""

    entity_description: AstroBinaryDescription

    def __init__(
        self,
        coordinator: AstroTrackerCoordinator,
        entry: ConfigEntry,
        description: AstroBinaryDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description
        if description.key.startswith("solar_eclipse_"):
            self._attr_suggested_object_id = f"astro_tracker_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return the binary state."""
        return self.entity_description.value_fn(self.coordinator.data.values)
