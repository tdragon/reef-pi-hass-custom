"""Test Ph sensor for Reef_Pi integration."""

from homeassistant.components.mqtt.models import ReceiveMessage
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN
from custom_components.reef_pi.mqtt_handler import ReefPiMQTTHandler


import pytest
import respx
from . import async_api_mock


@pytest.fixture
async def async_api_mock_instance():
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock)
        yield mock


async def test_sensors(hass, async_api_mock_instance):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi")
    assert state
    assert state.state == "39.0"
    assert state.name == "Reef PI"
    assert state.attributes["unit_of_measurement"] == "°C"


async def test_temperature_sensor(hass, async_api_mock_instance):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_temp")
    assert state
    assert state.state == "25.0"
    assert state.name == "Reef PI Temp"
    assert state.attributes["unit_of_measurement"] == "°C"


async def test_ato(hass, async_api_mock_instance):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_test_ato_last_run")
    assert state
    assert state.state == "2022-01-11T09:01:00+00:00"
    assert state.name == "Reef PI Test ATO Last Run"


async def test_ato_duration(hass, async_api_mock_instance):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_test_ato_duration")
    assert state
    assert state.state == "120"
    assert state.name == "Reef PI Test ATO Duration"


async def test_ato_empty(hass):
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock, has_ato_usage=False)
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": async_api_mock.REEF_MOCK_URL,
                "username": async_api_mock.REEF_MOCK_USER,
                "password": async_api_mock.REEF_MOCK_PASSWORD,
                "verify": False,
            },
        )

        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("sensor.reef_pi_test_ato_duration")
        assert state
        assert state.state == "unavailable"
        assert state.name == "Reef PI Test ATO Duration"


async def test_inlet_polled_with_ato(hass):
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock, has_inlets=True)
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": async_api_mock.REEF_MOCK_URL,
                "username": async_api_mock.REEF_MOCK_USER,
                "password": async_api_mock.REEF_MOCK_PASSWORD,
                "verify": False,
            },
        )

        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        assert "2" in coordinator.inlets
        assert coordinator.inlets["2"]["state"] is True

        # The ATO state topic is mapped to the inlet id, and the phantom inlet
        # topic (which reef-pi never publishes) must not be registered.
        topic_map = coordinator.mqtt_name_mapper.topic_to_device
        assert topic_map["reef-pi/ato_test_ato_state"] == ("inlet", "2")
        assert "reef-pi/float_switch" not in topic_map

        state = hass.states.get("binary_sensor.reef_pi_float_switch")
        assert state
        assert state.state == "on"
        assert state.name == "Reef PI Float Switch"


async def test_inlet_mqtt_updates_binary_sensor(hass):
    """End-to-end: an ATO state MQTT message flips the inlet binary_sensor (issue #69).

    Polling sets the inlet to on (read returns 1). update_atos registers
    ``reef-pi/ato_test_ato_state -> ("inlet", "2")``. Feeding a "0" payload through
    the real handler must propagate to the binary_sensor entity.
    """
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock, has_inlets=True)
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": async_api_mock.REEF_MOCK_URL,
                "username": async_api_mock.REEF_MOCK_USER,
                "password": async_api_mock.REEF_MOCK_PASSWORD,
                "verify": False,
            },
        )

        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        assert coordinator.inlets["2"]["state"] is True
        assert hass.states.get("binary_sensor.reef_pi_float_switch").state == "on"

        handler = ReefPiMQTTHandler(hass, coordinator)
        msg = ReceiveMessage(
            topic="reef-pi/ato_test_ato_state",
            payload="0.000000",
            qos=0,
            retain=False,
            subscribed_topic="reef-pi/#",
            timestamp=0.0,
        )
        handler._mqtt_message_received(msg)
        await hass.async_block_till_done()

        assert coordinator.inlets["2"]["state"] is False
        state = hass.states.get("binary_sensor.reef_pi_float_switch")
        assert state
        assert state.state == "off"


async def test_inlet_polled_without_ato(hass):
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock, has_ato=False, has_inlets=True)
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": async_api_mock.REEF_MOCK_URL,
                "username": async_api_mock.REEF_MOCK_USER,
                "password": async_api_mock.REEF_MOCK_PASSWORD,
                "verify": False,
            },
        )

        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        assert coordinator.has_ato is False
        assert "2" in coordinator.inlets
        assert coordinator.inlets["2"]["state"] is True

        state = hass.states.get("binary_sensor.reef_pi_float_switch")
        assert state
        assert state.state == "on"
        assert state.name == "Reef PI Float Switch"
