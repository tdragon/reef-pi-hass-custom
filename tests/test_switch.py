"""Test Ph sensor for Reef_Pi integration."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
)

from custom_components.reef_pi import DOMAIN


import pytest
import respx
from . import async_api_mock


@pytest.fixture
async def async_api_mock_instance():
    with respx.mock() as mock:
        async_api_mock.mock_all(mock)
        yield mock


async def test_switch(hass, async_api_mock_instance):
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

    state = hass.states.get("switch.reef_pi_co2")
    assert state.state == STATE_ON

    state = hass.states.get("switch.reef_pi_cooler")
    assert state.state == STATE_OFF
    assert state.name == "Reef PI Cooler"


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

    state = hass.states.get("switch.reef_pi_test_ato_enabled")
    assert state.state == STATE_ON
    assert state.name == "Reef PI Test ATO Enabled"
