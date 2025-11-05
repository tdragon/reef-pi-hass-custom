"""The ha_reef_pi integration."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .async_api import CannotConnect, InvalidAuth, ReefApi
from .mqtt_handler import ReefPiMQTTHandler
from .const import (
    _LOGGER,
    CONFIG_OPTIONS,
    DISABLE_PH,
    DOMAIN,
    HOST,
    MANUFACTURER,
    MQTT_ENABLED,
    PASSWORD,
    UPDATE_INTERVAL_CFG,
    UPDATE_INTERVAL_MIN,
    USER,
    VERIFY_TLS,
)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["sensor", "switch", "light", "binary_sensor", "button"]

REEFPI_DATETIME_FORMAT = "%b-%d-%H:%M, %Y"


CONFIG_SCHEMA = vol.Schema({DOMAIN: CONFIG_OPTIONS}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ha_reef_pi from a config entry."""

    websession = async_get_clientsession(hass)
    coordinator = ReefPiDataUpdateCoordinator(hass, websession, entry)

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    await coordinator.async_setup_mqtt()

    undo_listener = entry.add_update_listener(update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "undo_update_listener": undo_listener,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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

        _LOGGER.debug(
            "Using host %s for %s", config_entry.data[HOST], config_entry.title
        )
        self.default_name = config_entry.title
        self.username = config_entry.data[USER]
        self.password = config_entry.data[PASSWORD]
        self.api = ReefApi(
            config_entry.data[HOST], verify=config_entry.data[VERIFY_TLS]
        )
        self.configuration_url = config_entry.data[HOST]
        self.unique_id = config_entry.data[HOST]
        self.hass = hass

        self.update_interval = UPDATE_INTERVAL_MIN
        update_interval = config_entry.options.get(
            UPDATE_INTERVAL_CFG
        ) or config_entry.data.get(UPDATE_INTERVAL_CFG)
        if update_interval is not None:
            self.update_interval = timedelta(seconds=update_interval)

        self.disable_ph = config_entry.options.get(DISABLE_PH) or False

        self.has_temperature = False
        self.has_equipment = False
        self.has_ph = False
        self.has_pumps = False
        self.has_ato = False
        self.has_timers = False
        self.has_lights = False
        self.has_camera = False
        self.has_macro = False
        self.has_display = False

        self.info = {}
        self.capabilities = {}
        self.tcs = {}
        self.equipment = {}
        self.ph = {}
        self.pumps = {}
        self.ato = {}
        self.ato_states = {}
        self.lights = {}
        self.inlets = {}
        self.macros = {}
        self.timers = {}
        self.display = {}

        self.tcs_name_to_id = {}
        self.equipment_name_to_id = {}
        self.ph_name_to_id = {}
        self.inlet_name_to_id = {}
        self.light_name_to_id = {}

        self.mqtt_prefix = config_entry.data.get("mqtt_prefix", "reef-pi")
        self.mqtt_enabled = config_entry.options.get(MQTT_ENABLED) or False
        self.mqtt_handler = None

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=self.update_interval
        )

    async def async_setup_mqtt(self):
        """Setup MQTT subscriptions."""
        if not self.mqtt_enabled:
            _LOGGER.debug("MQTT is disabled, skipping subscription")
            return

        self.mqtt_handler = ReefPiMQTTHandler(self.hass, self)
        await self.mqtt_handler.async_subscribe()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            configuration_url=self.configuration_url,
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer=MANUFACTURER,
            model=self.info["model"] if self.info["model"] else "Reef PI",
            name=self.info["name"] if self.info["name"] else self.default_name,
            sw_version=self.info["name"] if self.info["name"] else None,
        )

    async def update_capabilities(self):
        _LOGGER.debug("Fetching capabilities")

        def get_capability(name):
            return name in self.capabilities.keys() and self.capabilities[name]

        self.capabilities = await self.api.capabilities()
        if self.capabilities:
            self.has_temperature = get_capability("temperature")
            self.has_equipment = get_capability("equipment")
            self.has_ph = get_capability("ph") and not self.disable_ph
            self.has_pumps = get_capability("doser")
            self.has_ato = get_capability("ato")
            self.has_timers = get_capability("timers")
            self.has_lights = get_capability("lighting")
            self.has_camera = get_capability("camera")
            self.has_macro = get_capability("macro")
            self.has_display = get_capability("display")
            _LOGGER.debug("Capabilities: ok")

    async def update_info(self):
        _LOGGER.debug("Fetching info")
        info = await self.api.info()
        if info:
            info["cpu_temperature"] = float(info["cpu_temperature"].split("'")[0])
            info["model"] = info["model"].rstrip("\0")
            info["capabilities"] = self.capabilities
            _LOGGER.debug("Basic info: ok")
            self.info = info
            _LOGGER.debug("Info: ok")

    async def update_temperature(self):
        if self.has_temperature:
            _LOGGER.debug("Fetching temperature")
            sensors = await self.api.temperature_sensors()
            if sensors:
                _LOGGER.debug("temperature updated: %d", len(sensors))
                all_tcs = {}
                for sensor in sensors:
                    all_tcs[sensor["id"]] = {
                        "name": sensor["name"],
                        "fahrenheit": sensor["fahrenheit"],
                        "temperature": (await self.api.temperature(sensor["id"]))[
                            "temperature"
                        ],
                        "attributes": sensor,
                    }
                    self.tcs_name_to_id[sensor["name"]] = sensor["id"]
                self.tcs = all_tcs

    async def update_equipment(self):
        if self.has_equipment:
            _LOGGER.debug("Fetching equipment")
            equipment = await self.api.equipment()
            if equipment:
                _LOGGER.debug("equipment updated: %s", json.dumps(equipment))
                all_equipment = {}
                for device in equipment:
                    all_equipment[device["id"]] = {
                        "name": device["name"],
                        "state": device["on"],
                        "attributes": device,
                    }
                    self.equipment_name_to_id[device["name"]] = device["id"]
                self.equipment = all_equipment

    async def update_timers(self):
        if self.has_timers:
            _LOGGER.debug("Fetching timers")
            timers = await self.api.timers()
            if timers:
                _LOGGER.debug("timers updated: %s", json.dumps(timers))
                all_timers = {}
                for timer in timers:
                    all_timers[timer["id"]] = {
                        "name": timer["name"],
                        "state": timer["enable"],
                        "attributes": timer,
                    }
                self.timers = all_timers

    async def update_macros(self):
        if self.has_macro:
            _LOGGER.debug("Fetching macros")
            macros = await self.api.macros()
            if macros:
                _LOGGER.debug("macros updated: %s", json.dumps(macros))
                all_macros = {}
                for macro in macros:
                    all_macros[macro["id"]] = {
                        "name": macro["name"],
                        "attributes": macro,
                    }
                self.macros = all_macros

    async def update_ph(self):
        if self.has_ph:
            _LOGGER.debug("Fetching phprobes")
            probes = await self.api.phprobes()
            if probes:
                _LOGGER.debug("pH probes updated: %s", json.dumps(probes))
                all_ph = {}
                for probe in probes:
                    attributes = probe
                    ph = await self.api.ph_readings(probe["id"])
                    value = round(ph["value"], 4) if ph["value"] else None

                    all_ph[probe["id"]] = {
                        "name": probe["name"],
                        "value": value,
                        "attributes": attributes,
                    }
                    self.ph_name_to_id[probe["name"]] = probe["id"]
                self.ph = all_ph
                _LOGGER.debug(f"Got {len(all_ph)} pH probes: {all_ph}")

    async def update_lights(self):
        if self.has_lights:
            _LOGGER.debug("Fetching lights")
            lights = await self.api.lights()
            if lights:
                all_light = {}
                for light in lights:
                    for channel in list(light["channels"].keys()):
                        light_id = light["id"]
                        if light["channels"][channel]["manual"]:
                            id = f"{light_id}-{channel}"
                            light_name = light["name"]
                            channel_name = light["channels"][channel]["name"]

                            state = light["channels"][channel]["value"] > 0
                            combined_name = f"{light_name}-{channel_name}"
                            all_light[id] = {
                                "name": combined_name,
                                "channel_id": channel,
                                "light_id": light_id,
                                "value": light["channels"][channel]["value"],
                                "state": state,
                                "attributes": light["channels"][channel],
                            }
                            self.light_name_to_id[combined_name] = id

                self.lights = all_light

    async def update_display(self):
        if self.has_display:
            _LOGGER.debug("Fetching display state")
            state = await self.api.display_state()
            if state:
                self.display = state

    async def update_inlets(self):
        if self.has_ato:
            _LOGGER.debug("Fetching inlets")
            inlets = await self.api.inlets()
            if inlets:
                _LOGGER.debug("inlets updated: %s", json.dumps(inlets))
                all_inlet = {}
                for inlet in inlets:
                    inlet_raw_value = await self.api.inlet(inlet["id"])

                    if inlet_raw_value == 1:
                        inlet_value = True
                    else:
                        inlet_value = False

                    all_inlet[inlet["id"]] = {
                        "name": inlet["name"],
                        "state": inlet_value,
                        "attributes": inlet,
                    }
                    self.inlet_name_to_id[inlet["name"]] = inlet["id"]
                self.inlets = all_inlet

    async def update_pumps(self):
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
                            "name": pump["name"],
                            "time": datetime.fromtimestamp(0),
                            "attributes": {pump["id"]: pump},
                        }
                    else:
                        result[key]["attributes"][pump["id"]] = pump

                    current = await self.api.pump(pump["id"])
                    if (
                        current
                        and "time" in current.keys()
                        and "pump" in current.keys()
                    ):
                        time = datetime.strptime(
                            current["time"], REEFPI_DATETIME_FORMAT
                        )
                        if time > result[key]["time"]:
                            result[key]["time"] = time
                            result[key]["attributes"]["duration"] = current["pump"]
            except Exception as ex:
                _LOGGER.exception(ex)
            self.pumps = result

    async def update_atos(self):
        if self.has_ato:
            atos = await self.api.atos()
            atos = {a["id"]: a for a in atos}
            ato_states = {}
            for id in atos.keys():
                ato_states[id] = {"ts": datetime.fromtimestamp(0), "pump": 0}
                states = await self.api.ato(id)
                ato_state = [s for s in states if s["pump"] != 0]
                if len(ato_state) > 0:
                    ato_states[id] = ato_state[-1]
                    ato_states[id]["ts"] = datetime.strptime(
                        ato_states[id]["time"], REEFPI_DATETIME_FORMAT
                    )
                else:
                    if len(states) > 0:
                        ato_states[id] = states[-1]
                        ato_states[id]["ts"] = datetime.strptime(
                            ato_states[id]["time"], REEFPI_DATETIME_FORMAT
                        )

            self.ato = atos
            self.ato_states = ato_states

    async def _async_update_data(self):
        """Update data via REST API."""
        try:
            if not self.api.is_authenticated():
                _LOGGER.debug("Authenticating")
                await self.api.authenticate(self.username, self.password)
                _LOGGER.debug("Authenticated")

            await self.update_capabilities()
            await self.update_info()
            await self.update_temperature()
            await self.update_equipment()
            await self.update_ph()
            await self.update_pumps()
            await self.update_atos()
            await self.update_inlets()
            await self.update_lights()
            await self.update_display()
            await self.update_macros()
            await self.update_timers()
        except InvalidAuth as error:
            raise ConfigEntryAuthFailed from error
        except CannotConnect as error:
            raise UpdateFailed(error) from error
        return {}

    async def equipment_control(self, id, state):
        await self.api.equipment_control(id, state)
        self.equipment[id]["state"] = state

    async def light_control(self, id, value):
        await self.api.light_update(
            self.lights[id]["light_id"], self.lights[id]["channel_id"], value
        )
        self.lights[id]["value"] = value
        if value > 0:
            self.lights[id]["state"] = True
        else:
            self.lights[id]["state"] = False

    async def ato_update(self, id, enable):
        await self.api.ato_update(id, enable)
        self.ato[id]["enable"] = enable

    async def run_script(self, id):
        await self.api.run_macro(id)

    async def reboot(self):
        await self.api.reboot()

    async def power_off(self):
        await self.api.power_off()

    async def display_switch(self, on: bool):
        await self.api.display_switch(on)
        self.display["on"] = on

    async def display_brightness(self, value: int):
        await self.api.display_brightness(value)
        self.display["brightness"] = value

    async def timer_control(self, id, state):
        await self.api.timer_control(id, state)
        self.timers[id]["state"] = state
