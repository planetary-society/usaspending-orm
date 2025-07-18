"""Test 400 Bad Request error handling with detail property."""

from unittest.mock import Mock, patch
import pytest
import logging

from usaspending.client import USASpending
from usaspending.config import Config
from usaspending.exceptions import APIError, HTTPError


class TestClient:
    """Test that client properly handles 400 Bad Request responses with detail property."""
    
    def test_400_error_with_detail_property(self, mock_usa_client):
        """Test that 400 errors with detail property are handled correctly."""
        # Set up mock error response
        mock_usa_client.set_error_response(
            "/test",
            error_code=400,
            detail="Invalid request parameters"
        )
        
        # Expect APIError with detail message
        with pytest.raises(APIError) as exc_info:
            mock_usa_client._make_request("GET", "/test")
        
        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == "Invalid request parameters"
        assert exc_info.value.response_body["detail"] == "Invalid request parameters"
    
    def test_400_error_without_detail_property(self, mock_usa_client):
        """Test that 400 errors without detail property still raise APIError."""
        # Set up mock response with 400 status but no detail property
        mock_usa_client.set_error_response(
            "/test",
            error_code=400,
            error_message="Bad request"
        )
        
        # Expect APIError with error message (400s always raise APIError)
        with pytest.raises(APIError) as exc_info:
            mock_usa_client._make_request("GET", "/test")
        
        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == "Bad request"
    
    @patch('requests.Session.request')
    def test_400_error_with_invalid_json(self, mock_request):
        """Test that 400 errors with invalid JSON still raise APIError."""
        # Set up mock response with 400 status but invalid JSON
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.content = b'Invalid JSON'
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_request.return_value = mock_response
        
        # Create client with fast config (no retries)
        client = USASpending(Config(max_retries=0))
        
        # Expect APIError with generic 400 message since JSON parsing failed
        with pytest.raises(APIError) as exc_info:
            client._make_request("GET", "/test")
        
        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == "Bad Request - Invalid JSON response"
    
    def test_other_http_errors_unchanged(self, mock_usa_client):
        """Test that other HTTP errors (non-400) are handled as before."""
        # Set up mock error response with 500 status
        mock_usa_client.set_error_response(
            "/test",
            error_code=500,
            error_message="Internal Server Error"
        )
        
        # Expect HTTPError (not APIError) for non-400 errors
        with pytest.raises(HTTPError) as exc_info:
            mock_usa_client._make_request("GET", "/test")
        
        assert exc_info.value.status_code == 500
        assert "HTTP 500" in str(exc_info.value)
    
    def test_successful_response_with_detail_property(self, mock_usa_client):
        """Test that successful responses with detail property are not treated as errors."""
        # Set up mock response with 200 status but has detail property
        mock_usa_client.set_response(
            "/test",
            {"detail": "This is just data", "results": []}
        )
        
        # Should not raise an error and return the data
        result = mock_usa_client._make_request("GET", "/test")
        
        assert result == {"detail": "This is just data", "results": []}
    
    def test_400_error_with_json_parse_error_detail(self, mock_usa_client):
        """Test 400 error with JSON parse error detail message."""
        error_detail = "JSON parse error - Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"
        
        # Set up mock response with 400 status and JSON parse error detail
        mock_usa_client.set_error_response(
            "/test",
            error_code=400,
            detail=error_detail
        )
        
        # Expect APIError with detail message
        with pytest.raises(APIError) as exc_info:
            mock_usa_client._make_request("GET", "/test")
        
        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == error_detail
        assert exc_info.value.response_body["detail"] == error_detail
    
    @patch('requests.Session.request')
    def test_200_response_with_messages_list(self, mock_request, caplog):
        """Test that messages list in 200 response is logged at INFO level."""
        # Set up mock response with 200 status and messages list
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"results": [], "messages": ["Warning: Data may be incomplete", "Info: Processing complete"]}'
        mock_response.json.return_value = {
            "results": [],
            "messages": ["Warning: Data may be incomplete", "Info: Processing complete"]
        }
        mock_request.return_value = mock_response
        
        # Create client with fast config (no retries)
        client = USASpending(Config(max_retries=0))
        
        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            result = client._make_request("GET", "/test")
        
        # Verify response is returned successfully
        assert result == {"results": [], "messages": ["Warning: Data may be incomplete", "Info: Processing complete"]}
        
        # Verify messages are logged at INFO level
        info_messages = [record.message for record in caplog.records if record.levelname == 'INFO']
        assert "API Message: Warning: Data may be incomplete" in info_messages
        assert "API Message: Info: Processing complete" in info_messages
    
    @patch('requests.Session.request')
    def test_200_response_with_messages_string(self, mock_request, caplog):
        """Test that single message string in 200 response is logged at INFO level."""
        # Set up mock response with 200 status and single message
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"results": [], "messages": "Data successfully retrieved"}'
        mock_response.json.return_value = {
            "results": [],
            "messages": "Data successfully retrieved"
        }
        mock_request.return_value = mock_response
        
        # Create client with fast config (no retries)
        client = USASpending(Config(max_retries=0))
        
        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            result = client._make_request("GET", "/test")
        
        # Verify response is returned successfully
        assert result == {"results": [], "messages": "Data successfully retrieved"}
        
        # Verify message is logged at INFO level
        info_messages = [record.message for record in caplog.records if record.levelname == 'INFO']
        assert "API Message: Data successfully retrieved" in info_messages
    
    @patch('requests.Session.request')
    def test_200_response_without_messages(self, mock_request, caplog):
        """Test that 200 response without messages doesn't log anything extra."""
        # Set up mock response with 200 status but no messages
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"results": [{"id": 1}]}'
        mock_response.json.return_value = {"results": [{"id": 1}]}
        mock_request.return_value = mock_response
        
        # Create client with fast config (no retries)
        client = USASpending(Config(max_retries=0))
        
        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            result = client._make_request("GET", "/test")
        
        # Verify response is returned successfully
        assert result == {"results": [{"id": 1}]}
        
        # Verify no API Message logs (only standard request/response logs)
        info_messages = [record.message for record in caplog.records if record.levelname == 'INFO']
        api_messages = [msg for msg in info_messages if msg.startswith("API Message:")]
        assert len(api_messages) == 0
    
    @patch('requests.Session.request')
    def test_non_200_response_with_messages_not_logged(self, mock_request, caplog):
        """Test that messages in non-200 responses are not logged as API messages."""
        # Set up mock response with 201 status and messages
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"results": [], "messages": ["Resource created successfully"]}'
        mock_response.json.return_value = {
            "results": [],
            "messages": ["Resource created successfully"]
        }
        mock_request.return_value = mock_response
        
        # Create client with fast config (no retries)
        client = USASpending(Config(max_retries=0))
        
        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            result = client._make_request("POST", "/test")
        
        # Verify response is returned successfully
        assert result == {"results": [], "messages": ["Resource created successfully"]}
        
        # Verify no API Message logs for non-200 responses
        info_messages = [record.message for record in caplog.records if record.levelname == 'INFO']
        api_messages = [msg for msg in info_messages if msg.startswith("API Message:")]
        assert len(api_messages) == 0