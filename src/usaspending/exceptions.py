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


class ConfigurationError(USASpendingError):
    """Raised when client configuration is invalid."""

    pass
