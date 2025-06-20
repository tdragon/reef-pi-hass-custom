import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import respx
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.reef_pi import DOMAIN

from . import async_api_mock


@pytest.fixture
async def async_api_mock_instance():
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_all(mock)
        yield mock


@pytest.mark.asyncio
async def test_ph_calibration_buttons(hass, async_api_mock_instance):
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

    with (
        patch("custom_components.reef_pi.__init__.PH_CALIBRATION_DELAY", 0),
        patch(
            "asyncio.sleep",
            return_value=asyncio.Future(),
        ) as sleep_mock,
        patch(
            "homeassistant.components.persistent_notification.async_create",
            new_callable=AsyncMock,
        ) as notify_mock,
        patch(
            "custom_components.reef_pi.async_api.ReefApi.ph",
            new_callable=AsyncMock,
            side_effect=[{"value": -1}] + [{"value": 7.0}] * 10,
        ) as ph_mock,
    ):
        sleep_mock.return_value.set_result(None)
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.reef_pi_calibrate_ph_freshwater"},
            blocking=True,
        )

        messages = [c[0][1] for c in notify_mock.call_args_list]
        assert "pH 4" in messages[0]
        assert "pH 7" in messages[1]
        assert notify_mock.call_count == 3

        notify_mock.reset_mock()

        assert ph_mock.call_count >= 2

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.reef_pi_calibrate_ph_saltwater"},
            blocking=True,
        )

        messages = [c[0][1] for c in notify_mock.call_args_list]
        assert "pH 7" in messages[0]
        assert "pH 10" in messages[1]
        assert notify_mock.call_count == 3

    assert route.call_count == 4
