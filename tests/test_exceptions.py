# tests/test_exceptions.py
"""
Comprehensive tests for USASpending exception classes.

Tests cover:
- Exception hierarchy (all inherit from USASpendingError)
- String representations
- Attribute access and defaults
- Exception chaining behavior
"""

from __future__ import annotations

import pytest

from usaspending.exceptions import (
    APIError,
    ConfigurationError,
    DetachedInstanceError,
    DownloadError,
    HTTPError,
    RateLimitError,
    USASpendingError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test that all exceptions inherit from the base USASpendingError."""

    def test_usaspending_error_inherits_from_exception(self):
        """USASpendingError should inherit from base Exception."""
        assert issubclass(USASpendingError, Exception)

    @pytest.mark.parametrize(
        "exception_class",
        [
            APIError,
            HTTPError,
            RateLimitError,
            ValidationError,
            DetachedInstanceError,
            ConfigurationError,
            DownloadError,
        ],
    )
    def test_all_exceptions_inherit_from_base(self, exception_class):
        """All custom exceptions should inherit from USASpendingError."""
        assert issubclass(exception_class, USASpendingError)

    @pytest.mark.parametrize(
        "exception_class",
        [
            APIError,
            HTTPError,
            RateLimitError,
            ValidationError,
            DetachedInstanceError,
            ConfigurationError,
            DownloadError,
        ],
    )
    def test_exceptions_can_be_caught_by_base(self, exception_class):
        """All exceptions should be catchable by USASpendingError."""
        # Create exception with minimal required args
        if exception_class == APIError:
            exc = exception_class("test message")
        elif exception_class == HTTPError:
            exc = exception_class("test message", status_code=500)
        elif exception_class == DownloadError:
            exc = exception_class("test message")
        else:
            exc = exception_class("test message")

        with pytest.raises(USASpendingError):
            raise exc


class TestUSASpendingError:
    """Tests for the base USASpendingError exception."""

    def test_message_is_accessible(self):
        """Exception message should be accessible via args."""
        error = USASpendingError("Test error message")
        assert str(error) == "Test error message"
        assert error.args[0] == "Test error message"

    def test_can_be_raised_and_caught(self):
        """Base exception can be raised and caught."""
        with pytest.raises(USASpendingError) as exc_info:
            raise USASpendingError("Base error")
        assert "Base error" in str(exc_info.value)


class TestAPIError:
    """Tests for APIError exception."""

    def test_message_only(self):
        """APIError can be created with just a message."""
        error = APIError("API returned an error")
        assert str(error) == "API returned an error"
        assert error.status_code is None
        assert error.response_body is None

    def test_with_status_code(self):
        """APIError stores status_code attribute."""
        error = APIError("Not found", status_code=404)
        assert error.status_code == 404
        assert error.response_body is None

    def test_with_response_body(self):
        """APIError stores response_body attribute."""
        body = {"error": "Invalid request", "details": "Missing required field"}
        error = APIError("Bad request", status_code=400, response_body=body)
        assert error.status_code == 400
        assert error.response_body == body
        assert error.response_body["error"] == "Invalid request"

    def test_all_attributes(self):
        """APIError correctly stores all provided attributes."""
        body = {"message": "Internal error"}
        error = APIError(
            "Server error", status_code=500, response_body=body
        )
        assert str(error) == "Server error"
        assert error.status_code == 500
        assert error.response_body == body


class TestHTTPError:
    """Tests for HTTPError exception."""

    def test_requires_status_code(self):
        """HTTPError requires a status_code parameter."""
        error = HTTPError("Connection failed", status_code=503)
        assert str(error) == "Connection failed"
        assert error.status_code == 503

    def test_various_status_codes(self):
        """HTTPError works with various HTTP status codes."""
        status_codes = [400, 401, 403, 404, 500, 502, 503, 504]
        for code in status_codes:
            error = HTTPError(f"Error {code}", status_code=code)
            assert error.status_code == code


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_default_message(self):
        """RateLimitError has a default message."""
        error = RateLimitError()
        assert str(error) == "Rate limit exceeded"
        assert error.retry_after is None

    def test_custom_message(self):
        """RateLimitError accepts custom message."""
        error = RateLimitError("Too many requests to endpoint")
        assert str(error) == "Too many requests to endpoint"

    def test_with_retry_after(self):
        """RateLimitError stores retry_after attribute."""
        error = RateLimitError("Rate limited", retry_after=60)
        assert error.retry_after == 60

    def test_retry_after_none_by_default(self):
        """RateLimitError.retry_after is None by default."""
        error = RateLimitError("Rate limited")
        assert error.retry_after is None


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_message_is_accessible(self):
        """ValidationError message is accessible."""
        error = ValidationError("Invalid fiscal year: 1899")
        assert str(error) == "Invalid fiscal year: 1899"

    def test_raised_for_invalid_input(self):
        """ValidationError can be raised for input validation failures."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("page_size must be between 1 and 100")
        assert "page_size" in str(exc_info.value)


class TestDetachedInstanceError:
    """Tests for DetachedInstanceError exception."""

    def test_message_is_accessible(self):
        """DetachedInstanceError message is accessible."""
        error = DetachedInstanceError(
            "Cannot access lazy-loaded property: client session is closed"
        )
        assert "lazy-loaded property" in str(error)
        assert "session is closed" in str(error)

    def test_descriptive_error_message(self):
        """DetachedInstanceError should have descriptive message."""
        error = DetachedInstanceError(
            "Cannot load recipient data: the USASpendingClient that created "
            "this Award has been closed. Access properties within the client "
            "context or call fetch_all_details() before exiting."
        )
        assert "USASpendingClient" in str(error)
        assert "fetch_all_details" in str(error)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_message_is_accessible(self):
        """ConfigurationError message is accessible."""
        error = ConfigurationError("Invalid cache_ttl: must be positive integer")
        assert "cache_ttl" in str(error)

    def test_raised_for_invalid_config(self):
        """ConfigurationError can be raised for configuration issues."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Unknown cache_backend: 'redis'")
        assert "cache_backend" in str(exc_info.value)


class TestDownloadError:
    """Tests for DownloadError exception."""

    def test_message_only(self):
        """DownloadError can be created with just a message."""
        error = DownloadError("Download failed")
        assert str(error) == "Download failed"
        assert error.file_name is None
        assert error.status is None

    def test_with_file_name(self):
        """DownloadError stores file_name attribute."""
        error = DownloadError("File not ready", file_name="award_123.zip")
        assert error.file_name == "award_123.zip"
        assert error.status is None

    def test_with_status(self):
        """DownloadError stores status attribute."""
        error = DownloadError("Job failed", status="failed")
        assert error.status == "failed"

    def test_all_attributes(self):
        """DownloadError correctly stores all provided attributes."""
        error = DownloadError(
            "Download timed out",
            file_name="contracts_2024.zip",
            status="timeout",
        )
        assert str(error) == "Download timed out"
        assert error.file_name == "contracts_2024.zip"
        assert error.status == "timeout"

    def test_path_traversal_error(self):
        """DownloadError can represent path traversal security issues."""
        error = DownloadError(
            "Attempted path traversal in ZIP archive: ../../../etc/passwd",
            file_name="malicious.zip",
        )
        assert "path traversal" in str(error)
        assert error.file_name == "malicious.zip"


class TestExceptionChaining:
    """Test exception chaining behavior."""

    def test_api_error_can_be_chained(self):
        """APIError can be chained from another exception."""
        original = ValueError("Invalid JSON")
        try:
            try:
                raise original
            except ValueError as e:
                raise APIError("Failed to parse response", status_code=500) from e
        except APIError as chained:
            assert chained.__cause__ is original
            assert isinstance(chained.__cause__, ValueError)

    def test_download_error_can_be_chained(self):
        """DownloadError can be chained from another exception."""
        original = IOError("Disk full")
        try:
            try:
                raise original
            except IOError as e:
                raise DownloadError(
                    "Failed to save file",
                    file_name="award.zip",
                ) from e
        except DownloadError as chained:
            assert chained.__cause__ is original
            assert chained.file_name == "award.zip"


class TestExceptionStringRepresentation:
    """Test string representation of exceptions."""

    def test_usaspending_error_str(self):
        """USASpendingError string representation."""
        error = USASpendingError("Base error message")
        assert str(error) == "Base error message"
        assert repr(error) == "USASpendingError('Base error message')"

    def test_api_error_str(self):
        """APIError string representation includes message."""
        error = APIError("API failure", status_code=500)
        assert str(error) == "API failure"

    def test_download_error_str(self):
        """DownloadError string representation includes message."""
        error = DownloadError("Failed", file_name="test.zip", status="error")
        assert str(error) == "Failed"
