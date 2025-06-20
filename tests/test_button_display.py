import pytest
import respx
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

from . import async_api_mock


@pytest.fixture
async def async_api_mock_instance_display():
    with respx.mock() as mock:
        async_api_mock.mock_all(mock)
        mock.get(
            f"{async_api_mock.REEF_MOCK_URL}/api/capabilities",
            cookies={"auth": "token"},
        ).respond(
            200,
            json={
                "dev_mode": False,
                "dashboard": False,
                "health_check": False,
                "equipment": True,
                "timers": False,
                "lighting": True,
                "temperature": True,
                "ato": True,
                "camera": False,
                "doser": True,
                "ph": True,
                "macro": False,
                "configuration": False,
                "journal": False,
                "display": True,
            },
        )
        mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/display").respond(
            200, json={"on": False, "brightness": 50}
        )
        yield mock


async def test_reboot_button(hass, async_api_mock_instance_display):
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

    route = async_api_mock_instance_display.post(
        f"{async_api_mock.REEF_MOCK_URL}/api/admin/reboot"
    ).respond(200, json={})

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.reef_pi_reboot"},
        blocking=True,
    )

    assert route.called


async def test_power_off_button(hass, async_api_mock_instance_display):
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

    route = async_api_mock_instance_display.post(
        f"{async_api_mock.REEF_MOCK_URL}/api/admin/poweroff"
    ).respond(200, json={})

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.reef_pi_power_off"},
        blocking=True,
    )

    assert route.called


async def test_display_switch(hass, async_api_mock_instance_display):
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

    route_on = async_api_mock_instance_display.post(
        f"{async_api_mock.REEF_MOCK_URL}/api/display/on"
    ).respond(200, json={})

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.reef_pi_display"},
        blocking=True,
    )

    assert route_on.called

    route_off = async_api_mock_instance_display.post(
        f"{async_api_mock.REEF_MOCK_URL}/api/display/off"
    ).respond(200, json={})

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.reef_pi_display"},
        blocking=True,
    )

    assert route_off.called
