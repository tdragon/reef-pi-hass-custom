"""MQTT handler for reef-pi integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components import mqtt
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.core import HomeAssistant, callback

from .const import _LOGGER

if TYPE_CHECKING:
    from . import ReefPiDataUpdateCoordinator


class ReefPiMQTTHandler:
    """Handle MQTT subscriptions and messages for reef-pi."""

    def __init__(self, hass: HomeAssistant, coordinator: ReefPiDataUpdateCoordinator):
        self.hass = hass
        self.coordinator = coordinator
        self.mqtt_prefix = coordinator.mqtt_prefix

    async def async_subscribe(self) -> None:
        """Subscribe to reef-pi MQTT topics for real-time updates."""
        try:
            await mqtt.async_wait_for_mqtt_client(self.hass)
            topic = f"{self.mqtt_prefix}/#"
            _LOGGER.info("Subscribing to MQTT topic: %s", topic)
            await mqtt.async_subscribe(
                self.hass, topic, self._mqtt_message_received, qos=1
            )
        except Exception as ex:
            _LOGGER.exception("Failed to setup MQTT subscriptions: %s", ex)

    @callback
    def _mqtt_message_received(self, msg: ReceiveMessage) -> None:
        """Handle received MQTT message from reef-pi."""
        topic = msg.topic
        payload = msg.payload

        _LOGGER.debug("MQTT message received: %s = %s", topic, payload)

        # Look up device from topic mapping
        mapper = self.coordinator.mqtt_name_mapper
        device = mapper.topic_to_device.get(topic)

        if not device:
            _LOGGER.debug("Topic not registered: %s", topic)
            return

        device_type, device_id = device

        # Parse payload as float
        try:
            value = float(payload)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid payload for topic %s: %s", topic, payload)
            return

        self._update_device_state(device_type, device_id, value)

    def _update_device_state(
        self, device_type: str, device_id: str, value: float
    ) -> None:
        """Update device state from MQTT message.

        Args:
            device_type: Device type (temperature, ph, equipment, etc.)
            device_id: Device ID
            value: Numeric value from MQTT message
        """
        updated = False

        if device_type == "temperature":
            if device_id in self.coordinator.tcs:
                self.coordinator.tcs[device_id]["temperature"] = value
                _LOGGER.debug("Updated temperature %s to %s", device_id, value)
                updated = True

        elif device_type == "ph":
            if device_id in self.coordinator.ph:
                self.coordinator.ph[device_id]["value"] = round(value, 4)
                _LOGGER.debug("Updated pH %s to %s", device_id, value)
                updated = True

        elif device_type == "equipment":
            if device_id in self.coordinator.equipment:
                state = bool(int(value))
                self.coordinator.equipment[device_id]["state"] = state
                _LOGGER.debug("Updated equipment %s to %s", device_id, state)
                updated = True

        if updated:
            if self.coordinator.mqtt_tracker:
                self.coordinator.mqtt_tracker.record_mqtt_update(device_type, device_id)
            self.coordinator.async_set_updated_data(self.coordinator.data)
