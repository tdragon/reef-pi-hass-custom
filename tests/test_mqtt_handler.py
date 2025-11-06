"""Test MQTT handler for Reef-Pi integration."""

from unittest.mock import MagicMock, Mock

import pytest
from homeassistant.components.mqtt.models import ReceiveMessage

from custom_components.reef_pi.mqtt_handler import ReefPiMQTTHandler
from custom_components.reef_pi.mqtt_tracker import ReefPiMQTTTracker


class MockCoordinator:
    """Mock coordinator for testing."""

    def __init__(self):
        self.mqtt_prefix = "reef-pi"
        self.tcs = {"1": {"temperature": 0.0}}
        self.equipment = {"1": {"state": False}}
        self.ph = {"1": {"value": 0.0}}
        self.tcs_name_to_id = {"temp": "1"}
        self.equipment_name_to_id = {"heater": "1"}
        self.ph_name_to_id = {"ph": "1"}
        self.mqtt_tracker = ReefPiMQTTTracker()
        self.data = {}
        self.async_set_updated_data = Mock()


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
async def test_parse_equipment_topic(mqtt_handler):
    """Test parsing equipment topic."""
    topic = "reef-pi/equipment_heater_state"

    result = mqtt_handler._parse_mqtt_topic(topic)

    assert result == ("equipment", "heater", "state")


@pytest.mark.asyncio
async def test_parse_equipment_topic_with_underscores(mqtt_handler):
    """Test parsing equipment topic with underscores in device name."""
    topic = "reef-pi/equipment_old_light_state"

    result = mqtt_handler._parse_mqtt_topic(topic)

    assert result == ("equipment", "old light", "state")


@pytest.mark.asyncio
async def test_parse_temperature_topic(mqtt_handler):
    """Test parsing temperature topic."""
    topic = "reef-pi/temp_reading"

    result = mqtt_handler._parse_mqtt_topic(topic)

    assert result == ("reading", "temp", "reading")


@pytest.mark.asyncio
async def test_parse_temperature_topic_with_underscores(mqtt_handler):
    """Test parsing temperature topic with underscores in device name."""
    topic = "reef-pi/water_temp_reading"

    result = mqtt_handler._parse_mqtt_topic(topic)

    assert result == ("reading", "water temp", "reading")


@pytest.mark.asyncio
async def test_parse_ph_topic(mqtt_handler):
    """Test parsing pH topic (parsed as reading, differentiated by name)."""
    topic = "reef-pi/ph_reading"

    result = mqtt_handler._parse_mqtt_topic(topic)

    # pH and temperature topics both use "reading" type and are differentiated by device name
    assert result == ("reading", "ph", "reading")


@pytest.mark.asyncio
async def test_parse_topic_wrong_prefix(mqtt_handler):
    """Test parsing topic with wrong prefix."""
    topic = "wrong-prefix/equipment_heater_state"

    result = mqtt_handler._parse_mqtt_topic(topic)

    assert result is None


@pytest.mark.asyncio
async def test_parse_topic_invalid_format(mqtt_handler):
    """Test parsing topic with invalid format."""
    topic = "reef-pi/invalid_topic"

    result = mqtt_handler._parse_mqtt_topic(topic)

    assert result is None


@pytest.mark.asyncio
async def test_parse_topic_custom_prefix():
    """Test parsing topic with custom prefix."""
    hass = MagicMock()
    coordinator = MockCoordinator()
    coordinator.mqtt_prefix = "reef-pi/aquarium"
    handler = ReefPiMQTTHandler(hass, coordinator)

    topic = "reef-pi/aquarium/equipment_heater_state"

    result = handler._parse_mqtt_topic(topic)

    assert result == ("equipment", "heater", "state")


@pytest.mark.asyncio
async def test_update_temperature_state(mqtt_handler, mock_coordinator):
    """Test updating temperature state."""
    mqtt_handler._update_device_state("reading", "temp", "reading", 25.5)

    assert mock_coordinator.tcs["1"]["temperature"] == 25.5
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_update_temperature_state_case_insensitive(
    mqtt_handler, mock_coordinator
):
    """Test updating temperature state with case-insensitive matching."""
    mock_coordinator.tcs_name_to_id = {"temp": "1"}

    mqtt_handler._update_device_state("reading", "Temp", "reading", 26.0)

    assert mock_coordinator.tcs["1"]["temperature"] == 26.0


