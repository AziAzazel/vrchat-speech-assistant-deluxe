from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
import pytest
from vrchat_speech_assistant.providers import PollyPool


def test_client_and_successful_validation_are_reused_until_keys_or_region_change():
    client = Mock()
    client.test.return_value = True
    factory = Mock(return_value=client)
    pool = PollyPool(factory)
    credentials = ('test-access', 'test-secret', 'us-west-2')
    assert pool.get(credentials) is client
    for _ in range(4):
        assert pool.get(credentials, validate=True) is client
    factory.assert_called_once_with(*credentials)
    client.test.assert_called_once()
    pool.get(('other-access', 'other-secret', 'eu-west-1'), validate=True)
    assert factory.call_count == 2 and client.test.call_count == 2


def test_failed_validation_can_be_retried_and_empty_credentials_never_construct():
    client, factory = Mock(), Mock()
    factory.return_value = client
    client.test.side_effect = [False, True]
    pool = PollyPool(factory)
    with pytest.raises(ValueError):
        pool.get(('', '', 'region'))
    factory.assert_not_called()
    key = ('access', 'secret', 'region')
    with pytest.raises(ValueError):
        pool.get(key, validate=True)
    assert pool.get(key, validate=True) is client
    assert client.test.call_count == 2


def test_concurrent_requests_create_one_shared_client():
    factory = Mock(return_value=Mock())
    pool = PollyPool(factory)
    with ThreadPoolExecutor(max_workers=4) as threads:
        clients = list(threads.map(lambda _: pool.get(('access', 'secret', 'region')), range(20)))
    assert all(client is clients[0] for client in clients)
    factory.assert_called_once()


def test_credential_check_closes_its_unused_response_stream():
    from vrchat_speech_assistant.providers import Polly
    stream = Mock()
    provider = Polly.__new__(Polly)
    provider.client = Mock()
    provider.client.synthesize_speech.return_value = {'AudioStream': stream}
    assert provider.test()
    stream.close.assert_called_once()
