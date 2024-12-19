from math import ceil

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import _LOGGER, DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add multiple entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    manual_lights = [
        ReefPiLight(id, lights["name"], coordinator)
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

    _attr_has_entity_name = True
    _attr_icon = "mdi:lightbulb-fluorescent-tube"

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_lights_{self._id}"

    @property
    def name(self):
        """Return the name of the light"""
        return self._name

    @property
    def available(self) -> bool:
        """Return if available"""
        return self._id in self.api.lights.keys()

    @property
    def device_info(self):
        return self.api.device_info

    @property
    def extra_state_attributes(self):
        return self.api.lights[self._id]["attributes"]

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.api.lights[self._id]["state"]

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        real_value = int(round(self.api.lights[self._id]["value"] * 2.55))
        return real_value

    @property
    def supported_color_modes(self) -> set[str] | None:
        """Flag supported color modes."""
        return {ColorMode.BRIGHTNESS}

    @property
    def color_mode(self) -> str | None:
        """Return the color mode of the light."""
        return ColorMode.BRIGHTNESS

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        await self.api.light_control(self._id, 0)
        self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            brightness = 255
        percent_brightness = ceil(100 * brightness / 255.0)

        _LOGGER.debug("Setting brightness: %s %s%%", brightness, percent_brightness)

        await self.api.light_control(self._id, percent_brightness)
        self.schedule_update_ha_state()
