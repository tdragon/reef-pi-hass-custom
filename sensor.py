"""Platform for reef-pi sensor integration."""
from homeassistant.const import CONF_NAME, TEMP_CELSIUS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (_LOGGER, DOMAIN)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add an temperature entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    sensors = [ReefPiTemperature(id, tcs["name"], coordinator) for id, tcs in coordinator.tcs.items()]
    async_add_entities(sensors)
    _LOGGER.debug("Added %d sensors (%d)", len(sensors), len(coordinator.tcs.items()))


class ReefPiTemperature(CoordinatorEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    @property
    def name(self):
        """Return the name of the sensor """
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_tcs_{self._id}"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def available(self):
        """Return if teperature """
        return self._id in self.api.tcs.keys()

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.api.tcs[self._id]["temperature"]
