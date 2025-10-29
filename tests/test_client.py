"""Test 400 Bad Request error handling with detail property."""

import pytest
import logging
import unittest.mock

from usaspending import USASpendingClient
from usaspending.exceptions import APIError, HTTPError


class TestClient:
    """Test that client properly handles 400 Bad Request responses with detail property."""

    def test_400_error_with_detail_property(self, mock_usa_client):
        """Test that 400 errors with detail property are handled correctly."""
        # Set up mock error response
        mock_usa_client.set_error_response(
            "/test", error_code=400, detail="Invalid request parameters"
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
            "/test", error_code=400, error_message="Bad request"
        )

        # Expect APIError with error message (400s always raise APIError)
        with pytest.raises(APIError) as exc_info:
            mock_usa_client._make_request("GET", "/test")

        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == "Bad request"

    def test_400_error_with_invalid_json(self, mock_usa_client):
        """Test that 400 errors with invalid JSON still raise APIError."""
        # Set up mock response with 400 status and invalid JSON content
        mock_usa_client.set_error_response(
            "/test", error_code=400, error_message="Bad Request - Invalid JSON response"
        )

        # Expect APIError with generic 400 message since JSON parsing failed
        with pytest.raises(APIError) as exc_info:
            mock_usa_client._make_request("GET", "/test")

        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == "Bad Request - Invalid JSON response"

    def test_other_http_errors_unchanged(self, mock_usa_client):
        """Test that other HTTP errors (non-400) are handled as before."""
        # Set up mock error response with 500 status
        mock_usa_client.set_error_response(
            "/test", error_code=500, error_message="Internal Server Error"
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
            "/test", {"detail": "This is just data", "results": []}
        )

        # Should not raise an error and return the data
        result = mock_usa_client._make_request("GET", "/test")

        assert result == {"detail": "This is just data", "results": []}

    def test_400_error_with_json_parse_error_detail(self, mock_usa_client):
        """Test 400 error with JSON parse error detail message."""
        error_detail = "JSON parse error - Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"

        # Set up mock response with 400 status and JSON parse error detail
        mock_usa_client.set_error_response("/test", error_code=400, detail=error_detail)

        # Expect APIError with detail message
        with pytest.raises(APIError) as exc_info:
            mock_usa_client._make_request("GET", "/test")

        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == error_detail
        assert exc_info.value.response_body["detail"] == error_detail

    def test_200_response_with_messages_list(self, mock_usa_client, caplog):
        """Test that messages list in 200 response is logged at INFO level."""
        # Set up mock response with 200 status and messages list
        mock_usa_client.set_response(
            "/test",
            {
                "results": [],
                "messages": [
                    "Warning: Data may be incomplete",
                    "Info: Processing complete",
                ],
            },
        )

        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            result = mock_usa_client._make_request("GET", "/test")

        # Verify response is returned successfully
        assert result == {
            "results": [],
            "messages": [
                "Warning: Data may be incomplete",
                "Info: Processing complete",
            ],
        }

        # Verify messages are logged at INFO level
        info_messages = [
            record.message for record in caplog.records if record.levelname == "INFO"
        ]
        assert "API Message: Warning: Data may be incomplete" in info_messages
        assert "API Message: Info: Processing complete" in info_messages

    def test_200_response_with_messages_string(self, mock_usa_client, caplog):
        """Test that single message string in 200 response is logged at INFO level."""
        # Set up mock response with 200 status and single message
        mock_usa_client.set_response(
            "/test", {"results": [], "messages": "Data successfully retrieved"}
        )

        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            result = mock_usa_client._make_request("GET", "/test")

        # Verify response is returned successfully
        assert result == {"results": [], "messages": "Data successfully retrieved"}

        # Verify message is logged at INFO level
        info_messages = [
            record.message for record in caplog.records if record.levelname == "INFO"
        ]
        assert "API Message: Data successfully retrieved" in info_messages

    def test_200_response_without_messages(self, mock_usa_client, caplog):
        """Test that 200 response without messages doesn't log anything extra."""
        # Set up mock response with 200 status but no messages
        mock_usa_client.set_response("/test", {"results": [{"id": 1}]})

        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            result = mock_usa_client._make_request("GET", "/test")

        # Verify response is returned successfully
        assert result == {"results": [{"id": 1}]}

        # Verify no API Message logs (only standard request/response logs)
        info_messages = [
            record.message for record in caplog.records if record.levelname == "INFO"
        ]
        api_messages = [msg for msg in info_messages if msg.startswith("API Message:")]
        assert len(api_messages) == 0

    def test_non_200_response_with_messages_not_logged(self, mock_usa_client, caplog):
        """Test that messages in non-200 responses are not logged as API messages."""
        # Note: This test can't easily simulate non-200 success responses with mock_usa_client
        # since it's designed to mock 200 responses. This test would need real HTTP mocking
        # to properly test status code 201. For now, we'll skip this specific scenario.
        pytest.skip("MockUSASpendingClient doesn't support non-200 success responses")


