"""MQTT update tracking for reef-pi integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from .const import _LOGGER

if TYPE_CHECKING:
    pass


class ReefPiMQTTTracker:
    """Track MQTT updates and manage polling optimization."""

    def __init__(self, skip_polling_threshold: timedelta = timedelta(minutes=2)):
        """Initialize the MQTT tracker.

        Args:
            skip_polling_threshold: Skip polling if MQTT update is more recent than this
        """
        self.total_messages = 0
        self.last_message_time: datetime | None = None

        self.last_update_by_type: dict[str, datetime] = {}
        self.last_update_by_device: dict[str, dict[str, datetime]] = {}
        self.update_source: dict[str, dict[str, str]] = {}

        self._skip_threshold = skip_polling_threshold

    def record_mqtt_update(
        self, device_type: str, device_id: str, timestamp: datetime | None = None
    ) -> None:
        """Record an MQTT update for a device.

        Args:
            device_type: Type of device (temperature, equipment, ph, etc.)
            device_id: Device ID
            timestamp: Update timestamp (defaults to now in UTC)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        self.total_messages += 1
        self.last_message_time = timestamp

        self.last_update_by_type[device_type] = timestamp

        if device_type not in self.last_update_by_device:
            self.last_update_by_device[device_type] = {}
        self.last_update_by_device[device_type][device_id] = timestamp

        if device_type not in self.update_source:
            self.update_source[device_type] = {}
        self.update_source[device_type][device_id] = "mqtt"

        _LOGGER.debug(
            "MQTT tracker: recorded %s update for device %s", device_type, device_id
        )

    def record_polling_update(
        self, device_type: str, device_id: str, timestamp: datetime | None = None
    ) -> None:
        """Record a polling update for a device.

        Args:
            device_type: Type of device (temperature, equipment, ph, etc.)
            device_id: Device ID
            timestamp: Update timestamp (defaults to now in UTC)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        if device_type not in self.update_source:
            self.update_source[device_type] = {}
        self.update_source[device_type][device_id] = "polling"

    def should_skip_polling(self, device_type: str, device_id: str) -> bool:
        """Check if polling should be skipped due to recent MQTT update.

        Args:
            device_type: Type of device
            device_id: Device ID

        Returns:
            True if device had recent MQTT update and polling should be skipped
        """
        if device_type not in self.last_update_by_device:
            return False

        last_mqtt = self.last_update_by_device[device_type].get(device_id)
        if not last_mqtt:
            return False

        time_since_mqtt = datetime.now(timezone.utc) - last_mqtt
        should_skip = time_since_mqtt < self._skip_threshold

        if should_skip:
            _LOGGER.debug(
                "Skipping polling for %s %s (MQTT update %s ago)",
                device_type,
                device_id,
                time_since_mqtt,
            )

        return should_skip

    def get_update_source(self, device_type: str, device_id: str) -> str | None:
        """Get the last update source for a device.

        Args:
            device_type: Type of device
            device_id: Device ID

        Returns:
            "mqtt", "polling", or None if no update recorded
        """
        return self.update_source.get(device_type, {}).get(device_id)

    def get_last_update_time(
        self, device_type: str, device_id: str | None = None
    ) -> datetime | None:
        """Get the last update time for a device or device type.

        Args:
            device_type: Type of device
            device_id: Device ID (if None, returns last update for any device of this type)

        Returns:
            Datetime of last update or None
        """
        if device_id:
            return self.last_update_by_device.get(device_type, {}).get(device_id)
        return self.last_update_by_type.get(device_type)

    def get_stats(self) -> dict:
        """Get statistics about MQTT updates.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_messages": self.total_messages,
            "last_message_time": (
                self.last_message_time.isoformat() if self.last_message_time else None
            ),
            "device_types_tracked": list(self.last_update_by_type.keys()),
            "last_update_by_type": {
                k: v.isoformat() for k, v in self.last_update_by_type.items()
            },
        }
