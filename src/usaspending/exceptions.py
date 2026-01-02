"""Custom exceptions for USASpending API client.

This module defines the exception hierarchy for the USASpending ORM library.
All exceptions inherit from USASpendingError, allowing users to catch all
library-specific errors with a single except clause.

Exception Hierarchy:
    USASpendingError (base)
    ├── APIError - API response errors (status codes, malformed responses)
    ├── HTTPError - Network/transport layer errors
    ├── RateLimitError - Rate limit exceeded (may include retry timing)
    ├── ValidationError - Invalid input parameters
    ├── DetachedInstanceError - Lazy-loading on closed session
    ├── ConfigurationError - Invalid configuration settings
    └── DownloadError - File download/extraction failures

Example:
    Catching all library errors::

        try:
            awards = client.awards.search().all()
        except USASpendingError as e:
            logger.error(f"USASpending operation failed: {e}")
"""

from __future__ import annotations


class USASpendingError(Exception):
    """Base exception for all USASpending client errors.

    All exceptions raised by this library inherit from this class,
    allowing users to catch any library-specific error with a single
    except clause.

    Example:
        Catching any library error::

            try:
                result = client.awards.find_by_award_id("ABC123")
            except USASpendingError as e:
                print(f"Operation failed: {e}")
    """


class APIError(USASpendingError):
    """Raised when the USASpending API returns an error response.

    This exception is raised when the API returns a non-success status code
    or when the response body indicates an error condition. The library's
    retry logic will NOT automatically retry APIError exceptions, as they
    typically indicate a problem with the request itself.

    Attributes:
        status_code: The HTTP status code returned by the API (e.g., 400, 404, 500).
            None if the error occurred before receiving a response.
        response_body: The parsed JSON response body from the API, if available.
            Useful for debugging and understanding the specific error.

    Example:
        Handling API errors::

            try:
                award = client.awards.find_by_award_id("INVALID_ID")
            except APIError as e:
                if e.status_code == 404:
                    print("Award not found")
                else:
                    print(f"API error {e.status_code}: {e}")
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class HTTPError(USASpendingError):
    """Raised when an HTTP transport-level error occurs.

    This exception is raised for network-level errors such as connection
    failures, timeouts, or server errors (5xx). The library's retry logic
    MAY automatically retry these errors with exponential backoff, depending
    on the status code and retry configuration.

    Retryable status codes (by default):
        - 500 Internal Server Error
        - 502 Bad Gateway
        - 503 Service Unavailable
        - 504 Gateway Timeout

    Attributes:
        status_code: The HTTP status code that triggered the error.

    Example:
        Handling network errors::

            try:
                awards = client.awards.search().all()
            except HTTPError as e:
                if e.status_code >= 500:
                    print("Server error - try again later")
                else:
                    print(f"HTTP error: {e}")
    """

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(USASpendingError):
    """Raised when the API rate limit is exceeded.

    The USASpending API enforces rate limits to prevent abuse. When exceeded,
    this exception is raised. The library includes built-in rate limiting
    (configurable via config.rate_limit_calls and config.rate_limit_period)
    to help prevent hitting API limits.

    The library's retry logic MAY automatically retry after the specified
    delay if retry_after is provided.

    Attributes:
        retry_after: The number of seconds to wait before retrying, if provided
            by the API. None if the API did not specify a retry delay.

    Example:
        Handling rate limits::

            try:
                for award in client.awards.search():
                    process(award)
            except RateLimitError as e:
                if e.retry_after:
                    print(f"Rate limited - retry after {e.retry_after} seconds")
                    time.sleep(e.retry_after)
                else:
                    print("Rate limited - please wait before retrying")
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(USASpendingError):
    """Raised when input validation fails.

    This exception is raised when user-provided parameters fail validation
    before being sent to the API. This includes invalid filter values,
    out-of-range pagination parameters, and malformed query options.

    This is NOT retried automatically, as the error is in the user's input.

    Common validation failures:
        - Invalid fiscal year (before 2008 or in the future)
        - Invalid page_size (must be 1-100)
        - Invalid sort field for the query type
        - Invalid award type filter

    Example:
        Handling validation errors::

            try:
                query = client.awards.search().fiscal_year(1990)
            except ValidationError as e:
                print(f"Invalid parameter: {e}")
    """


class DetachedInstanceError(USASpendingError):
    """Raised when accessing lazy-loaded properties on a detached model.

    This error occurs when you try to access properties that require API calls
    (lazy-loaded properties) on model instances after the USASpendingClient that
    created them has been closed or garbage collected.

    The library uses lazy loading for related data (e.g., award.transactions,
    award.recipient.location) to minimize API calls. These properties require
    an active client session to fetch data on demand.

    This is NOT retried automatically - the session must be restored.

    Solutions:
        1. Access all needed properties within the client context manager
        2. Use explicit client.close() only after you're done with models
        3. Call reattach() on models to reconnect to a new session
        4. Access only non-lazy properties after the context exits

    Example:
        Correct usage (within context)::

            with USASpendingClient() as client:
                award = client.awards.find_by_award_id("ABC123")
                # Access lazy properties inside the context
                recipient_name = award.recipient.name  # OK

        Reattaching to a new session::

            # Create objects in one session
            with USASpendingClient() as client:
                award = client.awards.find_by_award_id("ABC123")

            # Reattach to a new session
            with USASpendingClient() as new_client:
                award.reattach(new_client)
                print(award.transactions.count())  # Works!
    """


class ConfigurationError(USASpendingError):
    """Raised when client configuration is invalid.

    This exception is raised when the configuration settings provided to
    the library are invalid or inconsistent. Configuration is typically
    set via the config module before creating a client instance.

    This is NOT retried automatically - the configuration must be fixed.

    Common configuration errors:
        - Invalid cache_backend (must be 'file' or 'memory')
        - Invalid cache_ttl (must be a positive integer)
        - Invalid rate_limit_calls or rate_limit_period
        - Invalid timeout or retry settings

    Example:
        Handling configuration errors::

            from usaspending import config as usaspending_config

            try:
                usaspending_config.configure(cache_backend="redis")  # Invalid
            except ConfigurationError as e:
                print(f"Invalid configuration: {e}")
    """


class DownloadError(USASpendingError):
    """Raised when an award download process fails.

    This exception is raised during the award data download workflow, which
    involves queuing a download job, polling for completion, downloading
    the ZIP file, and extracting its contents.

    This is NOT retried automatically - the download must be restarted.

    Common download failures:
        - Download job timeout (API took too long to prepare the file)
        - API reported job failure
        - Network error during file download
        - Invalid or corrupted ZIP file
        - Path traversal attempt in ZIP archive (security protection)
        - Disk write errors during extraction

    Attributes:
        file_name: The name of the download file (provided by the API).
            Useful for identifying which download failed.
        status: The status of the download job when it failed (e.g., 'failed',
            'timeout'). None if the failure occurred before status was known.

    Example:
        Handling download errors::

            try:
                files = client.awards.download_award(
                    "ABC123",
                    destination_dir="/tmp/downloads"
                )
            except DownloadError as e:
                print(f"Download failed: {e}")
                if e.file_name:
                    print(f"File: {e.file_name}")
                if e.status:
                    print(f"Status: {e.status}")
    """

    def __init__(
        self,
        message: str,
        file_name: str | None = None,
        status: str | None = None,
    ):
        super().__init__(message)
        self.file_name = file_name
        self.status = status
