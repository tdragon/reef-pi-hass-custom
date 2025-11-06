"""Platform for reef-pi sensor integration."""

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import DEGREE, EntityCategory, UnitOfTemperature
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import _LOGGER, DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add multiple entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    sensors = [
        ReefPiTemperature(id, tcs["name"], coordinator)
        for id, tcs in coordinator.tcs.items()
    ]
    ph_sensors = [
        ReefPiPh(id, ph["name"], coordinator) for id, ph in coordinator.ph.items()
    ]
    pumps = [
        ReefPiPump(id, pump["name"], coordinator)
        for id, pump in coordinator.pumps.items()
    ]
    atos = [
        ReefPiATO(id, ato["name"] + " Last Run", False, coordinator)
        for id, ato in coordinator.ato.items()
    ] + [
        ReefPiATO(id, ato["name"] + " Duration", True, coordinator)
        for id, ato in coordinator.ato.items()
    ]

    _LOGGER.debug("sensor temperature: %d, pH: %d", len(sensors), len(ph_sensors))
    async_add_entities(sensors)
    async_add_entities(ph_sensors)
    async_add_entities([ReefPiBasicInfo(coordinator)])
    async_add_entities(pumps)
    async_add_entities(atos)

    if coordinator.mqtt_enabled and coordinator.mqtt_tracker:
        diagnostic_sensors = [
            ReefPiMQTTStatusSensor(coordinator),
            ReefPiMQTTMessageCountSensor(coordinator),
            ReefPiMQTTLastUpdateSensor(coordinator, "temperature"),
            ReefPiMQTTLastUpdateSensor(coordinator, "equipment"),
            ReefPiMQTTLastUpdateSensor(coordinator, "ph"),
        ]
        async_add_entities(diagnostic_sensors)


class ReefPiBasicInfo(CoordinatorEntity, SensorEntity):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.api = coordinator

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True
    _attr_icon = "mdi:fishbowl-outline"
    _attr_name = None
    _attr_should_poll: bool = True

    @property
    def device_info(self):
        return self.api.device_info

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
    _attr_has_entity_name = True

    @property
    def device_info(self):
        return self.api.device_info

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
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

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

    _attr_has_entity_name = True
    _attr_icon = "mdi:ph"
    _attr_native_unit_of_measurement = DEGREE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        return self.api.device_info

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_ph_{self._id}"

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
        self.entity_id = "sensor." + slugify(
            f"""{coordinator.info["name"]}_pump_{id}""".lower()
        )

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True

    @property
    def icon(self):
        return "mdi:heat-pump-outline"

    @property
    def device_info(self):
        return self.api.device_info

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
        return self._id in self.api.pumps.keys() and self.api.pumps[self._id][
            "time"
        ] != datetime.fromtimestamp(0)

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

    _attr_has_entity_name = True
    _attr_icon = "mdi:format-color-fill"

    @property
    def device_class(self):
        if not self._show_pump:
            return SensorDeviceClass.TIMESTAMP
        return None

    @property
    def device_info(self):
        return self.api.device_info

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
        return self._id in self.api.ato_states.keys() and self.api.ato_states[self._id][
            "ts"
        ] != datetime.fromtimestamp(0)

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


class ReefPiMQTTStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing MQTT connection status."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:connection"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.api = coordinator

    @property
    def name(self):
        return "MQTT Status"

    @property
    def unique_id(self):
        return f"{self.coordinator.unique_id}_mqtt_status"

    @property
    def native_value(self):
        """Return connection status."""
        if not self.api.mqtt_enabled:
            return "disabled"
        if not self.api.mqtt_handler:
            return "not_configured"
        if self.api.mqtt_tracker and self.api.mqtt_tracker.total_messages > 0:
            return "connected"
        return "no_messages"

    @property
    def extra_state_attributes(self):
        return {
            "mqtt_prefix": self.api.mqtt_prefix,
            "mqtt_enabled": self.api.mqtt_enabled,
        }

    @property
    def device_info(self):
        return self.api.device_info


class ReefPiMQTTMessageCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing total MQTT messages received."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_has_entity_name = True
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.api = coordinator

    @property
    def name(self):
        return "MQTT Messages Received"

    @property
    def unique_id(self):
        return f"{self.coordinator.unique_id}_mqtt_message_count"

    @property
    def native_value(self):
        return self.api.mqtt_tracker.total_messages if self.api.mqtt_tracker else 0

    @property
    def device_info(self):
        return self.api.device_info


class ReefPiMQTTLastUpdateSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing when last MQTT message was received for a device type."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True

    def __init__(self, coordinator, device_type):
        super().__init__(coordinator)
        self._device_type = device_type
        self.api = coordinator

    @property
    def name(self):
        return f"MQTT Last {self._device_type.title()} Update"

    @property
    def unique_id(self):
        return f"{self.coordinator.unique_id}_mqtt_last_{self._device_type}"

    @property
    def native_value(self):
        """Return timestamp of last MQTT message."""
        if self.api.mqtt_tracker:
            return self.api.mqtt_tracker.get_last_update_time(self._device_type)
        return None

    @property
    def device_info(self):
        return self.api.device_info
