"""Config flow for Astro Tracker."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_ENABLE_METEOR_SHOWERS,
    CONF_ENABLE_SPACE_WEATHER,
    CONF_ENABLE_WEATHER,
    CONF_EVENT_HORIZON_DAYS,
    CONF_MOVEMENT_THRESHOLD,
    CONF_TRACKER_ENTITY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ENABLE_METEOR_SHOWERS,
    DEFAULT_ENABLE_SPACE_WEATHER,
    DEFAULT_ENABLE_WEATHER,
    DEFAULT_EVENT_HORIZON_DAYS,
    DEFAULT_MOVEMENT_THRESHOLD,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_EVENT_HORIZON_DAYS,
    MAX_UPDATE_INTERVAL,
    MIN_EVENT_HORIZON_DAYS,
    MIN_UPDATE_INTERVAL,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the configuration schema."""
    defaults = defaults or {}
    tracker_marker = (
        vol.Required(
            CONF_TRACKER_ENTITY, default=defaults[CONF_TRACKER_ENTITY]
        )
        if defaults.get(CONF_TRACKER_ENTITY)
        else vol.Required(CONF_TRACKER_ENTITY)
    )
    return vol.Schema(
        {
            tracker_marker: EntitySelector(
                EntitySelectorConfig(domain="device_tracker")
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_UPDATE_INTERVAL,
                    max=MAX_UPDATE_INTERVAL,
                    step=5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
            vol.Required(
                CONF_MOVEMENT_THRESHOLD,
                default=defaults.get(
                    CONF_MOVEMENT_THRESHOLD, DEFAULT_MOVEMENT_THRESHOLD
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.1,
                    max=100,
                    step=0.1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="km",
                )
            ),
            vol.Required(
                CONF_EVENT_HORIZON_DAYS,
                default=defaults.get(
                    CONF_EVENT_HORIZON_DAYS, DEFAULT_EVENT_HORIZON_DAYS
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_EVENT_HORIZON_DAYS,
                    max=MAX_EVENT_HORIZON_DAYS,
                    step=10,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="dias",
                )
            ),
            vol.Required(
                CONF_ENABLE_WEATHER,
                default=defaults.get(CONF_ENABLE_WEATHER, DEFAULT_ENABLE_WEATHER),
            ): BooleanSelector(),
            vol.Required(
                CONF_ENABLE_SPACE_WEATHER,
                default=defaults.get(
                    CONF_ENABLE_SPACE_WEATHER, DEFAULT_ENABLE_SPACE_WEATHER
                ),
            ): BooleanSelector(),
            vol.Required(
                CONF_ENABLE_METEOR_SHOWERS,
                default=defaults.get(
                    CONF_ENABLE_METEOR_SHOWERS, DEFAULT_ENABLE_METEOR_SHOWERS
                ),
            ): BooleanSelector(),
        }
    )


class AstroTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Astro Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            tracker = user_input[CONF_TRACKER_ENTITY]
            state = self.hass.states.get(tracker)
            if state is None:
                errors[CONF_TRACKER_ENTITY] = "tracker_not_found"
            elif state.attributes.get("latitude") is None or state.attributes.get(
                "longitude"
            ) is None:
                errors[CONF_TRACKER_ENTITY] = "tracker_has_no_coordinates"
            else:
                await self.async_set_unique_id(tracker)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Astro Tracker — {state.name}", data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )
