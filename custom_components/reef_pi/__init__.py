"""The ha_reef_pi integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from async_timeout import timeout

import json
from datetime import datetime

from .const import (
    _LOGGER,
    DOMAIN,
    HOST,
    USER,
    PASSWORD,
    VERIFY_TLS,
    UPDATE_INTERVAL_MIN,
    TIMEOUT_API_SEC,
)

from .api import ReefApi, CannotConnect, InvalidAuth

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["sensor", "switch"]

REEFPI_DATETIME_FORMAT = "%b-%d-%H:%M, %Y"


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured FMI."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ha_reef_pi from a config entry."""

    websession = async_get_clientsession(hass)
    coordinator = ReefPiDataUpdateCoordinator(hass, websession, entry)

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

        _LOGGER.debug("Using host %s for %s", config_entry.data[HOST], config_entry.title)
        self.default_name = config_entry.title
        self.username = config_entry.data[USER]
        self.password = config_entry.data[PASSWORD]
        self.api = ReefApi(
            config_entry.data[HOST], verify=config_entry.data[VERIFY_TLS]
        )
        self.configuration_url = config_entry.data[HOST]
        self.unique_id = config_entry.data[HOST]
        self.hass = hass

        self.has_temperature = False
        self.has_equipment = False
        self.has_ph = False
        self.has_pumps = False

        self.info = {}
        self.tcs = {}
        self.equipment = {}
        self.ph = {}
        self.pumps = {}

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL_MIN
        )

    async def _async_update_data(self):
        """Update data via REST API."""

        def authenticate():
            if not self.api.is_authenticated():
                _LOGGER.debug("Authenticating")
                self.api.authenticate(self.username, self.password)
                _LOGGER.debug("Authenticated")

        def update_info():
            _LOGGER.debug("Fetching info")
            capabilities = self.api.capabilities()
            if capabilities:
                self.has_temperature = (
                    "temperature" in capabilities.keys() and capabilities["temperature"]
                )
                self.has_equipment = (
                    "equipment" in capabilities.keys() and capabilities["equipment"]
                )
                self.has_ph = (
                    "ph" in capabilities.keys() and capabilities["ph"]
                )
                self.has_pumps = (
                    "doser" in capabilities.keys() and capabilities["doser"]
                )
                _LOGGER.debug("Capabilities: ok")

            info = self.api.info()
            if info:
                info["cpu_temperature"] = float(info["cpu_temperature"].split("'")[0])
                info["model"] = info["model"].rstrip("\0")
                info["capabilities"] = capabilities
                _LOGGER.debug("Basic info: ok")
                return info
            return {}

        def update_temperature():
            if not self.has_temperature:
                return {}
            sensors = self.api.temperature_sensors()
            if sensors:
                _LOGGER.debug("temperature updated: %d", len(sensors))
                return {
                    t["id"]: {
                        "name": t["name"],
                        "fahrenheit": t["fahrenheit"],
                        "temperature": self.api.temperature(t["id"])["temperature"],
                        "attributes": t,
                    }
                    for t in sensors
                }
            return {}

        def update_equipment():
            if not self.has_equipment:
                return {}
            equipment = self.api.equipment()
            if equipment:
                _LOGGER.debug("equipment updated: %s", json.dumps(equipment))
                return {t["id"]: t for t in equipment}
            return {}

        def update_ph():
            if not self.has_ph:
                return {}

            probes = self.api.phprobes()
            if probes:
                _LOGGER.debug("pH probes updated: %s", json.dumps(probes))
                return {
                    p["id"]: {
                        "name": p["name"],
                        "value": self.api.ph(p["id"])["value"],
                        "attributes": p,
                    }
                    for p in probes
                }
            return {}

        def update_pumps():
            if not self.has_pumps:
                return {}

            result = {}
            try:
                pumps = self.api.pumps()
                for pump in pumps:
                    key = f"{pump['jack']}_{pump['pin']}"
                    _LOGGER.debug("Pump %s: %s", key, json.dumps(pump))
                    if key not in result.keys():
                        result[key] = {
                            "name": pump['name'],
                            "time": datetime.fromtimestamp(0),
                            "attributes": {
                                pump['id']: pump
                            }}
                    else:
                        result[key]['attributes'][pump['id']] = pump

                    current = self.api.pump(pump['id'])
                    if current and "time" in current.keys() and "pump" in current.keys():
                        time = datetime.strptime(current['time'], REEFPI_DATETIME_FORMAT)
                        if time > result[key]['time']:
                            result[key]['time'] = time
                            result[key]['attributes']['duration'] = current['pump']
            except Exception as ex:
                _LOGGER.exception(ex)
            return result

        tcs = {}
        equipment = {}
        info = {}
        ph = {}
        pumps = {}
        try:
            async with timeout(TIMEOUT_API_SEC):
                await self.hass.async_add_executor_job(authenticate)
                info = await self.hass.async_add_executor_job(update_info)
                tcs = await self.hass.async_add_executor_job(update_temperature)
                equipment = await self.hass.async_add_executor_job(update_equipment)
                ph = await self.hass.async_add_executor_job(update_ph)
                pumps = await self.hass.async_add_executor_job(update_pumps)
        except InvalidAuth as error:
            raise ConfigEntryAuthFailed from error
        except CannotConnect as error:
            raise UpdateFailed(error) from error
        finally:
            self.tcs = tcs
            self.equipment = equipment
            self.info = info
            self.ph = ph
            self.pumps = pumps
        return {}

    def equipment_control(self, id, on):
        self.api.equipment_control(id, on)
        self.equipment[id]["on"] = on
