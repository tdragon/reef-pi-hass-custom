"""Test Ph sensor for Reef_Pi integration."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

import pytest
import respx
from . import async_api_mock


@pytest.fixture
async def async_api_mock_instance():
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock)
        yield mock


async def test_pump1(hass, async_api_mock_instance):
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

    state = hass.states.get("sensor.reef_pi_pump_1_0")
    assert state
    assert state.state == "2021-08-23T20:30:00"
    assert state.name == "Reef PI Pump1 sched1"


async def test_pump2(hass, async_api_mock_instance):
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

    state = hass.states.get("sensor.reef_pi_pump_2_1")
    assert state
    assert state.state == "2021-08-23T21:30:00"
    assert state.name == "Reef PI Pump2 sched1"


async def test_pump_no_current(hass, async_api_mock_instance):
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

    state = hass.states.get("sensor.reef_pi_pump_2_2")
    assert state
    assert state.state == "2021-08-23T19:30:00"
    assert state.name == "Reef PI Pump2 sched1"


async def test_pump_no_history(hass, async_api_mock_instance):
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

    state = hass.states.get("sensor.reef_pi_pump_3_0")
    assert state.state == "unavailable"
