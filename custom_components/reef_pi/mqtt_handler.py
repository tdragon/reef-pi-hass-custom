"""MQTT handler for reef-pi integration."""

from __future__ import annotations

import re
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

        parsed = self._parse_mqtt_topic(topic)
        if not parsed:
            _LOGGER.debug("Could not parse topic: %s", topic)
            return

        device_type, device_name, metric_type = parsed

        try:
            value = float(payload)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid payload for topic %s: %s", topic, payload)
            return

        self._update_device_state(device_type, device_name, metric_type, value)

    def _update_device_state(
        self, device_type: str, device_name: str, metric_type: str, value: float
    ) -> None:
        """Update device state from MQTT message."""
        updated = False

        if (
            device_type == "temperature"
            and device_name in self.coordinator.tcs_name_to_id
        ):
            device_id = self.coordinator.tcs_name_to_id[device_name]
            if metric_type == "reading" and device_id in self.coordinator.tcs:
                self.coordinator.tcs[device_id]["temperature"] = value
                _LOGGER.debug("Updated temperature %s to %s", device_name, value)
                updated = True

        elif (
            device_type == "equipment"
            and device_name in self.coordinator.equipment_name_to_id
        ):
            device_id = self.coordinator.equipment_name_to_id[device_name]
            if metric_type == "state" and device_id in self.coordinator.equipment:
                state = bool(int(value))
                self.coordinator.equipment[device_id]["state"] = state
                _LOGGER.debug("Updated equipment %s to %s", device_name, state)
                updated = True

        elif device_type == "ph" and device_name in self.coordinator.ph_name_to_id:
            device_id = self.coordinator.ph_name_to_id[device_name]
            if metric_type == "reading" and device_id in self.coordinator.ph:
                self.coordinator.ph[device_id]["value"] = round(value, 4)
                _LOGGER.debug("Updated pH %s to %s", device_name, value)
                updated = True

        if updated:
            self.coordinator.async_set_updated_data(self.coordinator.data)

    def _parse_mqtt_topic(self, topic: str) -> tuple[str, str, str] | None:
        """Parse reef-pi MQTT topic into components.

        Returns: (device_type, device_name, metric_type) or None

        Examples:
            reef-pi/aquarium/Tank_Temp_reading -> ("temperature", "Tank Temp", "reading")
            reef-pi/aquarium/equipment_Heater-state -> ("equipment", "Heater", "state")
        """
        if not topic.startswith(f"{self.mqtt_prefix}/"):
            return None

        topic_without_prefix = topic[len(self.mqtt_prefix) + 1 :]

        equipment_match = re.match(r"equipment_(.+)-state$", topic_without_prefix)
        if equipment_match:
            device_name = equipment_match.group(1).replace("_", " ")
            return ("equipment", device_name, "state")

        sensor_match = re.match(r"(.+)_(reading|heater|cooler)$", topic_without_prefix)
        if sensor_match:
            device_name = sensor_match.group(1).replace("_", " ")
            metric_type = sensor_match.group(2)
            if metric_type == "reading":
                return ("temperature", device_name, metric_type)

        return None
