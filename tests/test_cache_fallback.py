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
            "business_types": ["nonprofit"]
        }
        
        # Mock the cached request method
        self.client._make_cached_request = Mock()
    
    def teardown_method(self):
        """Clean up test client after each test."""
        if hasattr(self, 'client') and self.client:
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
            "business_types": ["nonprofit"]
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