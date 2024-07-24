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


async def test_no_warning_in_log(hass, async_api_mock_instance, caplog):
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

    lines = caplog.text.split("\n")
    warnings = [
        line
        for line in lines
        if ("WARNING" in line or "ERROR" in line)
        and "We found a custom integration reef_pi" not in line
        and "falling back to zlib" not in line
    ]
    assert len(warnings) == 0
