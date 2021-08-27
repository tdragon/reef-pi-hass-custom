"""Test Ph sensor for Reef_Pi integration."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

from . import api_mock

async def test_pump1(hass, requests_mock):
    mock = api_mock.ApiMock(requests_mock)

    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": api_mock.REEF_MOCK_URL,
        "username": api_mock.REEF_MOCK_USER,
        "password": api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_pump_1_0")
    assert state
    assert state.state == '2021-08-23T20:30:00'
    assert state.name == 'reef-pi_pump_1_0'


async def test_pump2(hass, requests_mock):
    mock = api_mock.ApiMock(requests_mock)

    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": api_mock.REEF_MOCK_URL,
        "username": api_mock.REEF_MOCK_USER,
        "password": api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_pump_2_1")
    assert state
    assert state.state == '2021-08-23T21:30:00'
    assert state.name == 'reef-pi_pump_2_1'
