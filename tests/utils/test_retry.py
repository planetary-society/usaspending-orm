"""Tests for the RetryHandler class."""

from __future__ import annotations

import time
from unittest.mock import Mock, patch

import pytest
import requests

from usaspending.config import Config
from usaspending.exceptions import APIError, HTTPError, RateLimitError
from usaspending.utils.retry import RetryHandler


class TestRetryHandlerInitialization:
    """Test RetryHandler initialization."""
    
    def test_initialization_with_config(self):
        """Test creating a retry handler with configuration."""
        config = Config(
            max_retries=5,
            retry_delay=2.0,
            retry_backoff=1.5
        )
        handler = RetryHandler(config)
        
        assert handler.max_retries == 5
        assert handler.base_delay == 2.0
        assert handler.backoff_factor == 1.5


class TestRetryHandlerSuccessfulExecution:
    """Test successful execution without retries."""
    
    def test_execute_successful_function(self):
        """Test executing a function that succeeds on first try."""
        config = Config()
        handler = RetryHandler(config)
        
        mock_func = Mock(return_value="success")
        result = handler.execute(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_execute_successful_http_response(self):
        """Test executing a function that returns a successful HTTP response."""
        config = Config()
        handler = RetryHandler(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_func = Mock(return_value=mock_response)
        
        result = handler.execute(mock_func)
        
        assert result == mock_response
        mock_func.assert_called_once()


class TestRetryHandlerRetryableErrors:
    """Test retry behavior for retryable errors."""
    
    def test_retry_on_connection_error(self):
        """Test that connection errors are retried."""
        config = Config(max_retries=2, retry_delay=0.01)
        handler = RetryHandler(config)
        
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            "success"
        ])
        
        result = handler.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retry_on_timeout_error(self):
        """Test that timeout errors are retried."""
        config = Config(max_retries=1, retry_delay=0.01)
        handler = RetryHandler(config)
        
        mock_func = Mock(side_effect=[
            requests.exceptions.Timeout("Request timed out"),
            "success"
        ])
        
        result = handler.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_retry_on_server_error_response(self):
        """Test that 5xx server errors are retried."""
        config = Config(max_retries=2, retry_delay=0.01)
        handler = RetryHandler(config)
        
        # First two calls return 500 errors, third succeeds
        error_response = Mock()
        error_response.status_code = 500
        
        success_response = Mock()
        success_response.status_code = 200
        
        mock_func = Mock(side_effect=[error_response, error_response, success_response])
        
        result = handler.execute(mock_func)
        
        assert result == success_response
        assert mock_func.call_count == 3
    
    def test_retry_on_rate_limit_response(self):
        """Test that 429 rate limit errors are retried."""
        config = Config(max_retries=1, retry_delay=0.01)
        handler = RetryHandler(config)
        
        # First call returns 429, second succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}
        
        success_response = Mock()
        success_response.status_code = 200
        
        mock_func = Mock(side_effect=[rate_limit_response, success_response])
        
        result = handler.execute(mock_func)
        
        assert result == success_response
        assert mock_func.call_count == 2
    
    @patch('time.sleep')
    def test_retry_with_exponential_backoff(self, mock_sleep):
        """Test that exponential backoff is applied correctly."""
        config = Config(max_retries=3, retry_delay=1.0, retry_backoff=2.0)
        handler = RetryHandler(config)
        
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            "success"
        ])
        
        result = handler.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 4
        
        # Check that sleep was called with increasing delays
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert len(sleep_calls) == 3
        
        # Each delay should be approximately base_delay * backoff_factor^attempt
        # (with some jitter, so we check ranges)
        assert 1.0 <= sleep_calls[0] <= 1.5   # 1.0 * 2^0 + jitter
        assert 2.0 <= sleep_calls[1] <= 3.0   # 1.0 * 2^1 + jitter
        assert 4.0 <= sleep_calls[2] <= 6.0   # 1.0 * 2^2 + jitter


class TestRetryHandlerRateLimitHandling:
    """Test specific rate limit handling."""
    
    @patch('time.sleep')
    def test_rate_limit_with_retry_after_header(self, mock_sleep):
        """Test that Retry-After header is respected for rate limits."""
        config = Config(max_retries=1, retry_delay=0.1)
        handler = RetryHandler(config)
        
        # Mock response with Retry-After header
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '5'}
        
        success_response = Mock()
        success_response.status_code = 200
        
        mock_func = Mock(side_effect=[rate_limit_response, success_response])
        
        result = handler.execute(mock_func)
        
        assert result == success_response
        # Should sleep for exactly 5 seconds as specified in Retry-After
        mock_sleep.assert_called_once_with(5.0)
    
    @patch('time.sleep')
    def test_rate_limit_without_retry_after_header(self, mock_sleep):
        """Test rate limit handling when no Retry-After header is present."""
        config = Config(max_retries=1, retry_delay=1.0, retry_backoff=2.0)
        handler = RetryHandler(config)
        
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}
        
        success_response = Mock()
        success_response.status_code = 200
        
        mock_func = Mock(side_effect=[rate_limit_response, success_response])
        
        result = handler.execute(mock_func)
        
        assert result == success_response
        # Should use exponential backoff
        assert mock_sleep.called


