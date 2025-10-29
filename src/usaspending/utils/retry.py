"""Retry logic implementation for USASpending API client."""

from __future__ import annotations

import random
import time
from typing import Any, Callable, Optional

import requests

from ..config import config
from ..exceptions import HTTPError, RateLimitError
from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)


class RetryHandler:
    """
    Handles retry logic with exponential backoff for API requests.

    This implementation retries requests that fail due to transient errors
    like network issues, server errors (5xx), and rate limiting (429).
    """

    # HTTP status codes that should be retried
    RETRYABLE_STATUS_CODES = {
        429,  # Too Many Requests (rate limit)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
        520,  # Unknown Error (Cloudflare)
        521,  # Web Server Is Down
        522,  # Connection Timed Out
        523,  # Origin Is Unreachable
        524,  # A Timeout Occurred
    }

    # Exception types that should be retried
    RETRYABLE_EXCEPTIONS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout,
    )

    def __init__(self, session_reset_callback: Optional[Callable] = None):
        """
        Initialize the retry handler.

        Args:
            session_reset_callback: Optional callback to reset session on persistent errors
        """
        self.max_retries = config.max_retries
        self.base_delay = config.retry_delay
        self.backoff_factor = config.retry_backoff
        self.session_reset_callback = session_reset_callback

        # Track consecutive 5XX errors for session reset logic
        self._consecutive_5xx_errors = 0

        logger.debug(
            f"Initialized RetryHandler: max_retries={self.max_retries}, "
            f"base_delay={self.base_delay}s, backoff_factor={self.backoff_factor}, "
            f"session_reset={'enabled' if session_reset_callback else 'disabled'}"
        )

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute (typically session.request)
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the successful function call

        Raises:
            The last exception encountered if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):  # +1 for the initial attempt
            try:
                result = func(*args, **kwargs)

                # Check if the result is a response object with a status code
                if hasattr(result, "status_code"):
                    self._check_response_for_retry(result, attempt)

                # Reset consecutive 5XX error counter on successful response
                self._consecutive_5xx_errors = 0
                return result

            except Exception as e:
                last_exception = e

                # Track consecutive 5XX errors for session reset logic
                if isinstance(e, HTTPError) and e.status_code >= 500:
                    self._consecutive_5xx_errors += 1
                    logger.debug(
                        f"Consecutive 5XX errors: {self._consecutive_5xx_errors}"
                    )

                    # Check if we should reset session due to persistent 5XX errors
                    if (
                        self.session_reset_callback
                        and self._consecutive_5xx_errors
                        >= config.session_reset_on_5xx_threshold
                        and attempt < self.max_retries
                    ):  # Don't reset on final attempt
                        logger.warning(
                            f"Resetting session due to {self._consecutive_5xx_errors} consecutive 5XX errors "
                            f"(suggests server-side session exhaustion)"
                        )
                        self.session_reset_callback()
                        self._consecutive_5xx_errors = 0
                        # Reduce delay after session reset since we may have fixed the issue
                        delay = self.base_delay
                        logger.info(f"Retrying with fresh session after {delay:.2f}s")
                        time.sleep(delay)
                        continue
                else:
                    # Reset counter for non-5XX errors
                    if self._consecutive_5xx_errors > 0:
                        logger.debug(
                            f"5XX error counter reset by {type(e).__name__} (was {self._consecutive_5xx_errors})"
                        )
                    self._consecutive_5xx_errors = 0

                # Don't retry on the last attempt
                if attempt == self.max_retries:
                    logger.warning(
                        f"Max retries ({self.max_retries}) exhausted. Final error: {e}"
                    )
                    break

                # Check if this exception should be retried
                if not self._should_retry_exception(e):
                    logger.debug(f"Exception {type(e).__name__} is not retryable")
                    break

                # Calculate delay and wait before retrying
                delay = self._calculate_delay(attempt, e)
                if delay > 0:
                    logger.info(
                        f"Retry attempt {attempt + 1}/{self.max_retries} after {delay:.2f}s "
                        f"due to {type(e).__name__}: {e}"
                    )
                    time.sleep(delay)

        # If we get here, all retries were exhausted
        raise last_exception

    def _check_response_for_retry(
        self, response: requests.Response, attempt: int
    ) -> None:
        """
        Check if a response should trigger a retry.

        Args:
            response: The HTTP response object
            attempt: Current attempt number (0-based)

        Raises:
            Various exceptions if retry should occur
        """
        if response.status_code in self.RETRYABLE_STATUS_CODES:
            if response.status_code == 429:
                # Rate limit exceeded
                retry_after = self._get_retry_after_header(response)
                logger.warning(
                    f"Rate limit hit (HTTP 429). Retry-After: {retry_after}s"
                )
                raise RateLimitError("Rate limit exceeded", retry_after=retry_after)
            elif response.status_code >= 500:
                # Server error
                logger.warning(f"Server error (HTTP {response.status_code})")
                raise HTTPError(
                    f"Server error: HTTP {response.status_code}",
                    status_code=response.status_code,
                )

    def _should_retry_exception(self, exception: Exception) -> bool:
        """
        Determine if an exception should trigger a retry.

        Args:
            exception: The exception that occurred

        Returns:
            True if the exception should be retried, False otherwise
        """
        # Always retry these network-related exceptions
        if isinstance(exception, self.RETRYABLE_EXCEPTIONS):
            return True

        # Retry rate limit errors
        if isinstance(exception, RateLimitError):
            return True

        # Retry HTTP errors with retryable status codes
        if isinstance(exception, HTTPError):
            return exception.status_code in self.RETRYABLE_STATUS_CODES

        # Don't retry other exceptions (like validation errors, auth errors, etc.)
        return False

    def _calculate_delay(self, attempt: int, exception: Exception) -> float:
        """
        Calculate the delay before the next retry attempt.

        Args:
            attempt: Current attempt number (0-based)
            exception: The exception that triggered this retry

        Returns:
            Delay in seconds before the next attempt
        """
        # Handle rate limit errors specially
        if isinstance(exception, RateLimitError) and exception.retry_after:
            # Use the server-provided retry-after value
            return float(exception.retry_after)

        # Calculate exponential backoff with jitter
        delay = self.base_delay * (self.backoff_factor**attempt)

        # Add jitter (randomness) to avoid thundering herd problem
        # Use up to 25% jitter
        jitter = delay * 0.25 * random.random()
        delay += jitter

        logger.debug(f"Calculated retry delay: {delay:.3f}s (attempt {attempt})")
        return delay

    def _get_retry_after_header(self, response: requests.Response) -> Optional[int]:
        """
        Extract the Retry-After header value from a rate limit response.

        Args:
            response: The HTTP response object

        Returns:
            Number of seconds to wait, or None if header not present
        """
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                # Header might be in HTTP-date format, but we'll just ignore it
                # and use exponential backoff instead
                pass
        return None
