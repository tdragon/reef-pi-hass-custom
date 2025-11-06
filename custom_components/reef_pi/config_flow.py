"""Config flow for ha_reef_pi integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback

from .async_api import CannotConnect, InvalidAuth, ReefApi
from .const import (
    CONFIG_OPTIONS,
    DISABLE_PH,
    DOMAIN,
    MQTT_ENABLED,
    UPDATE_INTERVAL_CFG,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(CONFIG_OPTIONS)


async def validate_input(_hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    hub = ReefApi(data["host"], verify=data["verify"])

    await hub.authenticate(data["username"], data["password"])
    info = await hub.info()

    telemetry = await hub.telemetry_config()
    mqtt_config = telemetry.get("mqtt", {})
    mqtt_prefix = mqtt_config.get("prefix", "reef-pi")
    mqtt_available = mqtt_config.get("enable", False)

    # Return info that you want to store in the config entry.
    return {
        "title": info["name"],
        "mqtt_prefix": mqtt_prefix,
        "mqtt_available": mqtt_available,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ha_reef_pi."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        await self.async_set_unique_id(user_input["host"])
        self._abort_if_unique_id_configured()

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            user_input["mqtt_prefix"] = info["mqtt_prefix"]
            user_input["mqtt_available"] = info["mqtt_available"]
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ReefPiConfigFlowHandler:
        return ReefPiConfigFlowHandler()


class ReefPiConfigFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, _user_input=None):
        """Manage the options."""
        await self._refresh_mqtt_config()
        return await self.async_step_user()

    async def _refresh_mqtt_config(self):
        """Refresh MQTT configuration from reef-pi."""
        try:
            hub = ReefApi(
                self.config_entry.data["host"], verify=self.config_entry.data["verify"]
            )
            await hub.authenticate(
                self.config_entry.data["username"], self.config_entry.data["password"]
            )
            telemetry = await hub.telemetry_config()
            mqtt_config = telemetry.get("mqtt", {})
            mqtt_prefix = mqtt_config.get("prefix", "reef-pi")
            mqtt_available = mqtt_config.get("enable", False)

            if (
                self.config_entry.data.get("mqtt_prefix") != mqtt_prefix
                or self.config_entry.data.get("mqtt_available") != mqtt_available
            ):
                new_data = dict(self.config_entry.data)
                new_data["mqtt_prefix"] = mqtt_prefix
                new_data["mqtt_available"] = mqtt_available
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                _LOGGER.info(
                    "MQTT config refreshed: available=%s, prefix=%s",
                    mqtt_available,
                    mqtt_prefix,
                )
        except Exception as ex:
            _LOGGER.warning("Failed to refresh MQTT config: %s", ex)

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        update_interval = self.config_entry.options.get(UPDATE_INTERVAL_CFG)
        if update_interval is None:
            update_interval = self.config_entry.data.get(UPDATE_INTERVAL_CFG)

        mqtt_available = self.config_entry.data.get("mqtt_available", False)
        mqtt_enabled_default = self.config_entry.options.get(MQTT_ENABLED)
        if mqtt_enabled_default is None:
            mqtt_enabled_default = mqtt_available

        schema_dict = {
            vol.Optional(
                UPDATE_INTERVAL_CFG,
                default=update_interval,  # type: ignore
            ): int,
            vol.Optional(
                DISABLE_PH,
                default=self.config_entry.options.get(DISABLE_PH),  # type: ignore
            ): bool,
        }

        if mqtt_available:
            schema_dict[
                vol.Optional(
                    MQTT_ENABLED,
                    default=mqtt_enabled_default,  # type: ignore
                )
            ] = bool

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
        )
