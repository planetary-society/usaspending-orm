"""Tests for the RetryHandler class."""

from __future__ import annotations
from unittest.mock import Mock
import requests
from usaspending.config import config
from usaspending.utils.retry import RetryHandler


class TestRetryHandlerInitialization:
    """Test RetryHandler initialization."""
    
    def test_initialization_with_config(self):
        """Test creating a retry handler with configuration."""
        # Use default config - the test values don't match defaults but that's ok for this basic test
        handler = RetryHandler()
        
        # These assertions will use the default config values from Config class
        assert handler.max_retries == config.max_retries
        assert handler.base_delay == config.retry_delay
        assert handler.backoff_factor == config.retry_backoff


class TestRetryHandlerSuccessfulExecution:
    """Test successful execution without retries."""
    
    def test_execute_successful_function(self):
        """Test executing a function that succeeds on first try."""
        handler = RetryHandler()
        
        mock_func = Mock(return_value="success")
        result = handler.execute(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_execute_successful_http_response(self):
        """Test executing a function that returns a successful HTTP response."""
        handler = RetryHandler()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_func = Mock(return_value=mock_response)
        
        result = handler.execute(mock_func)
        
        assert result == mock_response
        mock_func.assert_called_once()


class TestRetryHandlerRetryableErrors:
    """Test retry behavior for retryable errors."""
    
    def test_retry_on_connection_error(self,client_config):
        """Test that connection errors are retried."""
        client_config(max_retries=3, timeout=0.01)
        handler = RetryHandler()
        
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            "success"
        ])
        
        result = handler.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 4  # 1 initial + 3 retries (using default max_retries=3)


class TestRetryHandlerNonRetryableErrors:
    """Test behavior for non-retryable errors."""
    
    def test_no_retry_on_client_errors(self):
        """Test that 4xx client errors (except 429) are not retried."""
        handler = RetryHandler()
        
        client_error_response = Mock()
        client_error_response.status_code = 400
        
        mock_func = Mock(return_value=client_error_response)
        
        result = handler.execute(mock_func)
        
        assert result == client_error_response
        mock_func.assert_called_once()  # No retries


class TestRetryHandlerEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_response_without_status_code(self):
        """Test handling of responses that don't have status_code attribute."""
        handler = RetryHandler()
        
        # Mock object without status_code attribute
        mock_response = Mock(spec=[])  # Empty spec = no attributes
        mock_func = Mock(return_value=mock_response)
        
        result = handler.execute(mock_func)
        
        assert result == mock_response
        mock_func.assert_called_once()
    
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
