"""Test Ph sensor for Reef_Pi integration."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

import os
import pytest
import httpx
import respx
from asyncio import sleep
from . import async_api_mock
import json
import logging

_LOGGER = logging.getLogger(__package__)
PAYLOAD_DIR = os.path.join(os.getcwd(), "tests/payloads")

@pytest.fixture
async def async_api_mock_instance():
    with respx.mock() as mock:
        async_api_mock.mock_all(mock)

        with open(os.path.join(PAYLOAD_DIR, "ph_readings.json"), "rt") as payload:
            ph_readings = json.loads(payload.read())

            mock.get(f'{async_api_mock.REEF_MOCK_URL}/api/phprobes/6/read').mock(side_effect=lambda request, route:
                httpx.Response(200, json=ph_readings['current'][route.call_count]['value']))
        yield mock


async def waitFor(condition, value, timeout: int):
    if condition() == value:
        return True
    while timeout != 0:
        await sleep(1)
        timeout -= 1
        current = condition()
        _LOGGER.debug("current value: %s", current)
        if current == value:
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
    assert state.state == '6.8389'
    assert state.name == 'Reef PI pH'
    await waitFor(lambda: hass.states.get("sensor.reef_pi_ph").state, '6.8389', 10)
    state = hass.states.get("sensor.reef_pi_ph")
    assert state.state == '6.8389'

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
    assert state.state == '7.23'

    state = hass.states.get("sensor.reef_pi_ph_no_history")
    assert state
    assert state.state == 'unavailable'