"""Tests for runtime client caching behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from usaspending.client import USASpendingClient


def test_memory_backend_reconfigures_cached_request(client_config) -> None:
    """Memory caching should replace the file-backed cachier core."""
    client_config(cache_enabled=True, cache_backend="memory")

    assert USASpendingClient._make_cached_request.cache_dpath() is None


def test_file_backend_uses_configured_cache_dir(client_config, tmp_path: Path) -> None:
    """File caching should use the configured cache directory."""
    client_config(cache_enabled=True, cache_backend="file", cache_dir=str(tmp_path))

    cache_dir = USASpendingClient._make_cached_request.cache_dpath()
    assert cache_dir is not None
    assert Path(cache_dir) == tmp_path


def test_cache_handles_unhashable_params(client_config) -> None:
    """Repeated requests with equivalent payloads should hit the cache once."""
    client_config(cache_enabled=True, cache_backend="memory")
    USASpendingClient._make_cached_request.clear_cache()

    client = USASpendingClient()
    client._make_uncached_request = Mock(return_value={"ok": True})

    try:
        client._make_request("POST", "/test", json={"a": 1, "b": [2, 3]})
        client._make_request("POST", "/test", json={"b": [2, 3], "a": 1})

        assert client._make_uncached_request.call_count == 1
    finally:
        USASpendingClient._make_cached_request.clear_cache()
        client.close()


def test_cache_shared_across_clients(client_config) -> None:
    """Cache entries should be reusable across client instances."""
    client_config(
        cache_enabled=True,
        cache_backend="memory",
        cache_namespace="test-namespace",
    )
    USASpendingClient._make_cached_request.clear_cache()

    client_one = USASpendingClient()
    client_two = USASpendingClient()

    client_one._make_uncached_request = Mock(return_value={"client": "one"})
    client_two._make_uncached_request = Mock(return_value={"client": "two"})

    try:
        client_one._make_request("GET", "/test")
        client_two._make_request("GET", "/test")

        assert client_one._make_uncached_request.call_count == 1
        assert client_two._make_uncached_request.call_count == 0
    finally:
        USASpendingClient._make_cached_request.clear_cache()
        client_one.close()
        client_two.close()
