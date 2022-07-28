"""Platform for reef-pi sensor integration."""
from homeassistant.const import (
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    DEGREE)

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.typing import StateType

from .const import _LOGGER, DOMAIN, MANUFACTURER

from datetime import datetime

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add multiple entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    base_name = coordinator.info["name"] + ": "
    sensors = [
        ReefPiTemperature(id, base_name + tcs["name"], coordinator)
        for id, tcs in coordinator.tcs.items()
    ]
    ph_sensors = [
        ReefPiPh(id, base_name + ph["name"], coordinator)
        for id, ph in coordinator.ph.items()
    ]
    pumps = [
        ReefPiPump(id, base_name + "pump_" + id, coordinator)
        for id, pump in coordinator.pumps.items()
    ]
    atos = [
        ReefPiATO(id, base_name + ato["name"] + " Last Run", False, coordinator)
        for id, ato in coordinator.ato.items()
    ] + [
        ReefPiATO(id, base_name + ato["name"] + " Duration", True, coordinator)
        for id, ato in coordinator.ato.items()
    ]

    _LOGGER.debug("sensor base name: %s, temperature: %d, pH: %d", base_name, len(sensors), len(ph_sensors))
    async_add_entities(sensors)
    async_add_entities(ph_sensors)
    async_add_entities([ReefPiBaicInfo(coordinator)])
    async_add_entities(pumps)
    async_add_entities(atos)


class ReefPiBaicInfo(CoordinatorEntity, SensorEntity):
    _attr_native_unit_of_measurement = TEMP_CELSIUS

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.api = coordinator

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        info = {
            'identifiers': {
                (DOMAIN, self.coordinator.unique_id)
            },
            'default_name': self.api.default_name,
            'default_manufacturer': MANUFACTURER,
            "default_model" : "Reef PI",
            "configuration_url": self.api.configuration_url
        }
        if self.api.info:
            info['model'] = self.api.info["model"]
            info['sw_version'] = self.api.info["version"]
            info['name'] = self.name
        return info

    @property
    def icon(self):
        return "mdi:fishbowl-outline"

    @property
    def name(self):
        """Return the name of the sensor"""
        if not self.api.info or not "name" in self.api.info:
            return "ReefPiBaicInfo"
        return self.api.info["name"]

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_info"

    @property
    def available(self):
        """Return if teperature"""
        return self.api.info and "name" in self.api.info

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.api.info["cpu_temperature"]

    @property
    def extra_state_attributes(self):
        if self.api.info:
            return self.api.info
        return {}


class ReefPiTemperature(CoordinatorEntity, SensorEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        return {
            'identifiers': {
                (DOMAIN, self.coordinator.unique_id)
            }}

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_tcs_{self._id}"

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        if self.available and self.api.tcs[self._id]["fahrenheit"]:
            return TEMP_FAHRENHEIT
        return TEMP_CELSIUS

    @property
    def available(self):
        """Return if available"""
        return self._id in self.api.tcs.keys()

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.api.tcs[self._id]["temperature"]

    @property
    def extra_state_attributes(self):
        return self.api.tcs[self._id]["attributes"]

class ReefPiPh(CoordinatorEntity, SensorEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    @property
    def device_info(self):
        return {
            'identifiers': {
                (DOMAIN, self.coordinator.unique_id)
            }}

    @property
    def icon(self):
        return "mdi:ph"

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_ph_{self._id}"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return DEGREE

    @property
    def available(self):
        """Return if available"""
        return self._id in self.api.ph.keys() and self.api.ph[self._id]["value"]

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.api.ph[self._id]["value"]

    @property
    def extra_state_attributes(self):
        return self.api.ph[self._id]["attributes"]

class ReefPiPump(CoordinatorEntity, SensorEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def icon(self):
        return "mdi:heat-pump-outline"

    @property
    def device_info(self):
        return {
            'identifiers': {
                (DOMAIN, self.coordinator.unique_id)
            }}

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_pump_{self._id}"

    @property
    def available(self):
        """Return if available"""
        return self._id in self.api.pumps.keys() and self.api.pumps[self._id]["time"] != datetime.fromtimestamp(0)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.api.pumps[self._id]["time"].isoformat()

    @property
    def extra_state_attributes(self):
        return self.api.pumps[self._id]["attributes"]

class ReefPiATO(CoordinatorEntity, SensorEntity):
    def __init__(self, id, name, show_pump, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self._show_pump = show_pump
        self.api = coordinator

    @property
    def device_class(self):
        if not self._show_pump:
            return SensorDeviceClass.TIMESTAMP
        return None

    @property
    def device_info(self):
        return {
            'identifiers': {
                (DOMAIN, self.coordinator.unique_id)
            }}

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        if self._show_pump:
            return f"{self.coordinator.unique_id}_ato_{self._id}_duration"
        else:
            return f"{self.coordinator.unique_id}_ato_{self._id}_last_run"


    @property
    def available(self):
        """Return if available"""
        return self._id in self.api.ato_states.keys() and self.api.ato_states[self._id]["ts"] != datetime.fromtimestamp(0)

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._show_pump:
            return self.api.ato_states[self._id]["pump"]
        else:
            return self.api.ato_states[self._id]["ts"].isoformat()

    @property
    def extra_state_attributes(self):
        return self.api.ato_states[self._id]

    @property
    def icon(self):
        return "mdi:format-color-fill"