@pytest.mark.asyncio
async def test_update_temperature_state_unknown_device(mqtt_handler, mock_coordinator):
    """Test updating temperature state for unknown device."""
    mqtt_handler._update_device_state("reading", "unknown", "reading", 25.5)

    # Should not update or crash
    assert mock_coordinator.tcs["1"]["temperature"] == 0.0
    assert not mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_update_equipment_state_on(mqtt_handler, mock_coordinator):
    """Test updating equipment state to on."""
    mqtt_handler._update_device_state("equipment", "heater", "state", 1.0)

    assert mock_coordinator.equipment["1"]["state"] is True
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_update_equipment_state_off(mqtt_handler, mock_coordinator):
    """Test updating equipment state to off."""
    mqtt_handler._update_device_state("equipment", "heater", "state", 0.0)

    assert mock_coordinator.equipment["1"]["state"] is False
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_update_equipment_state_case_insensitive(mqtt_handler, mock_coordinator):
    """Test updating equipment state with case-insensitive matching."""
    mock_coordinator.equipment_name_to_id = {"heater": "1"}

    mqtt_handler._update_device_state("equipment", "Heater", "state", 1.0)

    assert mock_coordinator.equipment["1"]["state"] is True


@pytest.mark.asyncio
async def test_update_ph_state(mqtt_handler, mock_coordinator):
    """Test updating pH state."""
    mqtt_handler._update_device_state("reading", "ph", "reading", 8.1234)

    assert mock_coordinator.ph["1"]["value"] == 8.1234
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_update_ph_state_rounds_to_4_decimals(mqtt_handler, mock_coordinator):
    """Test updating pH state rounds to 4 decimal places."""
    mqtt_handler._update_device_state("reading", "ph", "reading", 8.123456789)

    assert mock_coordinator.ph["1"]["value"] == 8.1235


@pytest.mark.asyncio
async def test_update_state_records_in_tracker(mqtt_handler, mock_coordinator):
    """Test that updates are recorded in MQTT tracker."""
    mqtt_handler._update_device_state("reading", "temp", "reading", 25.5)

    assert mock_coordinator.mqtt_tracker.get_update_source("temperature", "1") == "mqtt"
    assert mock_coordinator.mqtt_tracker.total_messages == 1


@pytest.mark.asyncio
async def test_mqtt_message_received_valid(mqtt_handler, mock_coordinator):
    """Test receiving valid MQTT message."""
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


@pytest.mark.asyncio
async def test_mqtt_message_received_invalid_payload(mqtt_handler, mock_coordinator):
    """Test receiving MQTT message with invalid payload."""
    msg = ReceiveMessage(
        topic="reef-pi/equipment_heater_state",
        payload="invalid",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    # Should not crash or update state
    assert mock_coordinator.equipment["1"]["state"] is False
    assert not mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_message_received_unparseable_topic(mqtt_handler, mock_coordinator):
    """Test receiving MQTT message with unparseable topic."""
    msg = ReceiveMessage(
        topic="reef-pi/invalid_topic",
        payload="1.0",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    # Should not crash
    assert not mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_message_received_temperature_update(mqtt_handler, mock_coordinator):
    """Test receiving temperature MQTT message."""
    msg = ReceiveMessage(
        topic="reef-pi/temp_reading",
        payload="25.13",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    assert mock_coordinator.tcs["1"]["temperature"] == 25.13
    assert mock_coordinator.async_set_updated_data.called


@pytest.mark.asyncio
async def test_mqtt_message_received_ph_update(mqtt_handler, mock_coordinator):
    """Test receiving pH MQTT message."""
    msg = ReceiveMessage(
        topic="reef-pi/ph_reading",
        payload="8.234",
        qos=0,
        retain=False,
        subscribed_topic="reef-pi/#",
        timestamp=None,
    )

    mqtt_handler._mqtt_message_received(msg)

    assert mock_coordinator.ph["1"]["value"] == 8.234
