"""Platform for reef-pi sensor integration."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add multiple entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    inlets = [
        ReefPiInlet(id, inlet["name"], coordinator)
        for id, inlet in coordinator.inlets.items()
    ]

    async_add_entities(inlets)


class ReefPiInlet(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the binary sensors."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    _attr_has_entity_name = True
    _attr_icon = "mdi:water-circle"

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_inlets_{self._id}"

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self.api.inlets[self._id]["state"]

    @property
    def available(self):
        """Return if available"""
        return self._id in self.api.inlets.keys()

    @property
    def device_info(self):
        return self.api.device_info

    @property
    def extra_state_attributes(self):
        return self.api.inlets[self._id]["attributes"]
