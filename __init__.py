"""The ha_reef_pi integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)
from homeassistant.exceptions import ConfigEntryAuthFailed

from async_timeout import timeout

import json

from .const import (_LOGGER, DOMAIN, HOST, USER, PASSWORD, VERIFY_TLS, UPDATE_INTERVAL_MIN, TIMEOUT_API_SEC)

from .api import ReefApi, CannotConnect, InvalidAuth

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["sensor", "switch"]


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured FMI."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ha_reef_pi from a config entry."""

    websession = async_get_clientsession(hass)
    coordinator = ReefPiDataUpdateCoordinator(
        hass, websession, entry
    )

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    undo_listener = entry.add_update_listener(update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "undo_update_listener": undo_listener,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    for component in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, component)

    hass.data[DOMAIN][entry.entry_id]["undo_update_listener"]()
    hass.data[DOMAIN].pop(entry.entry_id)

    return True


async def update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class ReefPiDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Reef-Pi data API."""

    def __init__(self, hass, session, config_entry):
        """Initialize."""

        _LOGGER.debug("Using host %s", config_entry.data[HOST])
        self.username = config_entry.data[USER]
        self.password = config_entry.data[PASSWORD]
        self.api = ReefApi(config_entry.data[HOST], verify=config_entry.data[VERIFY_TLS])
        self.unique_id = config_entry.data[HOST]
        self.hass = hass

        self.info = {}
        self.tcs = {}
        self.equipment = {}

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL_MIN
        )

    async def _async_update_data(self):
        """Update data via REST API."""

        def authenticate():
            if not self.api.is_authenticated():
                self.api.authenticate(self.username, self.password)

        def update_info():
            info = self.api.info()
            if info:
                info["cpu_temperature"] = float(info["cpu_temperature"].split("'")[0])
                info["model"] = info["model"].rstrip("\0")
                return info
            return {}

        def update_temperature():
            sensors = self.api.temperature_sensors()
            if sensors:
                _LOGGER.debug("temperature updated: %d", len(sensors))
                return {t["id"]: {
                    "name": t["name"],
                    "fahrenheit": t["fahrenheit"],
                    "temperature": self.api.temperature(t["id"])["temperature"]
                } for t in sensors}
            return {}

        def update_equipment():
            equipment = self.api.equipment()
            if equipment:
                _LOGGER.debug("equipment updated: %d", len(equipment))
                return {t["id"]: {"name": t["name"], "on": t["on"]} for t in equipment}
            return {}

        tcs = {}
        equipment = {}
        info = {}
        try:
            async with timeout(TIMEOUT_API_SEC):
                await self.hass.async_add_executor_job(authenticate)
                info = await self.hass.async_add_executor_job(update_info)
                tcs = await self.hass.async_add_executor_job(update_temperature)
                equipment = await self.hass.async_add_executor_job(update_equipment)
        except InvalidAuth as error:
            raise ConfigEntryAuthFailed from error
        except CannotConnect as error:
            raise UpdateFailed(error) from error
        finally:
            self.tcs = tcs
            self.equipment = equipment
            self.info = info
        return {}

    def equipment_control(self, id, on):
        self.api.equipment_control(id, on)
        self.equipment[id]["on"] = on
