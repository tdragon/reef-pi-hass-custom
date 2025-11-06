"""Test MQTT handler for Reef-Pi integration."""

from unittest.mock import MagicMock, Mock

import pytest
from homeassistant.components.mqtt.models import ReceiveMessage

from custom_components.reef_pi.mqtt_handler import ReefPiMQTTHandler
from custom_components.reef_pi.mqtt_name_mapper import ReefPiMQTTNameMapper
from custom_components.reef_pi.mqtt_tracker import ReefPiMQTTTracker


class MockCoordinator:
    """Mock coordinator for testing."""

    def __init__(self):
        self.mqtt_prefix = "reef-pi"
        self.tcs = {"1": {"temperature": 0.0}}
        self.equipment = {"1": {"state": False}}
        self.ph = {"1": {"value": 0.0}}
        self.mqtt_tracker = ReefPiMQTTTracker()
        self.data = {}
        self.async_set_updated_data = Mock()

        # Create mock mapper with test mappings
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.entry_id = "test"
        self.mqtt_name_mapper = ReefPiMQTTNameMapper(mock_hass, mock_entry, "reef-pi")
        # Pre-register test topics
        self.mqtt_name_mapper.topic_to_device["reef-pi/temp_reading"] = (
            "temperature",
            "1",
        )
        self.mqtt_name_mapper.topic_to_device["reef-pi/equipment_heater_state"] = (
            "equipment",
            "1",
        )
        self.mqtt_name_mapper.topic_to_device["reef-pi/ph_ph"] = ("ph", "1")


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def mock_coordinator():
    """Create mock coordinator."""
    return MockCoordinator()


@pytest.fixture
def mqtt_handler(mock_hass, mock_coordinator):
    """Create MQTT handler instance."""
    return ReefPiMQTTHandler(mock_hass, mock_coordinator)


@pytest.mark.asyncio
async def test_mqtt_message_received_temperature(mqtt_handler, mock_coordinator):
    """Test receiving temperature MQTT message."""
    msg = ReceiveMessage(
        topic="reef-pi/temp_reading",
        payload="25.5",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    assert mock_coordinator.tcs["1"]["temperature"] == 25.5
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_message_received_equipment_on(mqtt_handler, mock_coordinator):
    """Test receiving equipment on MQTT message."""
    msg = ReceiveMessage(
        topic="reef-pi/equipment_heater_state",
        payload="1.0",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    assert mock_coordinator.equipment["1"]["state"] is True
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_message_received_equipment_off(mqtt_handler, mock_coordinator):
    """Test receiving equipment off MQTT message."""
    msg = ReceiveMessage(
        topic="reef-pi/equipment_heater_state",
        payload="0.0",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    assert mock_coordinator.equipment["1"]["state"] is False
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_message_received_ph(mqtt_handler, mock_coordinator):
    """Test receiving pH MQTT message."""
    msg = ReceiveMessage(
        topic="reef-pi/ph_ph",
        payload="8.1234",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    assert mock_coordinator.ph["1"]["value"] == 8.1234
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_message_received_ph_rounds_to_4_decimals(
    mqtt_handler, mock_coordinator
):
    """Test pH value is rounded to 4 decimal places."""
    msg = ReceiveMessage(
        topic="reef-pi/ph_ph",
        payload="8.123456789",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    assert mock_coordinator.ph["1"]["value"] == 8.1235


@pytest.mark.asyncio
async def test_mqtt_message_received_unregistered_topic(mqtt_handler, mock_coordinator):
    """Test receiving message for unregistered topic."""
    msg = ReceiveMessage(
        topic="reef-pi/unknown_topic",
        payload="123",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    # Should not update anything
    assert not mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_message_received_invalid_payload(mqtt_handler, mock_coordinator):
    """Test receiving message with invalid payload."""
    msg = ReceiveMessage(
        topic="reef-pi/temp_reading",
        payload="not_a_number",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    # Should not update
    assert mock_coordinator.tcs["1"]["temperature"] == 0.0
    assert not mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_update_device_state_records_in_tracker(mqtt_handler, mock_coordinator):
    """Test that updates are recorded in MQTT tracker."""
    mqtt_handler._update_device_state("temperature", "1", 25.5)

    assert mock_coordinator.mqtt_tracker.get_update_source("temperature", "1") == "mqtt"
    assert mock_coordinator.mqtt_tracker.total_messages == 1


@pytest.mark.asyncio
async def test_update_device_state_unknown_device(mqtt_handler, mock_coordinator):
    """Test updating state for unknown device."""
    mqtt_handler._update_device_state("temperature", "999", 25.5)

    # Should not crash or update
    assert not mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_prefix_custom():
    """Test handler with custom MQTT prefix."""
    hass = MagicMock()
    coordinator = MockCoordinator()
    coordinator.mqtt_prefix = "reef-pi/aquarium"

    # Update mapper prefix and mappings
    coordinator.mqtt_name_mapper.mqtt_prefix = "reef-pi/aquarium"
    coordinator.mqtt_name_mapper.topic_to_device.clear()
    coordinator.mqtt_name_mapper.topic_to_device["reef-pi/aquarium/temp_reading"] = (
        "temperature",
        "1",
    )

    handler = ReefPiMQTTHandler(hass, coordinator)

    msg = ReceiveMessage(
        topic="reef-pi/aquarium/temp_reading",
        payload="26.0",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/aquarium/#",
        timestamp=None,
    )

    handler._mqtt_message_received(msg)

    assert coordinator.tcs["1"]["temperature"] == 26.0
