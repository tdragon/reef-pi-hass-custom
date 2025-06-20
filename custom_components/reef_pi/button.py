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

    ph_buttons: list[ReefPiPhCalibrationButton] = []
    for probe_id, probe in coordinator.ph.items():
        for mode in ("freshwater", "saltwater"):
            name = f"Calibrate {probe['name']} {mode.title()}"
            ph_buttons.append(
                ReefPiPhCalibrationButton(probe_id, name, mode, coordinator)
            )

    buttons = macros + ph_buttons
    buttons.append(ReefPiRebootButton(coordinator))
    buttons.append(ReefPiPowerOffButton(coordinator))
    async_add_entities(buttons)


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


class ReefPiRebootButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Reboot"
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.api = coordinator

    @property
    def unique_id(self):
        return f"{self.coordinator.unique_id}_reboot"

    @property
    def device_info(self):
        return self.api.device_info

    async def async_press(self) -> None:
        await self.api.reboot()


class ReefPiPowerOffButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Power Off"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.api = coordinator

    @property
    def unique_id(self):
        return f"{self.coordinator.unique_id}_poweroff"

    @property
    def device_info(self):
        return self.api.device_info

    async def async_press(self) -> None:
        await self.api.power_off()


class ReefPiPhCalibrationButton(CoordinatorEntity, ButtonEntity):
    """Button to start a two point pH probe calibration."""

    def __init__(self, probe_id: int, name: str, mode: str, coordinator):
        super().__init__(coordinator)
        self._probe_id = probe_id
        self._name = name
        self._mode = mode
        self.api = coordinator

    _attr_has_entity_name = True
    _attr_icon = "mdi:beaker"

    @property
    def device_info(self):
        return self.api.device_info

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"{self.coordinator.unique_id}_ph_{self._probe_id}_{self._mode}"

    @property
    def available(self):
        return self._probe_id in self.api.ph.keys()

    async def async_press(self) -> None:
        await self.api.calibrate_ph_probe_two_point(self._probe_id, self._mode)