class TestClientSessionManagement:
    """Test session management functionality in USASpendingClient."""

    def test_context_manager_functionality(self):
        """Test that client works as context manager."""
        with USASpendingClient() as client:
            assert client is not None
            assert hasattr(client, "_session")
            assert not client._closed

        # After exiting context, session should be closed
        assert client._closed

    def test_context_manager_calls_close(self):
        """Test that context manager properly calls close()."""
        client = USASpendingClient()

        # Mock the close method to verify it's called
        with unittest.mock.patch.object(client, "close") as mock_close:
            with client:
                pass
            mock_close.assert_called_once()

    def test_manual_close(self):
        """Test manual close functionality."""
        client = USASpendingClient()
        assert not client._closed

        # Mock session.close to verify it's called
        with unittest.mock.patch.object(client._session, "close") as mock_session_close:
            client.close()
            mock_session_close.assert_called_once()

        assert client._closed

    def test_close_is_idempotent(self):
        """Test that close can be called multiple times safely."""
        client = USASpendingClient()

        # Mock session.close to count calls
        with unittest.mock.patch.object(client._session, "close") as mock_session_close:
            client.close()
            client.close()  # Should not call session.close again
            client.close()  # Should not call session.close again

            # Session.close should only be called once
            mock_session_close.assert_called_once()

        assert client._closed

    def test_destructor_cleanup(self, caplog):
        """Test that destructor closes session if not already closed."""
        with caplog.at_level(logging.WARNING):
            client = USASpendingClient()

            # Mock session.close to verify it's called
            with unittest.mock.patch.object(
                client._session, "close"
            ) as mock_session_close:
                # Trigger destructor by deleting reference
                del client
                mock_session_close.assert_called_once()

        # Should log warning about improper cleanup
        assert "session was not explicitly closed" in caplog.text
        assert "Consider using 'with USASpendingClient() as client:'" in caplog.text

    def test_destructor_no_warning_if_already_closed(self, caplog):
        """Test that destructor doesn't warn if session already closed."""
        with caplog.at_level(logging.WARNING):
            client = USASpendingClient()
            client.close()  # Properly close first

            # Trigger destructor
            del client

        # Should not log warning
        warning_messages = [
            record.message for record in caplog.records if record.levelname == "WARNING"
        ]
        session_warnings = [
            msg
            for msg in warning_messages
            if "session was not explicitly closed" in msg
        ]
        assert len(session_warnings) == 0

    def test_context_manager_with_exception(self):
        """Test that session is closed even if exception occurs in context."""
        client = None

        try:
            with USASpendingClient() as client:
                assert not client._closed
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Session should still be closed despite exception
        assert client._closed

    def test_enter_returns_self(self):
        """Test that __enter__ returns self."""
        client = USASpendingClient()
        assert client.__enter__() is client

    def test_enhanced_close_logging(self, caplog):
        """Test that close() logs request count at INFO level."""
        client = USASpendingClient()
        client._request_count = 42

        with caplog.at_level(logging.INFO):
            client.close()

        info_messages = [
            record.message for record in caplog.records if record.levelname == "INFO"
        ]
        assert any(
            "USASpending client closed after 42 requests" in msg
            for msg in info_messages
        )

    def test_enhanced_destructor_logging(self, caplog):
        """Test that destructor logs request count with warning."""
        with caplog.at_level(logging.WARNING):
            client = USASpendingClient()
            client._request_count = 123

            # Simulate destructor being called
            client.__del__()

        warning_messages = [
            record.message for record in caplog.records if record.levelname == "WARNING"
        ]
        assert any("after 123 requests" in msg for msg in warning_messages)

    def test_error_logging_includes_request_count(self, caplog):
        """Test that error responses include request count in logging."""
        client = USASpendingClient()
        client._request_count = 50

        # Mock a 400 response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 400
        mock_response.content = b'{"detail": "Test error"}'
        mock_response.json.return_value = {"detail": "Test error"}

        with caplog.at_level(logging.ERROR):
            with unittest.mock.patch.object(
                client._session, "request", return_value=mock_response
            ):
                with pytest.raises(APIError):
                    client._make_uncached_request("GET", "/test")

        error_messages = [
            record.message for record in caplog.records if record.levelname == "ERROR"
        ]
        assert any("Request #51 in session" in msg for msg in error_messages)

    def test_error_logging_with_session_limit_warning(self, caplog):
        """Test that errors near session limit include warning context."""
        from usaspending import config
        import requests

        client = USASpendingClient()
        # Set request count close to session limit
        client._request_count = config.session_request_limit - 5

        # Mock a 500 response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 500
        mock_response.content = b"Server Error"
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "500 Server Error"
        )

        with caplog.at_level(logging.ERROR):
            with unittest.mock.patch.object(
                client._session, "request", return_value=mock_response
            ):
                with pytest.raises(HTTPError):
                    client._make_uncached_request("GET", "/test")

        error_messages = [
            record.message for record in caplog.records if record.levelname == "ERROR"
        ]
        # Should include warning about remaining requests before reset
        assert any("remaining before reset" in msg for msg in error_messages)

    def test_request_counter_increments(self, mock_usa_client):
        """Test that request counter increments with each request."""
        assert mock_usa_client._request_count == 0

        # Mock successful response
        mock_usa_client.set_response("/test", {"result": "success"})

        mock_usa_client._make_uncached_request("GET", "/test")
        assert mock_usa_client._request_count == 1

        mock_usa_client._make_uncached_request("GET", "/test")
        assert mock_usa_client._request_count == 2

    def test_session_reset_functionality(self):
        """Test that session reset creates new session and resets counter."""
        client = USASpendingClient()
        client._request_count = 100
        original_session = client._session

        client.reset_session()

        # Should have new session object
        assert client._session is not original_session
        # Counter should be reset
        assert client._request_count == 0
        # Should not be closed
        assert not client._closed

    def test_proactive_session_reset(self, mock_usa_client):
        """Test that session resets proactively when hitting request limit."""
        from usaspending import config

        # Set counter just below limit
        mock_usa_client._request_count = config.session_request_limit - 1
        original_session = mock_usa_client._session

        # Mock successful response
        mock_usa_client.set_response("/test", {"result": "success"})

        # This request should trigger proactive reset
        mock_usa_client._make_uncached_request("GET", "/test")

        # Session should be reset
        assert mock_usa_client._session is not original_session
        # Counter was incremented to trigger reset, then reset to 0
        # The current request doesn't increment again since it already incremented before reset
        assert mock_usa_client._request_count == 0
