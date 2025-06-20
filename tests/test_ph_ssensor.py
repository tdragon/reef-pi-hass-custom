"""Test Ph sensor for Reef_Pi integration."""

import logging
from asyncio import sleep

import pytest
import respx
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

from . import async_api_mock

_LOGGER = logging.getLogger(__package__)


@pytest.fixture
async def async_api_mock_instance():
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock)
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
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False,
            "update_interval": 1,
        },
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_ph")
    assert state
    assert state.state == "6.66"
    assert state.name == "Reef PI pH"
