"""Platform for reef-pi switch integration."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.switch import SwitchDeviceClass

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add an outlets entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    equipment = [
        ReefPiSwitch(id, outlet["name"], coordinator)
        for id, outlet in coordinator.equipment.items()
    ]
    async_add_entities(equipment)

    ato = [
        ReefPiAtoSwitch(id, ato["name"] + " Enabled", coordinator)
        for id, ato in coordinator.ato.items()
    ]
    async_add_entities(ato)

    timers = [
        ReefPiTimers(id, timer["name"], coordinator)
        for id, timer in coordinator.timers.items()
    ]
    async_add_entities(timers)


class ReefPiTimers(CoordinatorEntity, SwitchEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the timers."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_has_entity_name = True

    @property
    def device_info(self):
        return self.api.device_info

    @property
    def name(self):
        """Return the name of the timer"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_timer_{self._id}"

    @property
    def available(self):
        """Return if teperature"""
        return self._id in self.api.timers.keys()

    @property
    def icon(self):
        if self.available:
            return "mdi:timer" if self.is_on else "mdi:timer-off"
        else:
            return "mdi:exclamation"

    @property
    def is_on(self):
        """Return the state of the timer."""
        return self.api.timers[self._id]["state"]

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        await self.api.timer_control(self._id, True)
        self.schedule_update_ha_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.api.timer_control(self._id, False)
        self.schedule_update_ha_state(True)

    @property
    def extra_state_attributes(self):
        return self.api.timers[self._id]["attributes"]


class ReefPiSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_has_entity_name = True

    @property
    def device_info(self):
        return self.api.device_info

    @property
    def name(self):
        """Return the name of the switch"""
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
        """Return the state of the switch."""
        return self.api.equipment[self._id]["state"]

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        await self.api.equipment_control(self._id, True)
        self.schedule_update_ha_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.api.equipment_control(self._id, False)
        self.schedule_update_ha_state(True)

    @property
    def extra_state_attributes(self):
        return self.api.equipment[self._id]["attributes"]


class ReefPiAtoSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_has_entity_name = True

    @property
    def device_info(self):
        return self.api.device_info

    @property
    def name(self):
        """Return the name of the switch"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_ato_{self._id}_enable"

    @property
    def available(self):
        """Return if teperature"""
        return self._id in self.api.ato.keys()

    @property
    def icon(self):
        if self.available:
            return "mdi:water-boiler" if self.is_on else "mdi:water-boiler-off"
        else:
            return "mdi:water-boiler-alert"

    @property
    def is_on(self):
        """Return the state of the switch."""
        return self.api.ato[self._id]["enable"]

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        await self.api.ato_update(self._id, True)
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.api.ato_update(self._id, False)
        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self):
        return self.api.ato[self._id]
