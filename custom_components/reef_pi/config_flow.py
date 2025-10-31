"""Config flow for ha_reef_pi integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback

from .async_api import CannotConnect, InvalidAuth, ReefApi
from .const import (
    CALIBRATION_MODE,
    CALIBRATION_PROBE,
    CALIBRATION_TYPE_FRESHWATER,
    CALIBRATION_TYPE_SALTWATER,
    CONFIG_OPTIONS,
    DISABLE_PH,
    DOMAIN,
    START_CALIBRATION,
    UPDATE_INTERVAL_CFG,
    UPDATE_INTERVAL_MIN,
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

    # Return info that you want to store in the config entry.
    return {"title": info["name"]}


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
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]["coordinator"]
        probe_options = await coordinator.async_get_ph_probe_options()

        update_interval = self.config_entry.options.get(UPDATE_INTERVAL_CFG)
        if update_interval is None:
            update_interval = self.config_entry.data.get(UPDATE_INTERVAL_CFG)

        disable_ph_default = self.config_entry.options.get(DISABLE_PH, False)

        errors: dict[str, str] = {}
        calibration_probe = None
        calibration_mode = CALIBRATION_TYPE_FRESHWATER
        start_calibration = False
        new_update_interval = update_interval
        new_disable_ph = disable_ph_default

        if user_input is not None:
            new_update_interval = user_input.get(UPDATE_INTERVAL_CFG, update_interval)
            new_disable_ph = user_input.get(DISABLE_PH, disable_ph_default)
            calibration_probe = user_input.get(CALIBRATION_PROBE)
            calibration_mode = user_input.get(
                CALIBRATION_MODE, CALIBRATION_TYPE_FRESHWATER
            )
            start_calibration = user_input.get(START_CALIBRATION, False)

            if start_calibration:
                if not calibration_probe:
                    errors["base"] = "calibration_probe_required"
                else:
                    try:
                        probe_id = int(calibration_probe)
                    except (TypeError, ValueError):
                        errors["base"] = "calibration_probe_required"
                    else:
                        self.hass.async_create_task(
                            coordinator.async_calibrate_ph_probe(probe_id, calibration_mode)
                        )

            if not errors:
                data = self.config_entry.options.copy()
                if new_update_interval is not None:
                    data[UPDATE_INTERVAL_CFG] = new_update_interval
                data[DISABLE_PH] = new_disable_ph
                return self.async_create_entry(title="", data=data)

        if new_update_interval is None:
            new_update_interval = UPDATE_INTERVAL_MIN.total_seconds()

        schema_dict: dict[Any, Any] = {
            vol.Optional(UPDATE_INTERVAL_CFG, default=new_update_interval): int,
            vol.Optional(DISABLE_PH, default=new_disable_ph): bool,
        }

        if probe_options:
            default_probe = calibration_probe or next(iter(probe_options))
            schema_dict[vol.Optional(CALIBRATION_PROBE, default=default_probe)] = vol.In(
                probe_options
            )
            schema_dict[vol.Optional(
                CALIBRATION_MODE,
                default=calibration_mode,
            )] = vol.In(
                {
                    CALIBRATION_TYPE_FRESHWATER: "Freshwater",
                    CALIBRATION_TYPE_SALTWATER: "Saltwater",
                }
            )
            schema_dict[vol.Optional(START_CALIBRATION, default=start_calibration)] = bool

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