class TestRetryHandlerNonRetryableErrors:
    """Test behavior for non-retryable errors."""
    
    def test_no_retry_on_client_errors(self):
        """Test that 4xx client errors (except 429) are not retried."""
        config = Config(max_retries=3)
        handler = RetryHandler(config)
        
        client_error_response = Mock()
        client_error_response.status_code = 400
        
        mock_func = Mock(return_value=client_error_response)
        
        result = handler.execute(mock_func)
        
        assert result == client_error_response
        mock_func.assert_called_once()  # No retries
    
    def test_no_retry_on_authentication_errors(self):
        """Test that authentication errors are not retried."""
        config = Config(max_retries=3)
        handler = RetryHandler(config)
        
        auth_error_response = Mock()
        auth_error_response.status_code = 401
        
        mock_func = Mock(return_value=auth_error_response)
        
        result = handler.execute(mock_func)
        
        assert result == auth_error_response
        mock_func.assert_called_once()  # No retries
    
    def test_no_retry_on_non_http_exceptions(self):
        """Test that non-HTTP exceptions are not retried."""
        config = Config(max_retries=3)
        handler = RetryHandler(config)
        
        mock_func = Mock(side_effect=ValueError("Invalid input"))
        
        with pytest.raises(ValueError, match="Invalid input"):
            handler.execute(mock_func)
        
        mock_func.assert_called_once()  # No retries


class TestRetryHandlerExhaustionBehavior:
    """Test behavior when all retries are exhausted."""
    
    def test_exhausted_retries_raises_last_exception(self):
        """Test that the last exception is raised when retries are exhausted."""
        config = Config(max_retries=2, retry_delay=0.01)
        handler = RetryHandler(config)
        
        mock_func = Mock(side_effect=requests.exceptions.ConnectionError("Persistent error"))
        
        with pytest.raises(requests.exceptions.ConnectionError, match="Persistent error"):
            handler.execute(mock_func)
        
        # Should try initial + 2 retries = 3 total
        assert mock_func.call_count == 3
    
    def test_exhausted_retries_with_mixed_errors(self):
        """Test retry exhaustion with different types of errors."""
        config = Config(max_retries=2, retry_delay=0.01)
        handler = RetryHandler(config)
        
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError("First error"),
            requests.exceptions.Timeout("Second error"),
            requests.exceptions.ConnectionError("Final error")
        ])
        
        with pytest.raises(requests.exceptions.ConnectionError, match="Final error"):
            handler.execute(mock_func)
        
        assert mock_func.call_count == 3


class TestRetryHandlerEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_zero_max_retries(self):
        """Test behavior when max_retries is 0."""
        config = Config(max_retries=0)
        handler = RetryHandler(config)
        
        mock_func = Mock(side_effect=requests.exceptions.ConnectionError("Error"))
        
        with pytest.raises(requests.exceptions.ConnectionError):
            handler.execute(mock_func)
        
        mock_func.assert_called_once()  # No retries
    
    def test_invalid_retry_after_header(self):
        """Test handling of invalid Retry-After header values."""
        config = Config(max_retries=1, retry_delay=0.01)
        handler = RetryHandler(config)
        
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': 'invalid'}
        
        success_response = Mock()
        success_response.status_code = 200
        
        mock_func = Mock(side_effect=[rate_limit_response, success_response])
        
        # Should still work, falling back to exponential backoff
        result = handler.execute(mock_func)
        assert result == success_response
    
    def test_response_without_status_code(self):
        """Test handling of responses that don't have status_code attribute."""
        config = Config()
        handler = RetryHandler(config)
        
        # Mock object without status_code attribute
        mock_response = Mock(spec=[])  # Empty spec = no attributes
        mock_func = Mock(return_value=mock_response)
        
        result = handler.execute(mock_func)
        
        assert result == mock_response
        mock_func.assert_called_once()
    
    @patch('random.random', return_value=0.5)
    @patch('time.sleep')
    def test_jitter_calculation(self, mock_sleep, mock_random):
        """Test that jitter is applied to delay calculations."""
        config = Config(max_retries=1, retry_delay=4.0, retry_backoff=1.0)
        handler = RetryHandler(config)
        
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError(),
            "success"
        ])
        
        result = handler.execute(mock_func)
        
        assert result == "success"
        
        # Expected delay: 4.0 + (4.0 * 0.25 * 0.5) = 4.0 + 0.5 = 4.5
        mock_sleep.assert_called_once_with(4.5)
    
    def test_retryable_status_codes_coverage(self):
        """Test that all expected status codes are marked as retryable."""
        expected_codes = {429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
        assert RetryHandler.RETRYABLE_STATUS_CODES == expected_codes
    
    def test_retryable_exceptions_coverage(self):
        """Test that expected exception types are marked as retryable."""
        expected_exceptions = (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
        )
        assert RetryHandler.RETRYABLE_EXCEPTIONS == expected_exceptions


class TestRetryHandlerIntegration:
    """Integration tests for retry handler."""
    
    @patch('time.sleep')
    def test_realistic_api_failure_scenario(self, mock_sleep):
        """Test a realistic scenario with mixed failures."""
        config = Config(max_retries=4, retry_delay=0.1, retry_backoff=2.0)
        handler = RetryHandler(config)
        
        # Simulate various types of failures followed by success
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError("Network issue"),
            Mock(status_code=503),  # Service unavailable
            Mock(status_code=429, headers={'Retry-After': '1'}),  # Rate limit
            requests.exceptions.Timeout("Request timeout"),
            Mock(status_code=200)  # Success
        ])
        
        result = handler.execute(mock_func)
        
        assert result.status_code == 200
        assert mock_func.call_count == 5
        
        # Verify sleep was called for retries
        assert mock_sleep.call_count == 4
        
        # Third call should use Retry-After value of 1 second
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_calls[2] == 1.0  # Retry-After header value