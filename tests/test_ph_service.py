import pytest
import respx
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

from . import async_api_mock


@pytest.fixture
async def async_api_mock_instance():
    with respx.mock() as mock:
        async_api_mock.mock_all(mock)
        yield mock


async def test_ph_calibrate_service(hass, async_api_mock_instance):
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

    route = async_api_mock_instance.post(
        f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/6/calibratepoint"
    ).respond(200, json={})

    await hass.services.async_call(
        DOMAIN,
        "calibrate_ph_probe",
        {"probe_id": 6, "expected": 7.0, "observed": 6.9},
        blocking=True,
    )

    assert route.called
