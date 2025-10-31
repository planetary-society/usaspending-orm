"""Tests for caching fallback mechanisms.

This module tests the cache fallback behavior in the USASpendingClient,
ensuring that when the cache fails (due to locking issues, invalid data,
or other problems), the client gracefully falls back to making uncached
requests to maintain functionality.
"""

import pytest
from unittest.mock import Mock
from src.usaspending.exceptions import ValidationError


class TestCachingFallback:
    """Test caching fallback mechanisms."""

    def setup_method(self):
        """Set up test client with mocked methods."""
        from src.usaspending.client import USASpendingClient

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

    def test_cache_returns_none_fallback(self):
        """Test fallback when cache returns None."""
        # Setup: cache returns None
        self.client._make_cached_request.return_value = None

        # Execute: make request
        result = self.client._make_request("GET", "/test/endpoint/")

        # Assert: uncached request was called as fallback
        self.client._make_uncached_request.assert_called_once_with(
            "GET", "/test/endpoint/", params=None, json=None
        )
        assert result == {
            "name": "Test Recipient",
            "recipient_id": "test-123",
            "parents": [],
            "business_types": ["nonprofit"],
        }

    def test_cache_returns_invalid_type_fallback(self):
        """Test fallback when cache returns invalid type."""
        # Setup: cache returns string instead of dict
        self.client._make_cached_request.return_value = "invalid response"

        # Execute: make request
        result = self.client._make_request("GET", "/test/endpoint/")

        # Assert: uncached request was called as fallback
        self.client._make_uncached_request.assert_called_once()
        assert isinstance(result, dict)

    def test_cache_exception_fallback(self):
        """Test fallback when cache raises exception."""
        # Setup: cache raises exception
        self.client._make_cached_request.side_effect = Exception("Cache locked")

        # Execute: make request
        result = self.client._make_request("GET", "/test/endpoint/")

        # Assert: uncached request was called as fallback
        self.client._make_uncached_request.assert_called_once()
        assert isinstance(result, dict)

    def test_cache_disabled_fallback(self):
        """Test behavior when cache is disabled."""
        from src.usaspending.config import config

        original_cache_enabled = config.cache_enabled

        try:
            # Disable cache
            config.cache_enabled = False

            # Execute: make request
            result = self.client._make_request("GET", "/test/endpoint/")

            # Assert: uncached request was called directly
            self.client._make_uncached_request.assert_called_once()
            assert isinstance(result, dict)

        finally:
            # Restore original setting
            config.cache_enabled = original_cache_enabled

    def test_api_errors_dont_trigger_duplicate_calls(self):
        """Test that API errors don't cause duplicate calls due to fallback logic."""
        from src.usaspending.exceptions import APIError
        from src.usaspending.config import config

        original_cache_enabled = config.cache_enabled

        try:
            # Enable cache to test cache error propagation
            config.cache_enabled = True

            # Setup: cache raises API error (simulating failed API call)
            api_error = APIError("Invalid Recipient ID", status_code=400)
            self.client._make_cached_request.side_effect = api_error

            # Execute: make request and expect API error to propagate
            with pytest.raises(APIError) as exc_info:
                self.client._make_request("GET", "/recipient/invalid-id/")

            # Assert: API error propagated without fallback
            assert str(exc_info.value) == "Invalid Recipient ID"
            # Uncached request should NOT have been called (no fallback for API errors)
            self.client._make_uncached_request.assert_not_called()

        finally:
            # Restore original setting
            config.cache_enabled = original_cache_enabled

    def test_http_errors_dont_trigger_duplicate_calls(self):
        """Test that HTTP errors don't cause duplicate calls due to fallback logic."""
        from src.usaspending.exceptions import HTTPError
        from src.usaspending.config import config

        original_cache_enabled = config.cache_enabled

        try:
            # Enable cache to test cache error propagation
            config.cache_enabled = True

            # Setup: cache raises HTTP error (simulating HTTP failure)
            http_error = HTTPError("Not Found", status_code=404)
            self.client._make_cached_request.side_effect = http_error

            # Execute: make request and expect HTTP error to propagate
            with pytest.raises(HTTPError) as exc_info:
                self.client._make_request("GET", "/recipient/not-found/")

            # Assert: HTTP error propagated without fallback
            assert exc_info.value.status_code == 404
            # Uncached request should NOT have been called (no fallback for HTTP errors)
            self.client._make_uncached_request.assert_not_called()

        finally:
            # Restore original setting
            config.cache_enabled = original_cache_enabled

    def test_validation_errors_dont_trigger_duplicate_calls(self):
        """Test that ValidationError doesn't cause duplicate calls due to fallback logic."""
        from src.usaspending.config import config

        original_cache_enabled = config.cache_enabled

        try:
            # Enable cache to test cache error propagation
            config.cache_enabled = True

            # Setup: cache raises validation error (simulating input validation failure)
            validation_error = ValidationError("Invalid input parameters")
            self.client._make_cached_request.side_effect = validation_error

            # Execute: make request and expect validation error to propagate
            with pytest.raises(ValidationError) as exc_info:
                self.client._make_request("GET", "/recipient/invalid-params/")

            # Assert: Validation error propagated without fallback
            assert str(exc_info.value) == "Invalid input parameters"
            # Uncached request should NOT have been called (no fallback for validation errors)
            self.client._make_uncached_request.assert_not_called()

        finally:
            # Restore original setting
            config.cache_enabled = original_cache_enabled
