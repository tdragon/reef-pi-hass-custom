import logging
import pytest
from custom_components.reef_pi import async_api
from homeassistant.core import HomeAssistant

import respx
from . import async_api_mock

log = logging.getLogger(__name__)
log.info("TEST")

@pytest.fixture
async def reef_pi_instance():
    with respx.mock() as mock:
        async_api_mock.mock_signin(mock)
        a = async_api.ReefApi(async_api_mock.REEF_MOCK_URL)
        await a.authenticate(async_api_mock.REEF_MOCK_USER, async_api_mock.REEF_MOCK_PASSWORD)
        #async_api_mock.mock_authenticated(mock)
        yield (mock, a)

@pytest.mark.asyncio
async def test_basic_auth():
    with respx.mock() as mock:
        async_api_mock.mock_signin(mock)
        reef = async_api.ReefApi(async_api_mock.REEF_MOCK_URL)
        await reef.authenticate(async_api_mock.REEF_MOCK_USER, async_api_mock.REEF_MOCK_PASSWORD)
        assert reef.is_authenticated()
        assert "token" == reef.cookies['auth']

@pytest.mark.asyncio
async def test_capabilities(reef_pi_instance):
     mock, reef = reef_pi_instance
     async_api_mock.mock_capabilities(mock)
     c = await reef.capabilities()
     assert c['ph']

@pytest.mark.asyncio
async def test_probes(reef_pi_instance):
     mock, reef = reef_pi_instance
     async_api_mock.mock_phprobes(mock)
     probes = await reef.phprobes()
     assert 'pH' == probes[0]['name']
     assert '6' == probes[0]['id']

@pytest.mark.asyncio
async def test_ph(reef_pi_instance):
    mock, reef = reef_pi_instance
    async_api_mock.mock_ph6(mock)
    reading = await reef.ph('6')
    assert 8.194366197183099 == reading['value']
    mock.get(f'{async_api_mock.REEF_MOCK_URL}/api/phprobes/unknown/readings').respond(404)
    assert None == (await reef.ph('unknown'))['value']


