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

async def test_sensors(hass, async_api_mock_instance):

    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": async_api_mock.REEF_MOCK_URL,
        "username": async_api_mock.REEF_MOCK_USER,
        "password": async_api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi")
    assert state
    assert state.state == '39.0'
    assert state.name == 'reef_pi'
    assert state.attributes['unit_of_measurement'] == '°C'

async def test_temperature_sensor(hass, async_api_mock_instance):

    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": async_api_mock.REEF_MOCK_URL,
        "username": async_api_mock.REEF_MOCK_USER,
        "password": async_api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_temp")
    assert state
    assert state.state == '25.0'
    assert state.name == 'reef_pi Temp'
    assert state.attributes['unit_of_measurement'] == '°C'


async def test_ato(hass, async_api_mock_instance):

    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": async_api_mock.REEF_MOCK_URL,
        "username": async_api_mock.REEF_MOCK_USER,
        "password": async_api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_test_ato_last_run")
    assert state
    assert state.state == '2022-01-11T09:01:00'
    assert state.name == 'reef_pi Test ATO Last Run'


async def test_ato_duration(hass, async_api_mock_instance):

    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": async_api_mock.REEF_MOCK_URL,
        "username": async_api_mock.REEF_MOCK_USER,
        "password": async_api_mock.REEF_MOCK_PASSWORD,
        "verify": False})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.reef_pi_test_ato_duration")
    assert state
    assert state.state == '120'
    assert state.name == 'reef_pi Test ATO Duration'

async def test_ato_empty(hass):

    with respx.mock() as mock:
        async_api_mock.mock_all(mock, has_ato_usage=False)
        entry = MockConfigEntry(domain=DOMAIN, data={
            "host": async_api_mock.REEF_MOCK_URL,
            "username": async_api_mock.REEF_MOCK_USER,
            "password": async_api_mock.REEF_MOCK_PASSWORD,
            "verify": False})

        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("sensor.reef_pi_test_ato_duration")
        assert state
        assert state.state == 'unavailable'
        assert state.name == 'reef_pi Test ATO Duration'
