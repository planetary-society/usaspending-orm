"""Tests for client caching behavior."""

from __future__ import annotations

from unittest.mock import Mock

from usaspending.client import USASpendingClient


def test_cache_handles_unhashable_params(client_config) -> None:
    """Test that caching works with dict and list parameters."""
    client_config(cache_enabled=True, cache_backend="memory")
    USASpendingClient._make_cached_request.clear_cache()

    client = USASpendingClient()
    client._make_uncached_request = Mock(return_value={"ok": True})

    client._make_request("POST", "/test", json={"a": 1, "b": [2, 3]})
    client._make_request("POST", "/test", json={"b": [2, 3], "a": 1})

    assert client._make_uncached_request.call_count == 1

    USASpendingClient._make_cached_request.clear_cache()


def test_cache_isolated_per_client(client_config) -> None:
    """Test that caches are isolated across client instances."""
    client_config(cache_enabled=True, cache_backend="memory")
    USASpendingClient._make_cached_request.clear_cache()

    client_one = USASpendingClient()
    client_two = USASpendingClient()

    client_one._make_uncached_request = Mock(return_value={"client": "one"})
    client_two._make_uncached_request = Mock(return_value={"client": "two"})

    client_one._make_request("GET", "/test")
    client_one._make_request("GET", "/test")
    client_two._make_request("GET", "/test")

    assert client_one._make_uncached_request.call_count == 1
    assert client_two._make_uncached_request.call_count == 1

    USASpendingClient._make_cached_request.clear_cache()
