"""Custom exceptions for USASpending API client."""


class USASpendingError(Exception):
    """Base exception for all USASpending client errors."""

    pass


class APIError(USASpendingError):
    """Raised when the API returns an error response."""

    def __init__(
        self, message: str, status_code: int = None, response_body: dict = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class HTTPError(USASpendingError):
    """Raised when an HTTP error occurs."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(USASpendingError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(USASpendingError):
    """Raised when input validation fails."""

    pass


class DetachedInstanceError(USASpendingError):
    """Raised when attempting to access lazy-loaded properties on a model whose client session is closed.

    This error occurs when you try to access properties that require API calls
    (lazy-loaded properties) on model instances after the USASpendingClient that
    created them has been closed or garbage collected.

    To avoid this error:
    1. Access all needed properties within the client context manager
    2. Use explicit client cleanup (client.close()) only after you're done with models
    3. Call fetch_all_details() on models before the client context exits
    """

    pass


class ConfigurationError(USASpendingError):
    """Raised when client configuration is invalid."""

    pass


class DownloadError(USASpendingError):
    """Raised when an award download process fails, times out, or encounters issues during file processing."""

    def __init__(self, message: str, file_name: str = None, status: str = None):
        super().__init__(message)
        self.file_name = file_name
        self.status = status
