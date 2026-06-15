"""Test MQTT topic mapper for Reef-Pi integration."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed
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
async def test_begin_refresh_stages_keeps_live_and_notified_state():
    """Test begin_refresh stages new writes while preserving live maps + notified state."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")  # Collision
    with patch("custom_components.reef_pi.mqtt_name_mapper.persistent_notification"):
        mapper.notify_collisions()

    assert mapper.has_collisions()
    assert mapper._notified_signature == {
        "reef-pi/tank_reading": ("('temperature', '1')", "('temperature', '2')")
    }

    mapper.begin_refresh()

    # Live maps stay intact during a refresh; staging buffer is empty; notified state
    # preserved so a persisting collision is not re-notified.
    assert mapper.has_collisions()
    assert mapper._building == {}
    assert mapper._notified_signature == {
        "reef-pi/tank_reading": ("('temperature', '1')", "('temperature', '2')")
    }


@pytest.mark.asyncio
async def test_ato_repoint_across_refresh_no_false_collision():
    """An ATO repointed to a new inlet keeps real-time updates (no stale collision).

    Reproduces the codex finding: without a per-refresh rebuild, re-registering the
    unchanged ``ato_<name>_state`` topic with a new inlet id collides with the stale
    copy and silently disables the mapping. begin_refresh fixes this.
    """
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    # Refresh 1: ATO points at inlet "2"
    mapper.begin_refresh()
    mapper.add_ato_state("Test ATO", "2")
    mapper.commit_refresh()
    assert mapper.topic_to_device["reef-pi/ato_test_ato_state"] == ("inlet", "2")
    assert not mapper.has_collisions()

    # Refresh 2: ATO repointed to inlet "3" (same ATO name, same topic)
    mapper.begin_refresh()
    mapper.add_ato_state("Test ATO", "3")
    mapper.commit_refresh()

    # Topic now maps to the NEW inlet with no collision -> updates stay enabled
    assert mapper.topic_to_device["reef-pi/ato_test_ato_state"] == ("inlet", "3")
    assert not mapper.has_collisions()


@pytest.mark.asyncio
async def test_same_cycle_collision_still_detected_after_refresh():
    """Two different devices sharing a topic in one cycle still collide."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    mapper.begin_refresh()
    mapper.add_temperature("Tank", "1")
    mapper.add_temperature("Tank", "2")  # Genuine same-cycle collision
    mapper.commit_refresh()

    assert "reef-pi/tank_reading" not in mapper.topic_to_device
    assert mapper.has_collisions()
    assert mapper._collisions["reef-pi/tank_reading"] == [
        ("temperature", "1"),
        ("temperature", "2"),
    ]


@pytest.mark.asyncio
async def test_collision_detection_is_eventually_consistent_across_refreshes():
    """Collision detection is best-effort and eventually-consistent (accepted limitation).

    Collisions are computed only over each cycle's staged registrations. When a colliding
    subsystem soft-fails (its REST endpoint returns {}/[] without raising) so only one side
    is re-staged, the previously-detected collision is transiently cleared for that cycle.
    It is re-detected and self-heals on the next refresh where both colliding subsystems
    succeed and stage the same topic together. This documents that accepted transient
    staleness; it only affects the best-effort warning, never normal device state updates.
    """
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    topic = "reef-pi/ph_reading"

    # Cycle 1: two different device types normalize to the same topic -> collision.
    mapper.begin_refresh()
    mapper.add_temperature("ph", "temp1")  # -> reef-pi/ph_reading
    mapper.add_ph("reading", "ph1")  # -> reef-pi/ph_reading
    mapper.commit_refresh()

    assert topic not in mapper.topic_to_device
    assert mapper.has_collisions()
    assert mapper._collisions[topic] == [("temperature", "temp1"), ("ph", "ph1")]

    # Cycle 2: the colliding pH side soft-fails, so only the temperature side re-stages.
    # The collision is transiently cleared and the topic maps to the surviving device.
    mapper.begin_refresh()
    mapper.add_temperature("ph", "temp1")
    mapper.commit_refresh()

    assert mapper.topic_to_device[topic] == ("temperature", "temp1")
    assert not mapper.has_collisions()

    # Cycle 3: both subsystems succeed again -> collision is re-detected (self-healing).
    mapper.begin_refresh()
    mapper.add_temperature("ph", "temp1")
    mapper.add_ph("reading", "ph1")
    mapper.commit_refresh()

    assert topic not in mapper.topic_to_device
    assert mapper.has_collisions()
    assert mapper._collisions[topic] == [("temperature", "temp1"), ("ph", "ph1")]


@pytest.mark.asyncio
async def test_persistent_collision_not_renotified_across_refreshes():
    """A persisting collision notifies once, not on every poll cycle."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    with patch(
        "custom_components.reef_pi.mqtt_name_mapper.persistent_notification"
    ) as mock_notif:
        # Cycle 1: collision appears -> notify once
        mapper.begin_refresh()
        mapper.add_temperature("Tank", "1")
        mapper.add_temperature("Tank", "2")
        mapper.commit_refresh()
        mapper.notify_collisions()

        # Cycle 2: same collision persists -> no new notification
        mapper.begin_refresh()
        mapper.add_temperature("Tank", "1")
        mapper.add_temperature("Tank", "2")
        mapper.commit_refresh()
        mapper.notify_collisions()

        assert mock_notif.async_create.call_count == 1


