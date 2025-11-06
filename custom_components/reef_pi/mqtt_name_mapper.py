"""MQTT topic-to-device mapping with collision detection for reef-pi integration."""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import _LOGGER


class ReefPiMQTTNameMapper:
    """Manage MQTT topic-to-device mappings with collision detection."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize device name using reef-pi's MQTT topic normalization rules.

        Applies the same normalization as reef-pi's SanitizePrometheusMetricName:
        1. Converts to lowercase
        2. Replaces all non-alphanumeric characters (except underscore) with underscore

        Examples:
            "My Pump" -> "my_pump"
            "pH-Sensor" -> "ph_sensor"
            "café" -> "caf_"

        Args:
            name: Original device name from reef-pi API

        Returns:
            Normalized name matching MQTT topic format
        """

        # Convert to lowercase and replace non-ASCII-alphanumeric (except underscore) with underscore
        # Matches reef-pi's regex: [^a-zA-Z0-9_]
        def is_valid_char(c: str) -> bool:
            return c == "_" or ("a" <= c <= "z") or ("0" <= c <= "9")

        return "".join(c if is_valid_char(c) else "_" for c in name.lower())

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, mqtt_prefix: str
    ) -> None:
        """Initialize the topic mapper.

        Args:
            hass: Home Assistant instance
            entry: Config entry for notification ID
            mqtt_prefix: MQTT topic prefix (e.g., "reef-pi")
        """
        self.hass = hass
        self.entry = entry
        self.mqtt_prefix = mqtt_prefix

        # Topic-to-device mapping: topic -> (device_type, device_id)
        self.topic_to_device: dict[str, tuple[str, str]] = {}

        # Track collisions: topic -> [(device_type, device_id), ...]
        self._collisions: dict[str, list[tuple[str, str]]] = {}
        self._notified = False

    def _generate_topic(self, device_type: str, name: str) -> str:
        """Generate MQTT topic for device based on reef-pi's topic patterns.

        Args:
            device_type: Type of device (temperature, ph, equipment, light, ato)
            name: Device name (will be normalized)

        Returns:
            Full MQTT topic string
        """
        normalized_name = self.normalize_name(name)

        if device_type == "temperature":
            return f"{self.mqtt_prefix}/{normalized_name}_reading"
        elif device_type == "ph":
            return f"{self.mqtt_prefix}/ph_{normalized_name}"
        elif device_type == "equipment":
            return f"{self.mqtt_prefix}/equipment_{normalized_name}_state"
        elif device_type == "ato":
            return f"{self.mqtt_prefix}/ato_{normalized_name}_state"
        elif device_type == "light":
            # Light topics include channel, but we don't track those separately
            # This is just for base validation
            return f"{self.mqtt_prefix}/{normalized_name}"
        else:
            # Fallback for unknown types
            return f"{self.mqtt_prefix}/{normalized_name}"

    def add_temperature(self, name: str, device_id: str) -> None:
        """Add temperature sensor to topic mapping."""
        self._add_device("temperature", name, device_id)

    def add_ph(self, name: str, device_id: str) -> None:
        """Add pH probe to topic mapping."""
        self._add_device("ph", name, device_id)

    def add_equipment(self, name: str, device_id: str) -> None:
        """Add equipment to topic mapping."""
        self._add_device("equipment", name, device_id)

    def add_inlet(self, name: str, device_id: str) -> None:
        """Add inlet to topic mapping."""
        self._add_device("inlet", name, device_id)

    def add_light(self, name: str, device_id: str) -> None:
        """Add light to topic mapping."""
        self._add_device("light", name, device_id)

    def add_ato(self, name: str, device_id: str) -> None:
        """Add ATO to topic mapping."""
        self._add_device("ato", name, device_id)

    def _add_device(self, device_type: str, name: str, device_id: str) -> None:
        """Add device to topic mapping, track collisions.

        Args:
            device_type: Type of device (temperature, ph, equipment, inlet, light, ato)
            name: Device name from reef-pi
            device_id: Device ID
        """
        topic = self._generate_topic(device_type, name)
        device = (device_type, device_id)

        # Check if topic already registered
        if topic in self.topic_to_device:
            existing_device = self.topic_to_device[topic]

            # Same device re-registered - idempotent, no action needed
            if existing_device == device:
                return

            # First collision detected
            del self.topic_to_device[topic]
            self._collisions[topic] = [existing_device, device]

            _LOGGER.warning(
                "MQTT topic collision: %s used by multiple devices: %s and %s",
                topic,
                existing_device,
                device,
            )
            return

        # Check if topic already in collisions
        if topic in self._collisions:
            # Check if this device already in collision list
            if device in self._collisions[topic]:
                return  # Already tracked

            # Additional collision
            self._collisions[topic].append(device)
            _LOGGER.warning(
                "MQTT topic collision: %s used by multiple devices: %s",
                topic,
                ", ".join(str(d) for d in self._collisions[topic]),
            )
            return

        # No collision, register topic
        self.topic_to_device[topic] = device

    def clear_all(self) -> None:
        """Clear all mappings and collisions (e.g., before refresh)."""
        self.topic_to_device.clear()
        self._collisions.clear()
        self._notified = False

    def has_collisions(self) -> bool:
        """Check if any collisions were detected."""
        return len(self._collisions) > 0

    def notify_collisions(self) -> None:
        """Create or dismiss persistent notification for MQTT topic collisions."""
        notification_id = f"reef_pi_mqtt_collisions_{self.entry.entry_id}"

        if not self._collisions:
            # No collisions, dismiss any existing notification
            persistent_notification.async_dismiss(self.hass, notification_id)
            return

        # Only notify once per reload
        if self._notified:
            return

        # Build message listing all collisions
        lines = [
            "Multiple devices produce the same MQTT topic. MQTT updates disabled for these devices:",
            "",
        ]

        type_names = {
            "temperature": "Temperature",
            "ph": "pH",
            "equipment": "Equipment",
            "inlet": "Inlet",
            "light": "Light",
            "ato": "ATO",
        }

        for topic, devices in self._collisions.items():
            lines.append(f"**Topic:** `{topic}`")
            for device_type, device_id in devices:
                type_label = type_names.get(device_type, device_type.title())
                lines.append(f"- {type_label} (ID: {device_id})")
            lines.append("")

        lines.append(
            "Please rename devices in reef-pi so they produce unique MQTT topics."
        )
        lines.append("API polling continues to work normally.")

        message = "\n".join(lines)

        persistent_notification.async_create(
            self.hass,
            message,
            title="Reef-Pi MQTT: Topic Collisions",
            notification_id=notification_id,
        )

        self._notified = True
        _LOGGER.info(
            "MQTT topic collision notification created: %d topic(s) affected",
            len(self._collisions),
        )
