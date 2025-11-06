"""Test MQTT topic mapper for Reef-Pi integration."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.reef_pi.mqtt_name_mapper import ReefPiMQTTNameMapper


@pytest.mark.asyncio
async def test_normalize_name_lowercase():
    """Test name normalization converts to lowercase."""
    assert ReefPiMQTTNameMapper.normalize_name("MyPump") == "mypump"
    assert ReefPiMQTTNameMapper.normalize_name("HEATER") == "heater"
    assert ReefPiMQTTNameMapper.normalize_name("Tank") == "tank"


@pytest.mark.asyncio
async def test_normalize_name_spaces():
    """Test name normalization replaces spaces with underscores."""
    assert ReefPiMQTTNameMapper.normalize_name("My Pump") == "my_pump"
    assert ReefPiMQTTNameMapper.normalize_name("pH Sensor") == "ph_sensor"
    assert ReefPiMQTTNameMapper.normalize_name("Return  Pump") == "return__pump"


@pytest.mark.asyncio
async def test_normalize_name_special_chars():
    """Test name normalization replaces special characters with underscores."""
    assert ReefPiMQTTNameMapper.normalize_name("pH-Sensor") == "ph_sensor"
    assert ReefPiMQTTNameMapper.normalize_name("café") == "caf_"
    assert ReefPiMQTTNameMapper.normalize_name("pump@123") == "pump_123"
    assert ReefPiMQTTNameMapper.normalize_name("sensor#1") == "sensor_1"


@pytest.mark.asyncio
async def test_normalize_name_underscores_preserved():
    """Test name normalization preserves underscores."""
    assert ReefPiMQTTNameMapper.normalize_name("my_pump") == "my_pump"
    assert ReefPiMQTTNameMapper.normalize_name("ph_sensor_1") == "ph_sensor_1"


@pytest.mark.asyncio
async def test_normalize_name_alphanumeric():
    """Test name normalization preserves alphanumeric characters."""
    assert ReefPiMQTTNameMapper.normalize_name("pump123") == "pump123"
    assert ReefPiMQTTNameMapper.normalize_name("sensor1a2b3c") == "sensor1a2b3c"


@pytest.mark.asyncio
async def test_generate_topic_temperature():
    """Test topic generation for temperature sensors."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")
    topic = mapper._generate_topic("temperature", "Tank Temp")

    assert topic == "reef-pi/tank_temp_reading"


@pytest.mark.asyncio
async def test_generate_topic_ph():
    """Test topic generation for pH probes."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")
    topic = mapper._generate_topic("ph", "Display Tank")

    assert topic == "reef-pi/ph_display_tank"


@pytest.mark.asyncio
async def test_generate_topic_equipment():
    """Test topic generation for equipment."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")
    topic = mapper._generate_topic("equipment", "Main Pump")

    assert topic == "reef-pi/equipment_main_pump_state"


@pytest.mark.asyncio
async def test_add_temperature_no_collision():
    """Test adding temperature sensors without collisions."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Sump", "2")

    assert mapper.topic_to_device["reef-pi/tank_reading"] == ("temperature", "1")
    assert mapper.topic_to_device["reef-pi/sump_reading"] == ("temperature", "2")
    assert not mapper.has_collisions()


@pytest.mark.asyncio
async def test_add_temperature_with_collision():
    """Test adding temperature sensors with topic collision."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")  # Collision - same name

    # Both should be in collisions, not in mapping
    assert "reef-pi/tank_reading" not in mapper.topic_to_device
    assert mapper.has_collisions()
    assert "reef-pi/tank_reading" in mapper._collisions
    assert mapper._collisions["reef-pi/tank_reading"] == [
        ("temperature", "1"),
        ("temperature", "2"),
    ]


@pytest.mark.asyncio
async def test_add_same_device_twice_idempotent():
    """Test adding same device twice is idempotent."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "1")  # Same device

    # Should still be registered normally
    assert mapper.topic_to_device["reef-pi/tank_reading"] == ("temperature", "1")
    assert not mapper.has_collisions()


@pytest.mark.asyncio
async def test_cross_type_collision():
    """Test collision detection works across device types."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    # Temperature sensor named "ph" would produce topic "reef-pi/ph_reading"
    # pH probe named "reading" would produce topic "reef-pi/ph_reading"
    mapper.add_temperature("ph", "1")
    mapper.add_ph("reading", "2")

    # Both produce the same topic!
    assert "reef-pi/ph_reading" not in mapper.topic_to_device
    assert mapper.has_collisions()
    assert mapper._collisions["reef-pi/ph_reading"] == [
        ("temperature", "1"),
        ("ph", "2"),
    ]


