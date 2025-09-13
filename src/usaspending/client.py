"""Main USASpending client."""

from __future__ import annotations
import time
from typing import Optional, Dict, Any, TYPE_CHECKING
from urllib.parse import urljoin

import requests
import cachier

from .config import config
from .exceptions import HTTPError, APIError, ValidationError, RateLimitError
from .logging_config import USASpendingLogger, log_api_request, log_api_response

if TYPE_CHECKING:
    from .resources.base_resource import BaseResource
    from .resources.award_resource import AwardResource
    from .resources.transactions_resource import TransactionsResource
    from .resources.recipients_resource import RecipientsResource
    from .resources.spending_resource import SpendingResource
    from .resources.funding_resource import FundingResource
    from .resources.download_resource import DownloadResource
    from .resources.subawards_resource import SubAwardsResource
    from .resources.agency_resource import AgencyResource
    from .utils.rate_limit import RateLimiter
    from .utils.retry import RetryHandler

logger = USASpendingLogger.get_logger(__name__)


class USASpendingClient:
    """Main client for USASpending API.

    This client provides a centralized interface to the USASpending.gov API
    with automatic retry, rate limiting, and caching capabilities.

    Example:
        >>> client = USASpendingClient()
        >>> awards = client.awards.search().for_agency("NASA").limit(10)
        >>> for award in awards:
        ...     print(f"{award.recipient_name}: ${award.amount:,.2f}")
    """

    def __init__(self):
        """Initialize USASpendingClient."""

        logger.debug(f"Initializing USASpendingClient with base URL: {config.base_url}")

        # Initialize HTTP session
        self._session = self._create_session()
        self._closed = False
        self._request_count = 0

        # Lazy-loaded components
        self._rate_limiter: Optional[RateLimiter] = None
        self._retry_handler: Optional[RetryHandler] = None

        # Resource cache
        self._resources: Dict[str, BaseResource] = {}

        logger.debug("USASpending client initialized successfully")

    def _create_session(self) -> requests.Session:
        """Create configured requests session."""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        return session

    def _format_error_with_context(self, error_msg: str) -> str:
        """Format error message with request count and session limit context."""
        context = f"(Request #{self._request_count} in session"
        
        # Add warning if approaching session limit
        remaining = config.session_request_limit - self._request_count
        if remaining <= 10:
            context += f", {remaining} remaining before reset"
        
        context += ")"
        return f"{error_msg} {context}"

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get rate limiter (lazy-loaded)."""
        if self._rate_limiter is None:
            from .utils.rate_limit import RateLimiter

            self._rate_limiter = RateLimiter(
                config.rate_limit_calls, config.rate_limit_period
            )
        return self._rate_limiter

    @property
    def retry_handler(self) -> RetryHandler:
        """Get retry handler (lazy-loaded)."""
        if self._retry_handler is None:
            from .utils.retry import RetryHandler

            self._retry_handler = RetryHandler(session_reset_callback=self.reset_session)
        return self._retry_handler

    @property
    def awards(self) -> "AwardResource":
        """Access award endpoints."""
        if "awards" not in self._resources:
            from .resources.award_resource import AwardResource

            self._resources["awards"] = AwardResource(self)
        return self._resources["awards"]

    @property
    def downloads(self) -> "DownloadResource":
        """
        Access download operations for detailed award data.

        Allows queuing, monitoring, and retrieval of bulk award files.
        """
        if "downloads" not in self._resources:
            from .resources.download_resource import DownloadResource

            self._resources["downloads"] = DownloadResource(self)
        return self._resources["downloads"]

    @property
    def recipients(self) -> "RecipientsResource":
        """Access recipient endpoints."""
        if "recipients" not in self._resources:
            from .resources.recipients_resource import RecipientsResource

            self._resources["recipients"] = RecipientsResource(self)
        return self._resources["recipients"]

    @property
    def transactions(self) -> "TransactionsResource":
        """Access transaction endpoints."""
        if "transactions" not in self._resources:
            from .resources.transactions_resource import TransactionsResource

            self._resources["transactions"] = TransactionsResource(self)
        return self._resources["transactions"]

    @property
    def spending(self) -> "SpendingResource":
        """Access spending by category endpoints."""
        if "spending" not in self._resources:
            from .resources.spending_resource import SpendingResource

            self._resources["spending"] = SpendingResource(self)
        return self._resources["spending"]

    @property
    def funding(self) -> "FundingResource":
        """Access funding endpoints."""
        if "funding" not in self._resources:
            from .resources.funding_resource import FundingResource

            self._resources["funding"] = FundingResource(self)
        return self._resources["funding"]

    @property
    def subawards(self) -> "SubAwardsResource":
        """Access subaward endpoints."""
        if "subawards" not in self._resources:
            from .resources.subawards_resource import SubAwardsResource

            self._resources["subawards"] = SubAwardsResource(self)
        return self._resources["subawards"]

    @property
    def agencies(self) -> "AgencyResource":
        """Access agency endpoints."""
        if "agencies" not in self._resources:
            from .resources.agency_resource import AgencyResource

            self._resources["agencies"] = AgencyResource(self)
        return self._resources["agencies"]

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """A cacheable HTTP request method with fallback for cache failures."""
        try:
            # Try cached version first if caching is enabled
            if config.cache_enabled:
                cached_result = self._make_cached_request(
                    method, endpoint, params=params, json=json, **kwargs
                )
                # Validate that cache returned proper data
                if cached_result is not None and isinstance(cached_result, dict):
                    logger.debug(f"Cache hit for {method} {endpoint}")
                    return cached_result
                else:
                    logger.warning(
                        f"Cache returned invalid data for {method} {endpoint}, falling back to uncached request"
                    )
            
            # Fallback to uncached request if cache disabled or returned invalid data
            return self._make_uncached_request(
                method, endpoint, params=params, json=json, **kwargs
            )
        except (APIError, HTTPError, ValidationError, RateLimitError):
            # These are normal API errors - let them propagate without fallback
            # Cachier will re-execute on next call (doesn't cache exceptions)
            raise
        except Exception as cache_error:
            # Only catch serious cache failures (file corruption, lock issues, etc.)
            logger.warning(
                f"Cache operation failed for {method} {endpoint}: {cache_error}. Using uncached request."
            )
            return self._make_uncached_request(
                method, endpoint, params=params, json=json, **kwargs
            )

    @cachier.cachier()
    def _make_cached_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Internal cached request method."""
        return self._make_uncached_request(
            method, endpoint, params=params, json=json, **kwargs
        )

    def _make_uncached_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json: JSON body for POST requests
            **kwargs: Additional arguments for requests

        Returns:
            Response data as dictionary

        Raises:
            HTTPError: For HTTP errors
            APIError: For API-reported errors
            RateLimitError: When rate limited
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        # Increment request counter and check for proactive session reset
        self._request_count += 1
        if self._request_count >= config.session_request_limit:
            logger.info(f"Proactively resetting session after {self._request_count} requests")
            self.reset_session()

        # Build full URL
        url = urljoin(config.base_url, endpoint.lstrip("/"))

        # Log API request
        log_api_request(logger, method, url, params, json)

        # Prepare request
        request_kwargs = {
            "method": method,
            "url": url,
            "params": params,
            "json": json,
            "timeout": config.timeout,
            **kwargs,
        }

        # Track request timing
        start_time = time.time()

        try:
            # Make request with retry
            response = self.retry_handler.execute(
                self._session.request, **request_kwargs
            )

            # Calculate duration
            duration = time.time() - start_time

            # Handle specific 400 Bad Request responses first
            if response.status_code == 400:
                try:
                    data = response.json()
                    # Use "detail" property if available, otherwise fall back to generic message
                    error_msg = (
                        data.get("detail")
                        or data.get("error")
                        or data.get("message")
                        or "Bad Request"
                    )
                    error_msg_with_context = self._format_error_with_context(error_msg)
                    log_api_response(
                        logger,
                        response.status_code,
                        len(response.content) if response.content else None,
                        duration,
                        error_msg_with_context,
                    )
                    raise APIError(error_msg, status_code=400, response_body=data)
                except ValueError:
                    # If JSON parsing fails, use generic 400 error
                    error_msg = "Bad Request - Invalid JSON response"
                    error_msg_with_context = self._format_error_with_context(error_msg)
                    log_api_response(
                        logger,
                        response.status_code,
                        len(response.content) if response.content else None,
                        duration,
                        error_msg_with_context,
                    )
                    raise APIError(error_msg, status_code=400)

            # Handle other HTTP errors
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                error_msg_with_context = self._format_error_with_context(str(e))
                log_api_response(
                    logger,
                    response.status_code,
                    len(response.content) if response.content else None,
                    duration,
                    error_msg_with_context,
                )
                raise HTTPError(
                    f"HTTP {response.status_code}: {e}",
                    status_code=response.status_code,
                )

            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON: {e}"
                error_msg_with_context = self._format_error_with_context(error_msg)
                log_api_response(
                    logger,
                    response.status_code,
                    len(response.content) if response.content else None,
                    duration,
                    error_msg_with_context,
                )
                raise APIError(f"Invalid JSON response: {e}")

            # Check for API errors (fallback for other error patterns)
            # Note: Don't treat "message" alone as an error indicator since some endpoints
            # (like download/status) include message as a normal response field
            if "error" in data:
                error_msg = (
                    data.get("error") or data.get("message") or "Unknown API error"
                )
                error_msg_with_context = self._format_error_with_context(error_msg)
                log_api_response(
                    logger,
                    response.status_code,
                    len(response.content) if response.content else None,
                    duration,
                    error_msg_with_context,
                )
                raise APIError(
                    error_msg, status_code=response.status_code, response_body=data
                )

            # Log messages from successful responses (200 status code)
            if response.status_code == 200 and "messages" in data:
                messages = data["messages"]
                if isinstance(messages, list):
                    for msg in messages:
                        logger.debug(f"API Message: {msg}")
                else:
                    logger.debug(f"API Message: {messages}")

            # Log successful response
            log_api_response(
                logger,
                response.status_code,
                len(response.content) if response.content else None,
                duration,
            )

            return data

        except Exception as e:
            # Log any unexpected errors
            if "response" in locals():
                error_msg_with_context = self._format_error_with_context(str(e))
                log_api_response(
                    logger,
                    getattr(response, "status_code", 0),
                    None,
                    time.time() - start_time,
                    error_msg_with_context,
                )
            else:
                error_msg_with_context = self._format_error_with_context(f"Request failed before response: {e}")
                logger.error(error_msg_with_context)
            raise

    def _download_binary_file(self, file_url: str, destination_path: str) -> None:
        """Download binary file using client session with streaming support.

        This method is used internally for downloading large binary files
        like the ZIP archives from the download endpoints.

        Args:
            file_url: Relative or absolute URL to download
            destination_path: Local path where file will be saved

        Raises:
            DownloadError: If download fails
        """
        import os
        from .exceptions import DownloadError

        # Construct full URL
        if file_url.startswith("http"):
            download_url = file_url
        else:
            download_url = urljoin(config.base_url, file_url.lstrip("/"))

        logger.info(f"Downloading binary file from {download_url}")

        # Use a longer timeout for file downloads
        timeout = 600  # 10 minutes

        def download_operation():
            """Inner function for retry handler."""
            response = self._session.get(download_url, stream=True, timeout=timeout)
            response.raise_for_status()

            try:
                with open(destination_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            except IOError as e:
                raise DownloadError(
                    f"Error writing file to disk: {e}",
                    file_name=os.path.basename(destination_path),
                ) from e

        try:
            # Execute with retry handling
            self.retry_handler.execute(download_operation)
            logger.info(f"Successfully downloaded to {destination_path}")

        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            # Clean up partial file if it exists
            if os.path.exists(destination_path):
                try:
                    os.remove(destination_path)
                    logger.debug(f"Cleaned up partial file: {destination_path}")
                except OSError:
                    pass

            # Re-raise as DownloadError if not already
            if not isinstance(e, DownloadError):
                raise DownloadError(
                    f"Failed to download file from {download_url}",
                    file_name=os.path.basename(destination_path),
                ) from e
            raise

    def close(self) -> None:
        """Close client and cleanup resources.
        
        This method is idempotent and safe to call multiple times.
        """
        if not self._closed and self._session:
            self._session.close()
            self._closed = True
            logger.info(f"USASpending client closed after {self._request_count} requests")

    def reset_session(self) -> None:
        """Reset the HTTP session to handle server-side session limits.
        
        This creates a new session with fresh connection pools, which can
        resolve issues where the server limits requests per session.
        The request counter is also reset.
        """
        if not self._closed and self._session:
            old_count = self._request_count
            self._session.close()
            self._session = self._create_session()
            self._request_count = 0
            logger.info(f"Session reset after {old_count} requests")

    def __enter__(self) -> "USASpendingClient":
        """Enter context manager.
        
        Returns:
            Self for use in with statement
            
        Example:
            >>> with USASpendingClient() as client:
            ...     awards = client.awards.search().all()
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and cleanup resources.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred  
            exc_tb: Exception traceback if an exception occurred
        """
        self.close()

    def __del__(self) -> None:
        """Destructor to cleanup resources if not already closed.
        
        Note: It's better to use the context manager or call close() explicitly.
        This is a safety net for cases where proper cleanup wasn't done.
        """
        if not self._closed and hasattr(self, '_session') and self._session:
            logger.warning(
                f"USASpendingClient session was not explicitly closed after {self._request_count} requests. "
                "Consider using 'with USASpendingClient() as client:' or calling client.close()"
            )
            self.close()
