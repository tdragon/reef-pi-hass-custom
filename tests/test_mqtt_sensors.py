"""Test MQTT diagnostic sensors for Reef-Pi integration."""

import pytest
import respx
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

from . import async_api_mock


@pytest.fixture
async def async_api_mock_instance():
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock)
        yield mock


@pytest.fixture
async def async_api_mock_mqtt_enabled():
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all_mqtt_enabled(mock)
        yield mock


async def test_mqtt_sensors_not_created_when_disabled(hass, async_api_mock_instance):
    """Test that MQTT diagnostic sensors are not created when MQTT is disabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
            "mqtt_prefix": "reef-pi",
            "mqtt_available": False,
        },
        options={
            "mqtt_enabled": False,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # MQTT diagnostic sensors should not exist
    assert hass.states.get("sensor.reef_pi_mqtt_status") is None
    assert hass.states.get("sensor.reef_pi_mqtt_messages_received") is None
    assert hass.states.get("sensor.reef_pi_mqtt_last_temperature_update") is None
    assert hass.states.get("sensor.reef_pi_mqtt_last_equipment_update") is None
    assert hass.states.get("sensor.reef_pi_mqtt_last_ph_update") is None


async def test_mqtt_sensors_created_when_enabled(hass, async_api_mock_mqtt_enabled):
    """Test that MQTT diagnostic sensors are created when MQTT is enabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
            "mqtt_prefix": "reef-pi",
            "mqtt_available": True,
        },
        options={
            "mqtt_enabled": True,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # MQTT diagnostic sensors should exist
    assert hass.states.get("sensor.reef_pi_mqtt_status") is not None
    assert hass.states.get("sensor.reef_pi_mqtt_messages_received") is not None
    assert hass.states.get("sensor.reef_pi_mqtt_last_temperature_update") is not None
    assert hass.states.get("sensor.reef_pi_mqtt_last_equipment_update") is not None
    assert hass.states.get("sensor.reef_pi_mqtt_last_ph_update") is not None


async def test_mqtt_status_sensor_disabled(hass, async_api_mock_instance):
    """Test MQTT status sensor shows 'disabled' when MQTT is disabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
            "mqtt_prefix": "reef-pi",
            "mqtt_available": False,
        },
        options={
            "mqtt_enabled": False,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Status sensor should not exist when MQTT disabled
    assert hass.states.get("sensor.reef_pi_mqtt_status") is None


async def test_mqtt_status_sensor_no_messages(hass, async_api_mock_mqtt_enabled):
    """Test MQTT status sensor shows 'no_messages' when MQTT enabled but no messages."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
            "mqtt_prefix": "reef-pi",
            "mqtt_available": True,
        },
        options={
            "mqtt_enabled": True,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_mqtt_status")
    assert state is not None
    assert state.state == "No messages"


async def test_mqtt_message_count_sensor(hass, async_api_mock_mqtt_enabled):
    """Test MQTT message count sensor shows 0 initially."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
            "mqtt_prefix": "reef-pi",
            "mqtt_available": True,
        },
        options={
            "mqtt_enabled": True,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_mqtt_messages_received")
    assert state is not None
    assert state.state == "0"


async def test_mqtt_last_update_sensors(hass, async_api_mock_mqtt_enabled):
    """Test MQTT last update sensors exist."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
            "mqtt_prefix": "reef-pi",
            "mqtt_available": True,
        },
        options={
            "mqtt_enabled": True,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    temp_state = hass.states.get("sensor.reef_pi_mqtt_last_temperature_update")
    assert temp_state is not None
    assert temp_state.name == "Reef PI MQTT Last Temperature Update"

    equip_state = hass.states.get("sensor.reef_pi_mqtt_last_equipment_update")
    assert equip_state is not None
    assert equip_state.name == "Reef PI MQTT Last Equipment Update"

    ph_state = hass.states.get("sensor.reef_pi_mqtt_last_ph_update")
    assert ph_state is not None
    assert ph_state.name == "Reef PI MQTT Last Ph Update"


async def test_mqtt_sensor_names(hass, async_api_mock_mqtt_enabled):
    """Test MQTT diagnostic sensor names."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
            "mqtt_prefix": "reef-pi",
            "mqtt_available": True,
        },
        options={
            "mqtt_enabled": True,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    status = hass.states.get("sensor.reef_pi_mqtt_status")
    assert status.name == "Reef PI MQTT Status"

    messages = hass.states.get("sensor.reef_pi_mqtt_messages_received")
    assert messages.name == "Reef PI MQTT Messages Received"
