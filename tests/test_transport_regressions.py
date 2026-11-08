"""Regression coverage for real client retry and cache boundaries."""

from unittest.mock import Mock, patch

import pytest
import requests

from usaspending import USASpendingClient, config


@pytest.mark.parametrize("cache_enabled", [False, True])
@pytest.mark.parametrize("max_retries", [0, 2])
@pytest.mark.parametrize("error", [requests.Timeout, requests.ConnectionError])
def test_transport_failures_do_not_restart_retry_budget(
    client_config, cache_enabled, max_retries, error
):
    client_config(
        cache_enabled=cache_enabled,
        cache_backend="memory",
        max_retries=max_retries,
        retry_delay=0,
    )
    with USASpendingClient() as client:
        with (
            patch.object(client._session, "request", side_effect=error("offline")) as request,
            pytest.raises(error, match="offline"),
        ):
            client._make_request("GET", "/test/")
        assert request.call_count == max_retries + 1
        assert client._request_count == max_retries + 1
        assert len(client.rate_limiter._call_times) == max_retries + 1


def test_cache_failure_falls_back_to_one_retry_sequence(client_config):
    client_config(cache_enabled=True, cache_backend="memory", max_retries=2, retry_delay=0)
    with USASpendingClient() as client:
        client._make_cached_request = Mock(side_effect=RuntimeError("cache unavailable"))
        with (
            patch.object(client._session, "request", side_effect=requests.Timeout) as request,
            pytest.raises(requests.Timeout),
        ):
            client._make_request("GET", "/test/")
        assert request.call_count == 3
        client._make_cached_request.assert_called_once()


def test_retry_uses_replacement_session(client_config):
    client_config(max_retries=1, retry_delay=0, session_reset_on_5xx_threshold=1)
    failed = requests.Response()
    failed.status_code = 503
    failed._content = b"{}"
    succeeded = requests.Response()
    succeeded.status_code = 200
    succeeded._content = b'{"ok": true}'
    fresh_session = Mock(spec=requests.Session)
    fresh_session.request.return_value = succeeded
    with USASpendingClient() as client:
        with (
            patch.object(client._session, "request", return_value=failed) as old_request,
            patch.object(client, "_create_session", return_value=fresh_session),
        ):
            assert client._make_request("GET", "/test/") == {"ok": True}
        old_request.assert_called_once()
        fresh_session.request.assert_called_once()
        assert client._request_count == 1
        assert len(client.rate_limiter._call_times) == 2


def test_session_limit_counts_the_first_attempt_in_new_session(client_config, requests_mock):
    client_config(session_request_limit=2)
    requests_mock.get(config.base_url + "test/", json={"ok": True})
    with USASpendingClient() as client:
        original = client._session
        client._make_request("GET", "/test/")
        client._make_request("GET", "/test/")
        assert client._session is original
        assert client._request_count == 2
        client._make_request("GET", "/test/")
        assert client._session is not original
        assert client._request_count == 1


def test_file_cache_isolates_base_urls_and_cache_hits_are_free(
    client_config, requests_mock, tmp_path
):
    client_config(
        cache_enabled=True,
        cache_backend="file",
        cache_dir=str(tmp_path),
        base_url="https://first.example/api/",
    )
    requests_mock.get("https://first.example/api/test/", json={"source": "first"})
    requests_mock.get("https://second.example/api/test/", json={"source": "second"})
    with USASpendingClient() as client:
        assert client._make_request("GET", "/test/") == {"source": "first"}
        assert client._make_request("GET", "/test/") == {"source": "first"}
        assert client._request_count == 1
        assert len(client.rate_limiter._call_times) == 1
        client_config(base_url="https://second.example/api/")
        assert client._make_request("GET", "/test/") == {"source": "second"}
        assert client._request_count == 2
    assert requests_mock.call_count == 2
