"""Test Ph sensor for Reef_Pi integration."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

from . import api_mock

async def test_ph(hass, requests_mock):
    mock = api_mock.ApiMock(requests_mock)

    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": api_mock.REEF_MOCK_URL,
        "username": api_mock.REEF_MOCK_USER,
        "password": api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_ph")
    assert state
    assert state.state == '8.1943661971831'
    assert state.name == 'reef-pi_pH'
