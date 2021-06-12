import logging
import pytest
import requests
from custom_components.reef_pi import api
from homeassistant.core import HomeAssistant

from . import api_mock

log = logging.getLogger(__name__)
log.info("TEST")

@pytest.fixture
def reef_pi_instance(requests_mock):
    mock = api_mock.ApiMock(requests_mock)
    a = api.ReefApi(api_mock.REEF_MOCK_URL)
    a.authenticate(api_mock.REEF_MOCK_USER, api_mock.REEF_MOCK_PASSWORD)
    return (mock, a)

def test_basic_auth(requests_mock):
    mock = api_mock.ApiMock(requests_mock)
    #assert "token" == requests.get(f"{api_mock.REEF_MOCK_URL}/auth/signin").cookies["auth"]
    reef = api.ReefApi(api_mock.REEF_MOCK_URL)
    reef.authenticate(api_mock.REEF_MOCK_USER, api_mock.REEF_MOCK_PASSWORD)
    assert reef.is_authenticated()

def test_capabilities(reef_pi_instance):
    mock, reef = reef_pi_instance
    assert reef.capabilities()['ph']

def test_probes(reef_pi_instance):
    mock, reef = reef_pi_instance
    probes = reef.phprobes()
    assert 'pH' == probes[0]['name']
    assert '6' == probes[0]['id']

def test_ph(reef_pi_instance):
    mock, reef = reef_pi_instance
    reading = reef.ph('6')
    assert 8.194366197183099 == reading['value']


