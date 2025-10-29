"""Test session reset functionality in RetryHandler."""

import pytest
import unittest.mock
import logging

from usaspending.utils.retry import RetryHandler
from usaspending.exceptions import HTTPError
from usaspending import config


@pytest.fixture
def reset_config():
    """Reset config to defaults for testing."""
    # Store original values
    original_max_retries = config.max_retries
    original_reset_threshold = config.session_reset_on_5xx_threshold

    # Set test values
    config.max_retries = 3
    config.session_reset_on_5xx_threshold = 2

    yield

    # Restore original values
    config.max_retries = original_max_retries
    config.session_reset_on_5xx_threshold = original_reset_threshold


class TestRetrySessionReset:
    """Test session reset functionality in RetryHandler."""

    def test_consecutive_5xx_error_tracking(self):
        """Test that consecutive 5XX errors are tracked correctly."""
        session_reset_called = False

        def mock_session_reset():
            nonlocal session_reset_called
            session_reset_called = True

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        # Mock function that raises 500 errors
        def failing_request():
            raise HTTPError("Server Error", status_code=500)

        # First 500 error should not trigger reset
        with pytest.raises(HTTPError):
            handler.execute(failing_request)

        assert not session_reset_called
        assert (
            handler._consecutive_5xx_errors == config.max_retries + 1
        )  # All attempts failed

    def test_session_reset_on_threshold(self, reset_config):
        """Test that session reset is called when consecutive 5XX threshold is reached."""
        session_reset_called = False
        call_count = 0

        def mock_session_reset():
            nonlocal session_reset_called
            session_reset_called = True

        def mock_request():
            nonlocal call_count
            call_count += 1
            # Fail for threshold number of calls (2), then succeed after reset
            if (
                call_count <= config.session_reset_on_5xx_threshold
                and not session_reset_called
            ):
                raise HTTPError("Server Error", status_code=500)
            # After session reset, succeed
            return unittest.mock.Mock(status_code=200)

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        # Should succeed after session reset
        result = handler.execute(mock_request)

        assert session_reset_called
        assert result.status_code == 200
        assert handler._consecutive_5xx_errors == 0  # Should be reset after success

    def test_non_5xx_errors_reset_counter(self, reset_config):
        """Test that non-5XX errors reset the consecutive counter."""
        session_reset_called = False

        def mock_session_reset():
            nonlocal session_reset_called
            session_reset_called = True

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        call_count = 0

        def mixed_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HTTPError("Server Error", status_code=500)  # First error: 500
            elif call_count == 2:
                raise HTTPError(
                    "Too Many Requests", status_code=429
                )  # Second error: non-5XX error (should reset counter)
            elif call_count == 3:
                raise HTTPError(
                    "Server Error", status_code=500
                )  # Third error: back to 500 (counter was reset)
            else:
                return unittest.mock.Mock(status_code=200)  # Finally succeed

        # Should succeed without triggering session reset because 429 reset the 5XX counter
        result = handler.execute(mixed_errors)

        assert result.status_code == 200
        assert (
            not session_reset_called
        )  # 429 reset the counter before threshold was reached
        assert handler._consecutive_5xx_errors == 0

    def test_session_reset_without_callback(self):
        """Test that handler works without session reset callback."""
        handler = RetryHandler()  # No callback

        def failing_request():
            raise HTTPError("Server Error", status_code=500)

        # Should not crash, just retry normally
        with pytest.raises(HTTPError):
            handler.execute(failing_request)

    def test_successful_request_resets_counter(self):
        """Test that successful requests reset the consecutive error counter."""
        session_reset_called = False

        def mock_session_reset():
            nonlocal session_reset_called
            session_reset_called = True

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        # Manually set counter to simulate previous errors
        handler._consecutive_5xx_errors = 1

        # Successful request should reset counter
        def successful_request():
            return unittest.mock.Mock(status_code=200)

        result = handler.execute(successful_request)

        assert result.status_code == 200
        assert handler._consecutive_5xx_errors == 0
        assert not session_reset_called

    def test_session_reset_delay_optimization(self, reset_config):
        """Test that delay is optimized after session reset."""
        session_reset_count = 0

        def mock_session_reset():
            nonlocal session_reset_count
            session_reset_count += 1

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        call_count = 0

        def request_with_reset():
            nonlocal call_count
            call_count += 1

            # First 2 calls fail with 500, triggering reset after 2nd
            if (
                call_count <= config.session_reset_on_5xx_threshold
                and session_reset_count == 0
            ):
                raise HTTPError("Server Error", status_code=500)
            elif (
                call_count == config.session_reset_on_5xx_threshold + 1
                and session_reset_count == 1
            ):
                # After reset, still fails once more but with different error
                raise HTTPError("Too Many Requests", status_code=429)
            else:
                # Finally succeeds
                return unittest.mock.Mock(status_code=200)

        # Mock time.sleep to capture delay values
        with unittest.mock.patch("time.sleep") as mock_sleep:
            result = handler.execute(request_with_reset)

            assert result.status_code == 200
            assert session_reset_count == 1

            # Should have used base delay after session reset
            sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
            # The call after session reset should use base delay (1.0)
            assert any(delay == handler.base_delay for delay in sleep_calls)

    def test_enhanced_5xx_error_logging(self, reset_config, caplog):
        """Test enhanced logging for 5XX errors and session reset."""
        session_reset_called = False

        def mock_session_reset():
            nonlocal session_reset_called
            session_reset_called = True

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        call_count = 0

        def mock_request():
            nonlocal call_count
            call_count += 1
            if (
                call_count <= config.session_reset_on_5xx_threshold
                and not session_reset_called
            ):
                raise HTTPError("Server Error", status_code=500)
            return unittest.mock.Mock(status_code=200)

        with caplog.at_level(logging.DEBUG):
            result = handler.execute(mock_request)

            assert result.status_code == 200
            assert session_reset_called

            # Check for enhanced logging messages
            debug_messages = [
                record.message
                for record in caplog.records
                if record.levelname == "DEBUG"
            ]
            warning_messages = [
                record.message
                for record in caplog.records
                if record.levelname == "WARNING"
            ]

            # Should log consecutive 5XX errors count
            assert any("Consecutive 5XX errors:" in msg for msg in debug_messages)

            # Should log enhanced session reset message
            assert any(
                "server-side session exhaustion" in msg for msg in warning_messages
            )

    def test_5xx_error_counter_reset_logging(self, reset_config, caplog):
        """Test logging when 5XX error counter is reset by non-5XX errors."""
        handler = RetryHandler()

        call_count = 0

        def mixed_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HTTPError("Server Error", status_code=500)
            elif call_count == 2:
                raise HTTPError(
                    "Too Many Requests", status_code=429
                )  # Should reset counter
            else:
                return unittest.mock.Mock(status_code=200)

        with caplog.at_level(logging.DEBUG):
            result = handler.execute(mixed_errors)

            assert result.status_code == 200

            debug_messages = [
                record.message
                for record in caplog.records
                if record.levelname == "DEBUG"
            ]
            # Should log that counter was reset by HTTPError
            assert any(
                "5XX error counter reset by HTTPError" in msg for msg in debug_messages
            )

    def test_different_5xx_errors_count_together(self, reset_config):
        """Test that different 5XX error codes (500, 502, 503, 504) all contribute to the same counter."""
        session_reset_called = False

        def mock_session_reset():
            nonlocal session_reset_called
            session_reset_called = True

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        call_count = 0

        def mixed_5xx_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HTTPError("Internal Server Error", status_code=500)
            elif call_count == 2:
                raise HTTPError(
                    "Service Unavailable", status_code=503
                )  # Should trigger session reset after this
            elif call_count == 3:
                # After session reset, succeed
                return unittest.mock.Mock(status_code=200)
            else:
                return unittest.mock.Mock(status_code=200)

        # Should succeed after session reset triggered by mixed 5XX errors
        result = handler.execute(mixed_5xx_errors)

        assert result.status_code == 200
        assert session_reset_called  # Mixed 5XX errors should trigger reset
        assert handler._consecutive_5xx_errors == 0

    def test_all_5xx_error_codes_tracked(self, reset_config):
        """Test that various 5XX error codes (502, 504) are tracked correctly."""
        session_reset_called = False

        def mock_session_reset():
            nonlocal session_reset_called
            session_reset_called = True

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        call_count = 0

        def various_5xx_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HTTPError("Bad Gateway", status_code=502)
            elif call_count == 2:
                raise HTTPError(
                    "Gateway Timeout", status_code=504
                )  # Should trigger session reset after this
            elif call_count == 3:
                # After session reset, succeed
                return unittest.mock.Mock(status_code=200)
            else:
                return unittest.mock.Mock(status_code=200)

        # Should succeed after session reset triggered by mixed 5XX errors
        result = handler.execute(various_5xx_errors)

        assert result.status_code == 200
        assert session_reset_called  # Mixed 502/504 errors should trigger reset
        assert handler._consecutive_5xx_errors == 0

    def test_4xx_errors_reset_5xx_counter(self, reset_config):
        """Test that 4XX errors reset the 5XX error counter."""
        session_reset_called = False

        def mock_session_reset():
            nonlocal session_reset_called
            session_reset_called = True

        handler = RetryHandler(session_reset_callback=mock_session_reset)

        call_count = 0

        def mixed_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HTTPError("Internal Server Error", status_code=500)
            elif call_count == 2:
                raise HTTPError(
                    "Too Many Requests", status_code=429
                )  # Should reset 5XX counter
            elif call_count == 3:
                raise HTTPError(
                    "Service Unavailable", status_code=503
                )  # Start new 5XX count
            else:
                return unittest.mock.Mock(status_code=200)

        # Should succeed without session reset because 429 reset the counter
        result = handler.execute(mixed_errors)

        assert result.status_code == 200
        assert not session_reset_called  # 429 reset the counter before threshold
        assert handler._consecutive_5xx_errors == 0
