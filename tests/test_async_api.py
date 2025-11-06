import logging

import pytest
import respx

from custom_components.reef_pi import async_api

from . import async_api_mock

log = logging.getLogger(__name__)
log.info("TEST")


@pytest.fixture
async def reef_pi_instance():
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_signin(mock)
        a = async_api.ReefApi(async_api_mock.REEF_MOCK_URL)
        await a.authenticate(
            async_api_mock.REEF_MOCK_USER, async_api_mock.REEF_MOCK_PASSWORD
        )
        # async_api_mock.mock_authenticated(mock)
        yield (mock, a)


@pytest.mark.asyncio
async def test_basic_auth():
    with respx.mock(assert_all_called=False) as mock:
        async_api_mock.mock_signin(mock)
        reef = async_api.ReefApi(async_api_mock.REEF_MOCK_URL)
        await reef.authenticate(
            async_api_mock.REEF_MOCK_USER, async_api_mock.REEF_MOCK_PASSWORD
        )
        assert reef.is_authenticated()
        assert "token" == reef.cookies["auth"]


@pytest.mark.asyncio
async def test_capabilities(reef_pi_instance):
    mock, reef = reef_pi_instance
    async_api_mock.mock_capabilities(mock)
    c = await reef.capabilities()
    assert c["ph"]


@pytest.mark.asyncio
async def test_probes(reef_pi_instance):
    mock, reef = reef_pi_instance
    async_api_mock.mock_phprobes(mock)
    probes = await reef.phprobes()
    assert "pH" == probes[0]["name"]
    assert "6" == probes[0]["id"]


@pytest.mark.asyncio
async def test_ph(reef_pi_instance):
    mock, reef = reef_pi_instance
    async_api_mock.mock_ph6(mock)
    reading = await reef.ph_readings("6")
    assert 6.66 == reading["value"]
    mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/unknown/read").respond(404)
    assert (await reef.ph("unknown"))["value"] is None


@pytest.mark.asyncio
async def test_ph_nan_handling(reef_pi_instance):
    """Test that NaN values from disabled probes are handled correctly"""
    mock, reef = reef_pi_instance
    # Mock a probe returning NaN (happens when probe is disabled)
    mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/6/read").respond(
        200, json="NaN"
    )
    result = await reef.ph(6)
    # Should return None instead of NaN to prevent JSON encoding errors
    assert result["value"] is None


@pytest.mark.asyncio
async def test_atos(reef_pi_instance):
    mock, reef = reef_pi_instance
    async_api_mock.mock_atos(mock)
    info = await reef.atos()
    assert "1" == info[0]["id"]

    usage = await reef.ato(1)
    assert 0 == usage[-1]["pump"]
    assert 120 == usage[0]["pump"]


@pytest.mark.asyncio
async def test_ph_calibration_midpoint_saltwater(reef_pi_instance):
    """Test pH calibration midpoint with saltwater buffer (pH 7.0)"""
    mock, reef = reef_pi_instance
    mock.post(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/6/calibratepoint").respond(
        200, json={}
    )
    result = await reef.ph_probe_calibrate_point(6, 7.0, 6.9, "mid")
    assert result


@pytest.mark.asyncio
async def test_ph_calibration_midpoint_freshwater(reef_pi_instance):
    """Test pH calibration midpoint with freshwater buffer (pH 4.0)"""
    mock, reef = reef_pi_instance
    mock.post(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/6/calibratepoint").respond(
        200, json={}
    )
    result = await reef.ph_probe_calibrate_point(6, 4.0, 4.1, "mid")
    assert result


@pytest.mark.asyncio
async def test_ph_calibration_highpoint_saltwater(reef_pi_instance):
    """Test pH calibration highpoint with saltwater buffer (pH 10.0)"""
    mock, reef = reef_pi_instance
    mock.post(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/6/calibratepoint").respond(
        200, json={}
    )
    result = await reef.ph_probe_calibrate_point(6, 10.0, 9.8, "high")
    assert result


@pytest.mark.asyncio
async def test_ph_calibration_highpoint_freshwater(reef_pi_instance):
    """Test pH calibration highpoint with freshwater buffer (pH 7.0)"""
    mock, reef = reef_pi_instance
    mock.post(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/6/calibratepoint").respond(
        200, json={}
    )
    result = await reef.ph_probe_calibrate_point(6, 7.0, 6.9, "high")
    assert result


@pytest.mark.asyncio
async def test_ph_probe_enable_disable(reef_pi_instance):
    mock, reef = reef_pi_instance
    # Mock getting probe data
    mock.get(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/6").respond(
        200,
        json={
            "id": "6",
            "name": "pH",
            "enable": True,
            "period": 60,
            "analog_input": "1",
        },
    )
    # Mock updating probe
    mock.post(f"{async_api_mock.REEF_MOCK_URL}/api/phprobes/6").respond(200, json={})
    result = await reef.ph_probe_update(6, False)
    assert result
