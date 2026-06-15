"""Test MQTT topic mapper for Reef-Pi integration."""

from unittest.mock import MagicMock, patch

import pytest
import respx
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN, ReefPiDataUpdateCoordinator
from custom_components.reef_pi.mqtt_name_mapper import ReefPiMQTTNameMapper

from . import async_api_mock


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
async def test_add_ato_state_maps_to_inlet():
    """Test ATO state topic is registered against the inlet id."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_ato_state("Test ATO", "2")

    # Topic is generated from the ATO name, but device is stored as the inlet
    assert mapper.topic_to_device["reef-pi/ato_test_ato_state"] == ("inlet", "2")
    # Topic must match what the handler computes via _generate_topic("ato", ...)
    assert mapper._generate_topic("ato", "Test ATO") == "reef-pi/ato_test_ato_state"
    assert not mapper.has_collisions()


@pytest.mark.asyncio
async def test_add_ato_state_name_normalization():
    """Test ATO state topic uses normalized name."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_ato_state("My-ATO", "5")

    assert mapper.topic_to_device["reef-pi/ato_my_ato_state"] == ("inlet", "5")
    assert not mapper.has_collisions()


@pytest.mark.asyncio
async def test_add_ato_state_shared_inlet_no_collision():
    """Test two ATOs (different names) sharing one inlet do not collide."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_ato_state("ATO One", "2")
    mapper.add_ato_state("ATO Two", "2")

    # Different ATO names produce different topics, both pointing at the inlet
    assert mapper.topic_to_device["reef-pi/ato_ato_one_state"] == ("inlet", "2")
    assert mapper.topic_to_device["reef-pi/ato_ato_two_state"] == ("inlet", "2")
    assert not mapper.has_collisions()


@pytest.mark.asyncio
async def test_add_ato_state_idempotent():
    """Test re-registering the same ATO state mapping is idempotent."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_ato_state("Test ATO", "2")
    mapper.add_ato_state("Test ATO", "2")

    assert mapper.topic_to_device["reef-pi/ato_test_ato_state"] == ("inlet", "2")
    assert not mapper.has_collisions()


@pytest.mark.asyncio
async def test_add_ato_state_same_name_collision():
    """Test two ATOs with the same name but different inlets collide."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_ato_state("Test ATO", "2")
    mapper.add_ato_state("Test ATO", "3")  # Same topic, different inlet

    # Collision detection fires through the topic_type path - topic disabled
    assert "reef-pi/ato_test_ato_state" not in mapper.topic_to_device
    assert mapper.has_collisions()
    assert mapper._collisions["reef-pi/ato_test_ato_state"] == [
        ("inlet", "2"),
        ("inlet", "3"),
    ]


async def _build_coordinator(hass):
    """Build an authenticated coordinator wired for update_atos tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Reef Pi",
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
        },
    )
    entry.add_to_hass(hass)
    coordinator = ReefPiDataUpdateCoordinator(
        hass, async_get_clientsession(hass), entry
    )
    await coordinator.api.authenticate(
        async_api_mock.REEF_MOCK_USER, async_api_mock.REEF_MOCK_PASSWORD
    )
    coordinator.has_ato = True
    return coordinator


async def test_update_atos_registers_ato_state(hass):
    """Test update_atos registers the ATO state topic against its inlet id."""
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_signin(mock)
        async_api_mock.mock_atos(mock)
        coordinator = await _build_coordinator(hass)

        await coordinator.update_atos()

        assert coordinator.mqtt_name_mapper.topic_to_device[
            "reef-pi/ato_test_ato_state"
        ] == ("inlet", "2")


async def test_update_atos_skips_macro_ato(hass):
    """Test update_atos does not register a macro-based ATO with empty inlet."""
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_signin(mock)
        mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/atos").respond(
            200,
            json=[{"id": "1", "name": "Macro ATO", "inlet": "", "is_macro": True}],
        )
        mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/atos/1/usage").respond(
            200, json={}
        )
        coordinator = await _build_coordinator(hass)

        await coordinator.update_atos()

        assert coordinator.mqtt_name_mapper.topic_to_device == {}
        assert not coordinator.mqtt_name_mapper.has_collisions()


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
