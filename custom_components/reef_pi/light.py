from math import ceil
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)

from .const import _LOGGER, DOMAIN, MANUFACTURER

from datetime import datetime

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add multiple entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    base_name = coordinator.info["name"] + ": "
    manual_lights = [
        ReefPiLight(id, base_name + lights["name"], coordinator)
        for id, lights in coordinator.lights.items()
    ]

    async_add_entities(manual_lights)

class ReefPiLight(CoordinatorEntity, LightEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the lights."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_lights_{self._id}"

    @property
    def name(self):
        """Return the name of the light"""
        return self._name

    @property
    def available(self):
        """Return if available"""
        return self._id in self.api.lights.keys()

    @property
    def device_info(self):
        return {
            'identifiers': {
                (DOMAIN, self.coordinator.unique_id)
            }}

    @property
    def extra_state_attributes(self):
        return self.api.lights[self._id]["attributes"]

    @property
    def icon(self):
        return "mdi:lightbulb-fluorescent-tube"

    @property
    def is_on(self):
        """Return true if light is on."""
        return self.api.lights[self._id]["state"]

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        real_value = round(self.api.lights[self._id]["value"] * 2.55)
        return real_value

    @property
    def supported_features(self):
        """Return the supported features."""
        return SUPPORT_BRIGHTNESS

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        await self.api.light_control(self._id, 0)
        self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        brightness = kwargs[ATTR_BRIGHTNESS]
        percent_brightness = ceil(100 * brightness / 255.0)

        _LOGGER.debug("Setting brightness: %s %s%%", brightness, percent_brightness)

        await self.api.light_control(self._id, percent_brightness)
        self.schedule_update_ha_state()