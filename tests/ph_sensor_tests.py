"""Test Ph sensor for Reef_Pi integration."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

import pytest
import respx
from . import async_api_mock

@pytest.fixture
async def async_api_mock_instance():
    with respx.mock() as mock:
        async_api_mock.mock_all(mock)
        yield mock


async def test_ph(hass, async_api_mock_instance):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": async_api_mock.REEF_MOCK_URL,
        "username": async_api_mock.REEF_MOCK_USER,
        "password": async_api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_ph")
    assert state
    assert state.state == '8.19'
    assert state.name == 'Reef PI pH'

async def test_ph_without_current(hass, async_api_mock_instance):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": async_api_mock.REEF_MOCK_URL,
        "username": async_api_mock.REEF_MOCK_USER,
        "password": async_api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_ph_no_current")
    assert state
    assert state.state == '5.1'

    state = hass.states.get("sensor.reef_pi_ph_no_history")
    assert state
    assert state.state == 'unavailable'