"""Sensor platform for Astro Tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AstroTrackerCoordinator
from .entity import AstroTrackerEntity
from .models import AstroEvent

ValueFn = Callable[[dict[str, Any]], Any]
AttrsFn = Callable[[dict[str, Any]], dict[str, Any]]


def _event_value(key: str) -> ValueFn:
    return lambda values: values[key].start if values.get(key) else None


def _event_attributes(key: str) -> AttrsFn:
    def attributes(values: dict[str, Any]) -> dict[str, Any]:
        event: AstroEvent | None = values.get(key)
        if event is None:
            return {}
        result = {
            "summary": event.summary,
            "event_type": event.event_type,
            "end": event.end.isoformat(),
            "description": event.description,
        }
        if event.location:
            result["location"] = event.location
        if event.attributes:
            result.update(event.attributes)
        return result

    return attributes


def _planet_attributes(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "planets": values.get("planet_positions", {}),
        "visible": values.get("visible_planets", []),
    }


def _source_attributes(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "latitude": values.get("latitude"),
        "longitude": values.get("longitude"),
        "tracker_entity": values.get("tracker_entity"),
        "tracker_name": values.get("tracker_name"),
        "last_location_update": values.get("last_location_update"),
        "sources": values.get("source_status", {}),
    }


def _solar_eclipse_attributes(values: dict[str, Any]) -> dict[str, Any]:
    """Return detailed local solar eclipse attributes."""
    return {
        "source": values.get("solar_eclipse_source"),
        "geometric_active": values.get("solar_eclipse_geometric_active"),
        "visible_from_tracker": values.get("solar_eclipse_visible"),
        "totality": values.get("solar_eclipse_totality"),
        "annularity": values.get("solar_eclipse_annularity"),
        "local_type": values.get("solar_eclipse_local_type"),
        "start": values.get("solar_eclipse_start"),
        "second_contact": values.get("solar_eclipse_second_contact"),
        "maximum": values.get("solar_eclipse_maximum"),
        "third_contact": values.get("solar_eclipse_third_contact"),
        "end": values.get("solar_eclipse_end"),
        "maximum_obscuration": values.get("solar_eclipse_max_obscuration"),
        "maximum_magnitude": values.get("solar_eclipse_max_magnitude"),
        "sun_altitude_at_maximum": values.get(
            "solar_eclipse_sun_altitude_at_maximum"
        ),
        "visible_at_maximum": values.get("solar_eclipse_visible_at_maximum"),
        "sun_altitude": values.get("solar_eclipse_sun_altitude"),
        "sun_azimuth": values.get("solar_eclipse_sun_azimuth"),
        "moon_altitude": values.get("solar_eclipse_moon_altitude"),
        "moon_azimuth": values.get("solar_eclipse_moon_azimuth"),
        "sun_angular_radius": values.get("solar_eclipse_sun_angular_radius"),
        "moon_angular_radius": values.get("solar_eclipse_moon_angular_radius"),
        "latitude": values.get("latitude"),
        "longitude": values.get("longitude"),
    }


@dataclass(frozen=True, kw_only=True)
class AstroSensorDescription(SensorEntityDescription):
    """Describe an Astro Tracker sensor."""

    value_fn: ValueFn
    attrs_fn: AttrsFn | None = None


SENSORS: tuple[AstroSensorDescription, ...] = (
    AstroSensorDescription(
        key="light_phase",
        name="Fase de luz",
        icon="mdi:theme-light-dark",
        value_fn=lambda v: v.get("light_phase"),
    ),
    AstroSensorDescription(
        key="day_night",
        name="Dia/noite",
        icon="mdi:weather-sunset-up",
        value_fn=lambda v: v.get("day_night"),
    ),
    AstroSensorDescription(
        key="sun_elevation",
        name="Elevação do Sol",
        icon="mdi:white-balance-sunny",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("sun_elevation"),
    ),
    AstroSensorDescription(
        key="sun_azimuth",
        name="Azimute do Sol",
        icon="mdi:compass",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("sun_azimuth"),
    ),
    AstroSensorDescription(
        key="next_sunrise",
        name="Próximo nascer do Sol",
        icon="mdi:weather-sunset-up",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("next_sunrise"),
    ),
    AstroSensorDescription(
        key="next_sunset",
        name="Próximo pôr do Sol",
        icon="mdi:weather-sunset-down",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("next_sunset"),
    ),
    AstroSensorDescription(
        key="moon_phase",
        name="Fase da Lua",
        icon="mdi:moon-waning-crescent",
        value_fn=lambda v: v.get("moon_phase"),
        attrs_fn=lambda v: {
            "phase_angle": v.get("moon_phase_angle"),
            "age_days": v.get("moon_age"),
        },
    ),
    AstroSensorDescription(
        key="moon_illumination",
        name="Iluminação da Lua",
        icon="mdi:brightness-percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("moon_illumination"),
    ),
    AstroSensorDescription(
        key="moon_elevation",
        name="Elevação da Lua",
        icon="mdi:moon-waxing-crescent",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("moon_elevation"),
    ),
    AstroSensorDescription(
        key="moon_azimuth",
        name="Azimute da Lua",
        icon="mdi:compass-outline",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("moon_azimuth"),
    ),
    AstroSensorDescription(
        key="moon_distance_km",
        name="Distância da Lua",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("moon_distance_km"),
    ),
    AstroSensorDescription(
        key="next_moonrise",
        name="Próximo nascer da Lua",
        icon="mdi:moon-waxing-crescent",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("next_moonrise"),
    ),
    AstroSensorDescription(
        key="next_moonset",
        name="Próximo pôr da Lua",
        icon="mdi:moon-waning-crescent",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("next_moonset"),
    ),
    AstroSensorDescription(
        key="visible_planets",
        name="Planetas observáveis",
        icon="mdi:orbit",
        value_fn=lambda v: len(v.get("visible_planets", [])),
        attrs_fn=_planet_attributes,
    ),
    AstroSensorDescription(
        key="observing_score",
        name="Qualidade de observação",
        icon="mdi:telescope",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("observing_score"),
        attrs_fn=lambda v: {
            "cloud_cover": v.get("cloud_cover"),
            "visibility_m": v.get("visibility_m"),
            "precipitation": v.get("precipitation"),
            "moon_illumination": v.get("moon_illumination"),
            "light_phase": v.get("light_phase"),
        },
    ),
    AstroSensorDescription(
        key="cloud_cover",
        name="Nebulosidade astronómica",
        icon="mdi:weather-cloudy",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("cloud_cover"),
    ),
    AstroSensorDescription(
        key="visibility_km",
        name="Visibilidade atmosférica",
        icon="mdi:eye-outline",
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: (
            round(float(v["visibility_m"]) / 1000, 1)
            if v.get("visibility_m") is not None
            else None
        ),
    ),
    AstroSensorDescription(
        key="kp_index",
        name="Índice geomagnético Kp",
        icon="mdi:aurora",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("kp_index"),
        attrs_fn=lambda v: {
            "status": v.get("geomagnetic_status"),
            "measurement_time": v.get("kp_time"),
            "recent_alerts": v.get("space_weather_alerts", []),
        },
    ),
    AstroSensorDescription(
        key="solar_eclipse_phase",
        name="Fase do eclipse solar",
        icon="mdi:weather-sunny-off",
        value_fn=lambda v: v.get("solar_eclipse_phase"),
        attrs_fn=_solar_eclipse_attributes,
    ),
    AstroSensorDescription(
        key="solar_eclipse_obscuration",
        name="Ocultação do eclipse solar",
        icon="mdi:circle-opacity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("solar_eclipse_obscuration"),
        attrs_fn=_solar_eclipse_attributes,
    ),
    AstroSensorDescription(
        key="solar_eclipse_magnitude",
        name="Magnitude do eclipse solar",
        icon="mdi:eclipse",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("solar_eclipse_magnitude"),
    ),
    AstroSensorDescription(
        key="solar_eclipse_separation",
        name="Separação Sol-Lua",
        icon="mdi:arrow-expand-horizontal",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("solar_eclipse_separation"),
    ),
    AstroSensorDescription(
        key="solar_eclipse_max_obscuration",
        name="Ocultação máxima local",
        icon="mdi:brightness-percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("solar_eclipse_max_obscuration"),
    ),
    AstroSensorDescription(
        key="solar_eclipse_progress",
        name="Progresso do eclipse solar",
        icon="mdi:progress-clock",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.get("solar_eclipse_progress"),
    ),
    AstroSensorDescription(
        key="solar_eclipse_seconds_to_maximum",
        name="Tempo até ao máximo do eclipse",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda v: v.get("solar_eclipse_seconds_to_maximum"),
    ),
    AstroSensorDescription(
        key="solar_eclipse_start",
        name="Início do eclipse solar local",
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("solar_eclipse_start"),
    ),
    AstroSensorDescription(
        key="solar_eclipse_maximum",
        name="Máximo do eclipse solar local",
        icon="mdi:clock-star-four-points",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("solar_eclipse_maximum"),
    ),
    AstroSensorDescription(
        key="solar_eclipse_end",
        name="Fim do eclipse solar local",
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("solar_eclipse_end"),
    ),
    AstroSensorDescription(
        key="solar_eclipse_updated_at",
        name="Última atualização do eclipse solar",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("solar_eclipse_updated_at"),
    ),
    AstroSensorDescription(
        key="next_event",
        name="Próximo fenómeno astronómico",
        icon="mdi:calendar-star",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_event_value("next_event"),
        attrs_fn=_event_attributes("next_event"),
    ),
    AstroSensorDescription(
        key="next_moon_phase",
        name="Próxima fase principal da Lua",
        icon="mdi:moon-full",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_event_value("next_moon_phase"),
        attrs_fn=_event_attributes("next_moon_phase"),
    ),
    AstroSensorDescription(
        key="next_lunar_eclipse",
        name="Próximo eclipse lunar",
        icon="mdi:moon-new",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_event_value("next_lunar_eclipse"),
        attrs_fn=_event_attributes("next_lunar_eclipse"),
    ),
    AstroSensorDescription(
        key="next_solar_eclipse",
        name="Próximo eclipse solar",
        icon="mdi:weather-sunny-off",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_event_value("next_solar_eclipse"),
        attrs_fn=_event_attributes("next_solar_eclipse"),
    ),
    AstroSensorDescription(
        key="next_season",
        name="Próximo evento sazonal",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_event_value("next_season"),
        attrs_fn=_event_attributes("next_season"),
    ),
    AstroSensorDescription(
        key="tracker_timezone",
        name="Fuso horário da localização",
        icon="mdi:map-clock",
        value_fn=lambda v: v.get("tracker_timezone"),
        attrs_fn=_source_attributes,
    ),
    AstroSensorDescription(
        key="updated_at",
        name="Última atualização astronómica",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: v.get("updated_at"),
        attrs_fn=lambda v: {"sources": v.get("source_status", {})},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Astro Tracker sensors."""
    coordinator: AstroTrackerCoordinator = entry.runtime_data
    async_add_entities(
        AstroTrackerSensor(coordinator, entry, description)
        for description in SENSORS
    )


class AstroTrackerSensor(AstroTrackerEntity, SensorEntity):
    """Representation of an Astro Tracker sensor."""

    entity_description: AstroSensorDescription

    def __init__(
        self,
        coordinator: AstroTrackerCoordinator,
        entry: ConfigEntry,
        description: AstroSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description
        if description.key.startswith("solar_eclipse_"):
            self._attr_suggested_object_id = f"astro_tracker_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data.values)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data.values)