@pytest.mark.asyncio
async def test_resolved_collision_dismisses_and_renotifies():
    """A resolved collision dismisses; a later collision notifies again."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass, entry, "reef-pi")

    with patch(
        "custom_components.reef_pi.mqtt_name_mapper.persistent_notification"
    ) as mock_notif:
        # Cycle 1: collision -> notify
        mapper.begin_refresh()
        mapper.add_temperature("Tank", "1")
        mapper.add_temperature("Tank", "2")
        mapper.commit_refresh()
        mapper.notify_collisions()
        assert mock_notif.async_create.call_count == 1

        # Cycle 2: collision resolved -> dismiss
        mapper.begin_refresh()
        mapper.add_temperature("Tank", "1")
        mapper.commit_refresh()
        mapper.notify_collisions()
        mock_notif.async_dismiss.assert_called_with(
            hass, "reef_pi_mqtt_collisions_test_id"
        )

        # Cycle 3: collision returns -> notify again (state was reset on dismiss)
        mapper.begin_refresh()
        mapper.add_temperature("Tank", "1")
        mapper.add_temperature("Tank", "2")
        mapper.commit_refresh()
        mapper.notify_collisions()
        assert mock_notif.async_create.call_count == 2


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


async def test_update_atos_skips_ato_without_inlet_key(hass):
    """Test update_atos handles an ATO with no inlet key at all."""
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_signin(mock)
        mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/atos").respond(
            200,
            json=[{"id": "1", "name": "Keyless ATO", "is_macro": True}],
        )
        mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/atos/1/usage").respond(
            200, json={}
        )
        coordinator = await _build_coordinator(hass)

        await coordinator.update_atos()

        assert coordinator.mqtt_name_mapper.topic_to_device == {}
        assert not coordinator.mqtt_name_mapper.has_collisions()


async def test_async_update_data_commits_mappings_on_success(hass):
    """A successful refresh commits the staged mappings into the live maps."""
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock, has_inlets=True)
        coordinator = await _build_coordinator(hass)

        await coordinator._async_update_data()

        # ATO state topic was registered and committed to the live map
        assert coordinator.mqtt_name_mapper.topic_to_device[
            "reef-pi/ato_test_ato_state"
        ] == ("inlet", "2")
        assert coordinator.mqtt_name_mapper._building is None


async def test_async_update_data_preserves_mappings_on_transient_failure(hass):
    """A transient REST failure mid-cycle must not wipe the last committed mappings."""
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock, has_inlets=True)
        coordinator = await _build_coordinator(hass)

        # First refresh succeeds and commits mappings.
        await coordinator._async_update_data()
        committed = dict(coordinator.mqtt_name_mapper.topic_to_device)
        assert "reef-pi/ato_test_ato_state" in committed

        # Second refresh: equipment endpoint now raises a connection error partway
        # through (CannotConnect -> UpdateFailed). commit_refresh is never reached.
        mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/equipment").mock(
            side_effect=httpx.ConnectError("boom")
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        # Live mappings are unchanged (last known-good preserved), not emptied.
        assert coordinator.mqtt_name_mapper.topic_to_device == committed
        assert (
            "reef-pi/ato_test_ato_state" in coordinator.mqtt_name_mapper.topic_to_device
        )


async def test_async_update_data_retains_soft_failed_subsystem_topics(hass):
    """A subsystem endpoint soft-failing ({}/[] without raising) keeps its topics.

    Reproduces the codex iteration-3 finding: a REST endpoint returning an empty body
    (no exception) skips that subsystem's add_* calls for the cycle. A REPLACE-on-commit
    would drop those topics from the live map and silently disable MQTT updates for the
    still-existing entities. With MERGE-on-commit the previously committed topics are
    retained (pH is a known-flaky endpoint in this project).
    """
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock, has_inlets=True)
        coordinator = await _build_coordinator(hass)

        # Cycle 1 succeeds: pH probe (id "6") gets registered and committed.
        await coordinator._async_update_data()
        ph_topic = "reef-pi/ph_ph"
        assert coordinator.mqtt_name_mapper.topic_to_device[ph_topic] == ("ph", "6")

        # Cycle 2: /api/phprobes now soft-fails with an empty list (no exception). The
        # other subsystems still succeed, so commit_refresh is reached.
        mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes").respond(200, json=[])

        await coordinator._async_update_data()

        # pH topic is retained from the previous good cycle (not dropped by the merge).
        assert coordinator.mqtt_name_mapper.topic_to_device[ph_topic] == ("ph", "6")
        # A subsystem that did refresh this cycle is still present too.
        assert (
            "reef-pi/ato_test_ato_state" in coordinator.mqtt_name_mapper.topic_to_device
        )


async def test_notify_collisions_rewrites_when_devices_change(hass):
    """A stable topic whose colliding devices change re-creates the notification."""
    hass_mock = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_id"

    mapper = ReefPiMQTTNameMapper(hass_mock, entry, "reef-pi")

    with patch(
        "custom_components.reef_pi.mqtt_name_mapper.persistent_notification"
    ) as mock_notif:
        # Cycle 1: devices 1+2 collide on the tank topic -> notify once
        mapper.begin_refresh()
        mapper.add_temperature("Tank", "1")
        mapper.add_temperature("Tank", "2")
        mapper.commit_refresh()
        mapper.notify_collisions()
        assert mock_notif.async_create.call_count == 1

        # Cycle 2: same topic, but devices change to 1+3 -> must re-notify
        mapper.begin_refresh()
        mapper.add_temperature("Tank", "1")
        mapper.add_temperature("Tank", "3")
        mapper.commit_refresh()
        mapper.notify_collisions()
        assert mock_notif.async_create.call_count == 2

        # New notification message reflects the new device id
        message = mock_notif.async_create.call_args[0][1]
        assert "ID: 3" in message


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
