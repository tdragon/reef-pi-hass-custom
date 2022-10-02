"""Test Ph sensor for Reef_Pi integration."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

import pytest
import httpx
import respx
from asyncio import sleep
from . import async_api_mock

@pytest.fixture
async def async_api_mock_instance():
    with respx.mock() as mock:
        async_api_mock.mock_all(mock)

        mock.get(f'{async_api_mock.REEF_MOCK_URL}/api/phprobes/6/readings').mock(side_effect=lambda equest, route:
              httpx.Response(200, json={"current": [{"value": 7+(route.call_count + 1.0)/1000.0, "up": 0, "down": 15, "time": "Jun-08-02:07, 2021"}]}))
        yield mock


async def waitFor(condition, value, timeout: int):
    if condition() == value:
        return True
    while timeout != 0:
        await sleep(1)
        timeout -= 1
        if condition() == value:
            return True
    return False


async def test_ph(hass, async_api_mock_instance):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": async_api_mock.REEF_MOCK_URL,
        "username": async_api_mock.REEF_MOCK_USER,
        "password": async_api_mock.REEF_MOCK_PASSWORD,
        "verify": False,
        "update_interval": 1})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_ph")
    assert state
    assert state.state == '7.001'
    assert state.name == 'Reef PI pH'
    assert await waitFor(lambda: hass.states.get("sensor.reef_pi_ph").state, '7.003', 3)

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