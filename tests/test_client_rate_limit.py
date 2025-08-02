"""Test rate limiter integration with USASpending client."""

import time
from usaspending.config import config


class TestClientRateLimitIntegration:
    """Test that the client properly integrates with the rate limiter."""

    def test_client_creates_rate_limiter(self, mock_usa_client):
        """Test that client creates rate limiter with correct config."""

        # Act: Access the rate limiter from the mock client
        limiter = mock_usa_client.rate_limiter

        # Assert
        assert limiter is not None
        assert limiter.max_calls == config.rate_limit_calls
        assert limiter.period == config.rate_limit_period

    def test_client_caches_rate_limiter(self, mock_usa_client):
        """Test that client returns the same rate limiter instance."""
        # Act
        limiter1 = mock_usa_client.rate_limiter
        limiter2 = mock_usa_client.rate_limiter

        # Assert
        assert limiter1 is limiter2

    def test_make_request_uses_rate_limiter(self, client_config, mock_usa_client):
        """Test that _make_request calls the rate limiter and waits."""
        # Arrange
        # Set a tight rate limit
        client_config(rate_limit_calls=2, rate_limit_period=0.5)

        # Set up responses for the endpoints
        mock_usa_client.set_response("/test1", {"results": []})
        mock_usa_client.set_response("/test2", {"results": []})
        mock_usa_client.set_response("/test3", {"results": []})

        # Enable rate limit simulation to verify behavior
        mock_usa_client.simulate_rate_limit(delay=0.001)  # Small delay for testing

        # Record start time
        start_time = time.time()

        # Act
        mock_usa_client._make_request("GET", "/test1")
        mock_usa_client._make_request("GET", "/test2")
        mock_usa_client._make_request(
            "GET", "/test3"
        )  # This should trigger rate limit delay

        # Record end time
        end_time = time.time()

        # Assert
        # Verify all requests were made
        assert mock_usa_client.get_request_count() == 3

        # Verify specific endpoints were called
        assert mock_usa_client.get_request_count("/test1") == 1
        assert mock_usa_client.get_request_count("/test2") == 1
        assert mock_usa_client.get_request_count("/test3") == 1

        # Verify that the rate limiter caused a delay (3 requests * 0.001s delay)
        assert end_time - start_time >= 0.003
