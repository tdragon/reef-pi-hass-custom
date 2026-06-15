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

        # Staging buffers used during a refresh cycle. While a refresh is in progress
        # (_building is not None), registrations are written here and only swapped into
        # the live maps on commit_refresh(), so a transient API failure leaves the last
        # known-good mappings intact.
        self._building: dict[str, tuple[str, str]] | None = None
        self._building_collisions: dict[str, list[tuple[str, str]]] = {}

        # Collisions already surfaced via persistent notification, keyed by a signature
        # that includes the colliding devices (not just the topic). A persisting
        # collision is not re-notified every refresh, while a changed collision set
        # (different topics OR different devices on a topic) triggers a fresh
        # notification.
        self._notified_signature: dict[str, tuple[str, ...]] = {}

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

    def add_light(self, name: str, device_id: str) -> None:
        """Add light to topic mapping."""
        self._add_device("light", name, device_id)

    def add_ato_state(self, ato_name: str, inlet_id: str) -> None:
        """Map an ATO's state topic to its inlet device.

        reef-pi publishes the float-switch reading on the ATO's ``_state`` topic,
        so the topic is generated from the ATO name but stored against the inlet id
        (the device the inlet binary_sensor reads).

        Args:
            ato_name: ATO name from reef-pi (used to build the ``ato_<name>_state`` topic)
            inlet_id: Inlet device ID referenced by the ATO's ``inlet`` field
        """
        self._add_device("inlet", ato_name, inlet_id, topic_type="ato")

    def _add_device(
        self,
        device_type: str,
        name: str,
        device_id: str,
        topic_type: str | None = None,
    ) -> None:
        """Add device to topic mapping, track collisions.

        Args:
            device_type: Type of device the message updates (temperature, ph, equipment,
                inlet, light)
            name: Device name from reef-pi
            device_id: Device ID
            topic_type: Topic pattern to use when it differs from device_type
                (e.g. ATO state topics map to inlet devices)
        """
        topic = self._generate_topic(topic_type or device_type, name)
        device = (device_type, device_id)

        # Write into the staging buffer during a refresh, otherwise into the live maps
        # directly (e.g. ad-hoc registrations outside a poll cycle).
        if self._building is not None:
            mapping = self._building
            collisions = self._building_collisions
        else:
            mapping = self.topic_to_device
            collisions = self._collisions

        # Check if topic already registered
        if topic in mapping:
            existing_device = mapping[topic]

            # Same device re-registered - idempotent, no action needed
            if existing_device == device:
                return

            # First collision detected
            del mapping[topic]
            collisions[topic] = [existing_device, device]

            _LOGGER.warning(
                "MQTT topic collision: %s used by multiple devices: %s and %s",
                topic,
                existing_device,
                device,
            )
            return

        # Check if topic already in collisions
        if topic in collisions:
            # Check if this device already in collision list
            if device in collisions[topic]:
                return  # Already tracked

            # Additional collision
            collisions[topic].append(device)
            _LOGGER.warning(
                "MQTT topic collision: %s used by multiple devices: %s",
                topic,
                ", ".join(str(d) for d in collisions[topic]),
            )
            return

        # No collision, register topic
        mapping[topic] = device

    def begin_refresh(self) -> None:
        """Start a fresh staging buffer for a poll cycle without touching live maps.

        Registrations issued until commit_refresh() are accumulated in a staging buffer.
        The live topic mappings are left untouched so a transient API failure mid-cycle
        (commit never reached) preserves the last known-good mappings, keeping MQTT
        updates working. A successful refresh atomically replaces the live maps.
        """
        self._building = {}
        self._building_collisions = {}

    def commit_refresh(self) -> None:
        """Merge the staging buffer into the live maps after a good refresh.

        Merge (not replace) so a subsystem whose endpoint soft-failed this cycle
        (returned an empty {}/[] without raising, e.g. the known-flaky pH endpoint)
        keeps its previously committed topics instead of losing real-time MQTT updates
        until the next fully-successful poll. Staging is still rebuilt fresh each cycle,
        so a changed registration (e.g. an ATO repointed to a new inlet) overwrites the
        live entry without a false self-collision.

        Note: a device genuinely deleted in reef-pi leaves a stale topic mapping until
        reload. This is harmless: the MQTT handler guards every branch on the device id
        existing in the coordinator's dicts and no-ops for unknown ids.

        Mutations are single synchronous statements on the event loop, so the MQTT
        callback (which reads topic_to_device) never observes a torn state.
        """
        if self._building is None:
            return

        # Successful (re)registrations overwrite the live entry and clear any prior
        # collision on that exact topic.
        for topic, device in self._building.items():
            self.topic_to_device[topic] = device
            self._collisions.pop(topic, None)

        # Genuine same-cycle collisions disable the topic for real-time updates.
        for topic, devices in self._building_collisions.items():
            self._collisions[topic] = devices
            self.topic_to_device.pop(topic, None)

        self._building = None
        self._building_collisions = {}

    def clear_all(self) -> None:
        """Clear all mappings, collisions and notification state (e.g., on reload)."""
        self.topic_to_device.clear()
        self._collisions.clear()
        self._building = None
        self._building_collisions = {}
        self._notified_signature.clear()

    def has_collisions(self) -> bool:
        """Check if any collisions were detected."""
        return len(self._collisions) > 0

    def notify_collisions(self) -> None:
        """Create or dismiss persistent notification for MQTT topic collisions."""
        notification_id = f"reef_pi_mqtt_collisions_{self.entry.entry_id}"

        if not self._collisions:
            # No collisions, dismiss any existing notification and reset state so a
            # future collision triggers a fresh notification.
            persistent_notification.async_dismiss(self.hass, notification_id)
            self._notified_signature.clear()
            return

        # Signature includes the colliding devices, not just the topic, so a changed
        # device set on a stable topic still triggers a rewrite. Skip re-notifying only
        # when the full signature is unchanged (avoids spamming on every poll).
        current_signature = {
            topic: tuple(sorted(str(d) for d in devices))
            for topic, devices in self._collisions.items()
        }
        if current_signature == self._notified_signature:
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

        self._notified_signature = current_signature
        _LOGGER.info(
            "MQTT topic collision notification created: %d topic(s) affected",
            len(self._collisions),
        )
