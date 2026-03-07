"""Tests for caching fallback mechanisms.

This module tests the cache fallback behavior in the USASpendingClient,
ensuring that when the cache fails (due to locking issues, invalid data,
or other problems), the client gracefully falls back to making uncached
requests to maintain functionality.
"""

from unittest.mock import Mock

import pytest

from usaspending.client import USASpendingClient
from usaspending.exceptions import APIError, HTTPError, ValidationError


class TestCachingFallback:
    """Test caching fallback mechanisms."""

    def setup_method(self):
        """Set up test client with mocked methods."""
        self.client = USASpendingClient()

        # Mock the uncached request method
        self.client._make_uncached_request = Mock()
        self.client._make_uncached_request.return_value = {
            "name": "Test Recipient",
            "recipient_id": "test-123",
            "parents": [],
            "business_types": ["nonprofit"],
        }

        # Mock the cached request method
        self.client._make_cached_request = Mock()

    def teardown_method(self):
        """Clean up test client after each test."""
        if hasattr(self, "client") and self.client:
            self.client.close()

    def test_cache_returns_none_fallback(self, client_config):
        """Test fallback when cache returns None."""
        client_config(cache_enabled=True)
        self.client._make_cached_request.return_value = None

        result = self.client._make_request("GET", "/test/endpoint/")

        self.client._make_uncached_request.assert_called_once_with(
            "GET", "/test/endpoint/", params=None, json=None
        )
        assert result == {
            "name": "Test Recipient",
            "recipient_id": "test-123",
            "parents": [],
            "business_types": ["nonprofit"],
        }

    def test_cache_returns_invalid_type_fallback(self, client_config):
        """Test fallback when cache returns invalid type."""
        client_config(cache_enabled=True)
        self.client._make_cached_request.return_value = "invalid response"

        result = self.client._make_request("GET", "/test/endpoint/")

        self.client._make_uncached_request.assert_called_once()
        assert isinstance(result, dict)

    def test_cache_exception_fallback(self, client_config):
        """Test fallback when cache raises exception."""
        client_config(cache_enabled=True)
        self.client._make_cached_request.side_effect = Exception("Cache locked")

        result = self.client._make_request("GET", "/test/endpoint/")

        self.client._make_uncached_request.assert_called_once()
        assert isinstance(result, dict)

    def test_cache_disabled_fallback(self):
        """Test behavior when cache is disabled.

        The default_test_config autouse fixture sets cache_enabled=False,
        so no explicit configuration is needed here.
        """
        result = self.client._make_request("GET", "/test/endpoint/")

        self.client._make_uncached_request.assert_called_once()
        assert isinstance(result, dict)

    def test_api_errors_dont_trigger_duplicate_calls(self, client_config):
        """Test that API errors don't cause duplicate calls due to fallback logic."""
        client_config(cache_enabled=True)
        self.client._make_cached_request.side_effect = APIError(
            "Invalid Recipient ID", status_code=400
        )

        with pytest.raises(APIError) as exc_info:
            self.client._make_request("GET", "/recipient/invalid-id/")

        assert str(exc_info.value) == "Invalid Recipient ID"
        self.client._make_uncached_request.assert_not_called()

    def test_http_errors_dont_trigger_duplicate_calls(self, client_config):
        """Test that HTTP errors don't cause duplicate calls due to fallback logic."""
        client_config(cache_enabled=True)
        self.client._make_cached_request.side_effect = HTTPError(
            "Not Found", status_code=404
        )

        with pytest.raises(HTTPError) as exc_info:
            self.client._make_request("GET", "/recipient/not-found/")

        assert exc_info.value.status_code == 404
        self.client._make_uncached_request.assert_not_called()

    def test_validation_errors_dont_trigger_duplicate_calls(self, client_config):
        """Test that ValidationError doesn't cause duplicate calls due to fallback logic."""
        client_config(cache_enabled=True)
        self.client._make_cached_request.side_effect = ValidationError(
            "Invalid input parameters"
        )

        with pytest.raises(ValidationError) as exc_info:
            self.client._make_request("GET", "/recipient/invalid-params/")

        assert str(exc_info.value) == "Invalid input parameters"
        self.client._make_uncached_request.assert_not_called()
