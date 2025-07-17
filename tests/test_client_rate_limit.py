"""Test rate limiter integration with USASpending client."""

from unittest.mock import Mock, patch
import time

import pytest

from usaspending.client import USASpending
from usaspending.config import Config


class TestClientRateLimitIntegration:
    """Test that the client properly integrates with the rate limiter."""
    
    def test_client_creates_rate_limiter(self):
        """Test that client creates rate limiter with correct config."""
        config = Config(rate_limit_calls=10, rate_limit_period=2.0)
        client = USASpending(config)
        
        # Access the rate limiter
        limiter = client.rate_limiter
        
        assert limiter is not None
        assert limiter.max_calls == 10
        assert limiter.period == 2.0
        assert limiter.available_calls == 10
    
    def test_client_caches_rate_limiter(self):
        """Test that client returns the same rate limiter instance."""
        config = Config()
        client = USASpending(config)
        
        limiter1 = client.rate_limiter
        limiter2 = client.rate_limiter
        
        assert limiter1 is limiter2
    
    @patch('requests.Session.request')
    def test_make_request_uses_rate_limiter(self, mock_request):
        """Test that _make_request calls the rate limiter."""
        # Set up mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"results": []}'
        mock_response.json.return_value = {"results": []}
        mock_request.return_value = mock_response
        
        # Create client with tight rate limit
        config = Config(rate_limit_calls=2, rate_limit_period=0.5)
        client = USASpending(config)
        
        # Make 3 requests
        start_time = time.time()
        client._make_request("GET", "/test1")
        client._make_request("GET", "/test2")
        client._make_request("GET", "/test3")  # This should wait
        elapsed = time.time() - start_time
        
        # Should have waited for rate limit
        assert elapsed >= 0.4  # Close to 0.5s period
        assert mock_request.call_count == 3
    
    @patch('requests.Session.request')
    def test_rate_limit_shared_across_resources(self, mock_request):
        """Test that rate limit is shared across different resources."""
        # Set up mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"results": []}'
        mock_response.json.return_value = {"results": []}
        mock_request.return_value = mock_response
        
        # Create client with rate limit of 1 per second
        config = Config(rate_limit_calls=1, rate_limit_period=1.0)
        client = USASpending(config)
        
        # Make requests through different paths
        start_time = time.time()
        client._make_request("GET", "/api/v2/awards/1/")
        client._make_request("GET", "/api/v2/recipients/2/")  # Should wait
        elapsed = time.time() - start_time
        
        # Should have waited due to shared rate limit
        assert elapsed >= 0.9
        assert mock_request.call_count == 2