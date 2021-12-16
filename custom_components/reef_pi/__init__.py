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

from .async_api import ReefApi, CannotConnect, InvalidAuth

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
        try:
            if not self.api.is_authenticated():
                _LOGGER.debug("Authenticating")
                await self.api.authenticate(self.username, self.password)
                _LOGGER.debug("Authenticated")

            _LOGGER.debug("Fetching capabilities")
            capabilities = await self.api.capabilities()
            if capabilities:
                get_cabability = lambda n: n in capabilities.keys() and capabilities[n]
                self.has_temperature = get_cabability("temperature")
                self.has_equipment = get_cabability("equipment")
                self.has_ph = get_cabability("ph")
                self.has_pumps = get_cabability("doser")
                _LOGGER.debug("Capabilities: ok")

            _LOGGER.debug("Fetching info")
            info = await self.api.info()
            if info:
                info["cpu_temperature"] = float(info["cpu_temperature"].split("'")[0])
                info["model"] = info["model"].rstrip("\0")
                info["capabilities"] = capabilities
                _LOGGER.debug("Basic info: ok")
                self.info = info

            if self.has_temperature:
                _LOGGER.debug("Fetching temperature")
                sensors = await self.api.temperature_sensors()
                if sensors:
                    _LOGGER.debug("temperature updated: %d", len(sensors))
                    self.tcs = {
                        t["id"]: {
                            "name": t["name"],
                            "fahrenheit": t["fahrenheit"],
                            "temperature": (await self.api.temperature(t["id"]))["temperature"],
                            "attributes": t,
                        }
                        for t in sensors
                    }

            if self.has_equipment:
                _LOGGER.debug("Fetching equipment")
                equipment = await self.api.equipment()
                if equipment:
                    _LOGGER.debug("equipment updated: %s", json.dumps(equipment))
                    self.equipment = {t["id"]: t for t in equipment}
            
            if self.has_ph:
                _LOGGER.debug("Fetching phprobes")
                probes = await self.api.phprobes()
                if probes:
                    _LOGGER.debug("pH probes updated: %s", json.dumps(probes))
                    all_ph = {}
                    for p in probes:
                        ph = await self.api.ph(p['id'])
                        all_ph[p["id"]] = {
                            "name": p["name"],
                            "value": ph["value"],
                            "attributes": p
                        }
                    self.ph = all_ph
            
            if self.has_pumps:
                _LOGGER.debug("Fetching pumps")
                result = {}
                try:
                    pumps = await self.api.pumps()
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

                        current = await self.api.pump(pump['id'])
                        if current and "time" in current.keys() and "pump" in current.keys():
                            time = datetime.strptime(current['time'], REEFPI_DATETIME_FORMAT)
                            if time > result[key]['time']:
                                result[key]['time'] = time
                                result[key]['attributes']['duration'] = current['pump']
                except Exception as ex:
                    _LOGGER.exception(ex)
                self.pumps = result
        except InvalidAuth as error:
            raise ConfigEntryAuthFailed from error
        except CannotConnect as error:
            raise UpdateFailed(error) from error
        return {}

    async def equipment_control(self, id, on):
        await self.api.equipment_control(id, on)
        self.equipment[id]["on"] = on
