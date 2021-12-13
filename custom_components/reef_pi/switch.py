"""Platform for reef-pi switch integration."""
from homeassistant.const import CONF_NAME
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.switch import SwitchDeviceClass


from .const import _LOGGER, DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add an outlets entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    base_name = coordinator.info["name"] + ": "
    equipment = [
        ReefPiSwitch(id, base_name + tcs["name"], coordinator)
        for id, tcs in coordinator.equipment.items()
    ]
    async_add_entities(equipment)


class ReefPiSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    _attr_device_class = SwitchDeviceClass.OUTLET

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
        return f"{self.coordinator.unique_id}_switch_{self._id}"

    @property
    def available(self):
        """Return if teperature"""
        return self._id in self.api.equipment.keys()

    @property
    def icon(self):
        if self.available:
            return "mdi:power-plug" if self.is_on else "mdi:power-plug-off"
        else:
            return "mdi:exclamation"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self.api.equipment[self._id]["on"]

    def turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self.api.equipment_control(self._id, True)
        self.schedule_update_ha_state(True)

    def turn_off(self, **kwargs) -> None:
        """Turn the entity on."""
        self.api.equipment_control(self._id, False)
        self.schedule_update_ha_state(True)

    @property
    def extra_state_attributes(self):
        return {"id": self._id, "outlet": self.api.equipment[self._id]["outlet"]}
