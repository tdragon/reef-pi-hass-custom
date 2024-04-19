from __future__ import annotations


from homeassistant.components.button import (
    ButtonEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add an buttons entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    base_name = coordinator.info["name"] + ": "
    macros = [
        ReefPiButton(id, base_name + macro["name"], coordinator)
        for id, macro in coordinator.macros.items()
    ]
    async_add_entities(macros)


class ReefPiButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, id, name, coordinator):
        """Initialize the button."""
        super().__init__(coordinator)
        self._id = id
        self._name = name
        self.api = coordinator

    _attr_has_entity_name = True
    _attr_icon = "mdi:script-text-play"

    @property
    def device_info(self):
        return self.api.device_info

    @property
    def name(self):
        """Return the name of the button"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.coordinator.unique_id}_button_{self._id}"

    @property
    def available(self):
        """Return if teperature"""
        return self._id in self.api.macros.keys()

    async def async_press(self) -> None:
        """Async press action."""
        await self.api.run_script(self._id)