@pytest.mark.asyncio
async def test_no_collision_different_topics():
    """Test that different device types with different names don't collide."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_ph("Display", "2")
    mapper.add_equipment("Heater", "3")

    # All should be registered separately (different topics)
    assert mapper.topic_to_device["reef-pi/tank_reading"] == ("temperature", "1")
    assert mapper.topic_to_device["reef-pi/ph_display"] == ("ph", "2")
    assert mapper.topic_to_device["reef-pi/equipment_heater_state"] == (
        "equipment",
        "3",
    )
    assert not mapper.has_collisions()


@pytest.mark.asyncio
async def test_collision_with_three_devices():
    """Test collision with three devices producing same topic."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")
    mapper.add_temperature("Tank", "3")

    assert "reef-pi/tank_reading" not in mapper.topic_to_device
    assert mapper._collisions["reef-pi/tank_reading"] == [
        ("temperature", "1"),
        ("temperature", "2"),
        ("temperature", "3"),
    ]


@pytest.mark.asyncio
async def test_clear_all():
    """Test clearing all mappings and collisions."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")  # Collision
    mapper.add_equipment("Heater", "3")

    assert mapper.has_collisions()
    assert len(mapper.topic_to_device) == 1  # Only heater

    mapper.clear_all()

    assert not mapper.has_collisions()
    assert len(mapper.topic_to_device) == 0


@pytest.mark.asyncio
async def test_notify_collisions_with_no_collisions():
    """Test notification dismissal when no collisions exist."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")

    with patch(
        "custom_components.reef_pi.mqtt_name_mapper.persistent_notification"
    ) as mock_notif:
        mapper.notify_collisions()
        mock_notif.async_dismiss.assert_called_once_with(
            hass, "reef_pi_mqtt_collisions_test_id"
        )
        mock_notif.async_create.assert_not_called()


@pytest.mark.asyncio
async def test_notify_collisions_with_collisions():
    """Test notification creation when collisions exist."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")  # Collision

    with patch(
        "custom_components.reef_pi.mqtt_name_mapper.persistent_notification"
    ) as mock_notif:
        mapper.notify_collisions()
        mock_notif.async_create.assert_called_once()

        # Check notification message contains key info
        call_args = mock_notif.async_create.call_args
        message = call_args[0][1]
        assert "reef-pi/tank_reading" in message
        assert "Temperature" in message
        assert "ID: 1" in message
        assert "ID: 2" in message


@pytest.mark.asyncio
async def test_notify_collisions_multiple_topics():
    """Test notification with collisions across multiple topics."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")
    mapper.add_equipment("Heater", "3")
    mapper.add_equipment("Heater", "4")

    with patch(
        "custom_components.reef_pi.mqtt_name_mapper.persistent_notification"
    ) as mock_notif:
        mapper.notify_collisions()
        mock_notif.async_create.assert_called_once()

        call_args = mock_notif.async_create.call_args
        message = call_args[0][1]
        assert "reef-pi/tank_reading" in message
        assert "reef-pi/equipment_heater_state" in message
        assert "Temperature" in message
        assert "Equipment" in message


@pytest.mark.asyncio
async def test_notify_collisions_only_once():
    """Test that notification is only created once per reload."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")

    with patch(
        "custom_components.reef_pi.mqtt_name_mapper.persistent_notification"
    ) as mock_notif:
        mapper.notify_collisions()
        mapper.notify_collisions()  # Second call

        # Should only be called once
        assert mock_notif.async_create.call_count == 1


@pytest.mark.asyncio
async def test_notify_collisions_resets_after_clear():
    """Test that notification flag resets after clear_all."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")

    with patch(
        "custom_components.reef_pi.mqtt_name_mapper.persistent_notification"
    ) as mock_notif:
        mapper.notify_collisions()
        assert mock_notif.async_create.call_count == 1

        mapper.clear_all()

        # After clear, should be able to notify again
        mapper.add_temperature("Sump", "3")
        mapper.add_temperature("Sump", "4")
        mapper.notify_collisions()
        assert mock_notif.async_create.call_count == 2


@pytest.mark.asyncio
async def test_custom_mqtt_prefix():
    """Test mapper with custom MQTT prefix."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi/aquarium")

    mapper.add_temperature("Tank", "1")
    mapper.add_equipment("Heater", "2")

    assert mapper.topic_to_device["reef-pi/aquarium/tank_reading"] == (
        "temperature",
        "1",
    )
    assert mapper.topic_to_device["reef-pi/aquarium/equipment_heater_state"] == (
        "equipment",
        "2",
    )
