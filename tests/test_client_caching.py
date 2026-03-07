"""Tests for client caching behavior.

The ``@cachier.cachier`` decorator on ``_make_cached_request`` creates a
``_PickleCore`` at import time.  ``set_global_params`` only affects *new*
decorators, so calling ``config.configure(cache_backend="memory")`` does not
switch the existing decorator's core.  In sandboxed environments the pickle
core fails because ``~/.cachier/`` is not writable.

To work around this, the ``_use_memory_cache`` fixture re-applies the
decorator with ``backend="memory"`` before each caching test and restores
the original afterwards.
"""

from __future__ import annotations

from unittest.mock import Mock

import cachier
import pytest

from usaspending.client import USASpendingClient, _cache_key


@pytest.fixture(autouse=True)
def _use_memory_cache():
    """Replace the pickle-backed cachier decorator with a memory-backed one.

    The original decorator is restored after each test to avoid polluting
    other test modules.
    """
    original = USASpendingClient._make_cached_request
    memory_cached = cachier.cachier(backend="memory", hash_func=_cache_key)(
        original.__wrapped__,
    )
    USASpendingClient._make_cached_request = memory_cached
    yield
    USASpendingClient._make_cached_request = original


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


def test_cache_shared_across_clients(client_config) -> None:
    """Test that caches are shared across client instances."""
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

    client_one._make_request("GET", "/test")
    client_two._make_request("GET", "/test")

    assert client_one._make_uncached_request.call_count == 1
    assert client_two._make_uncached_request.call_count == 0

    USASpendingClient._make_cached_request.clear_cache()
