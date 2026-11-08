"""Main USASpending client."""

from __future__ import annotations

import os
import stat
import time
import uuid
from types import TracebackType
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

import cachier
import requests

from .config import config, register_cache_settings_observer
from .exceptions import APIError, DownloadError, HTTPError, USASpendingError
from .logging_config import USASpendingLogger, log_api_request, log_api_response

if TYPE_CHECKING:
    from .resources.agency_resource import AgencyResource
    from .resources.award_accounts_resource import AwardAccountsResource
    from .resources.award_resource import AwardResource
    from .resources.base_resource import BaseResource
    from .resources.download_resource import DownloadResource
    from .resources.funding_resource import FundingResource
    from .resources.recipients_resource import RecipientsResource
    from .resources.references_resource import ReferencesResource
    from .resources.spending_resource import SpendingResource
    from .resources.subawards_resource import SubAwardsResource
    from .resources.tas_resource import TASResource
    from .resources.transactions_resource import TransactionsResource
    from .utils.rate_limit import RateLimiter
    from .utils.retry import RetryHandler

logger = USASpendingLogger.get_logger(__name__)


def _freeze_cache_value(value: Any) -> Any:
    """Convert nested values into a hashable structure for cachier keys.

    Args:
        value: Arbitrary value to convert into a hashable structure.

    Returns:
        Hashable representation of the input value.
    """
    if isinstance(value, (str, int, float, bool, type(None))):
        return value

    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: repr(item[0]))
        return (
            "dict",
            tuple((_freeze_cache_value(k), _freeze_cache_value(v)) for k, v in items),
        )

    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_freeze_cache_value(v) for v in value))

    if isinstance(value, set):
        items = sorted(value, key=lambda item: repr(item))
        return ("set", tuple(_freeze_cache_value(v) for v in items))

    return ("repr", repr(value))


def _cache_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, Any]:
    """Build a stable cache key for cachier from args and kwargs."""
    return (_freeze_cache_value(args), _freeze_cache_value(kwargs))


def _cached_request_decorator_kwargs() -> dict[str, Any]:
    """Build cachier decorator kwargs from the current configuration."""
    return {**config._cachier_params(), "hash_func": _cache_key, "allow_none": False}


class USASpendingClient:
    """Main client for USASpending API.

    This client provides a centralized interface to the USASpending.gov API
    with automatic retry, rate limiting, and caching capabilities.

    Example:
        >>> client = USASpendingClient()
        >>> awards = (
        ...     client.awards.search()
        ...     .agency("National Aeronautics and Space Administration")
        ...     .limit(10)
        ... )
        >>> for award in awards:
        ...     print(f"{award.recipient.name}: ${award.total_obligation or 0:,.2f}")
    """

    _make_cached_request: Any

    def __init__(self):
        """Initialize USASpendingClient."""

        logger.debug(f"Initializing USASpendingClient with base URL: {config.base_url}")

        # Initialize HTTP session
        self._session = self._create_session()
        self._closed = False
        self._request_count = 0

        # Lazy-loaded components
        self._rate_limiter: RateLimiter | None = None
        self._retry_handler: RetryHandler | None = None

        # Resource cache
        self._resources: dict[str, BaseResource] = {}

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

            self._rate_limiter = RateLimiter(config.rate_limit_calls, config.rate_limit_period)
        return self._rate_limiter

    @property
    def retry_handler(self) -> RetryHandler:
        """Get retry handler (lazy-loaded)."""
        if self._retry_handler is None:
            from .utils.retry import RetryHandler

            self._retry_handler = RetryHandler(session_reset_callback=self.reset_session)
        return self._retry_handler

    @property
    def awards(self) -> AwardResource:
        """Access award endpoints."""
        if "awards" not in self._resources:
            from .resources.award_resource import AwardResource

            self._resources["awards"] = AwardResource(self)
        return self._resources["awards"]

    @property
    def downloads(self) -> DownloadResource:
        """
        Access download operations for detailed award data.

        Allows queuing, monitoring, and retrieval of bulk award files.
        """
        if "downloads" not in self._resources:
            from .resources.download_resource import DownloadResource

            self._resources["downloads"] = DownloadResource(self)
        return self._resources["downloads"]

    @property
    def recipients(self) -> RecipientsResource:
        """Access recipient endpoints."""
        if "recipients" not in self._resources:
            from .resources.recipients_resource import RecipientsResource

            self._resources["recipients"] = RecipientsResource(self)
        return self._resources["recipients"]

    @property
    def references(self) -> ReferencesResource:
        """Access USAspending reference-data endpoints.

        Returns:
            ReferencesResource: The lazily created reference-data resource.
        """
        if "references" not in self._resources:
            from .resources.references_resource import ReferencesResource

            self._resources["references"] = ReferencesResource(self)
        return self._resources["references"]

    @property
    def transactions(self) -> TransactionsResource:
        """Access transaction endpoints."""
        if "transactions" not in self._resources:
            from .resources.transactions_resource import TransactionsResource

            self._resources["transactions"] = TransactionsResource(self)
        return self._resources["transactions"]

    @property
    def spending(self) -> SpendingResource:
        """Access spending by category endpoints."""
        if "spending" not in self._resources:
            from .resources.spending_resource import SpendingResource

            self._resources["spending"] = SpendingResource(self)
        return self._resources["spending"]

    @property
    def funding(self) -> FundingResource:
        """Access funding endpoints."""
        if "funding" not in self._resources:
            from .resources.funding_resource import FundingResource

            self._resources["funding"] = FundingResource(self)
        return self._resources["funding"]

    @property
    def subawards(self) -> SubAwardsResource:
        """Access subaward endpoints."""
        if "subawards" not in self._resources:
            from .resources.subawards_resource import SubAwardsResource

            self._resources["subawards"] = SubAwardsResource(self)
        return self._resources["subawards"]

    @property
    def agencies(self) -> AgencyResource:
        """Access agency endpoints."""
        if "agencies" not in self._resources:
            from .resources.agency_resource import AgencyResource

            self._resources["agencies"] = AgencyResource(self)
        return self._resources["agencies"]

    @property
    def tas(self) -> TASResource:
        """Access TAS (Treasury Account Symbol) endpoints.

        Provides access to the TAS filter tree hierarchy for discovering
        agencies with Treasury Account Symbols and their federal accounts.

        Example:
            >>> # List all agencies with TAS
            >>> for agency in client.tas.agencies:
            ...     print(f"{agency.code}: {agency.name}")
            >>>
            >>> # Access federal accounts from an agency
            >>> agency = client.agencies.find_by_toptier_code("080")
            >>> for account in agency.federal_accounts:
            ...     print(f"{account.code}: {account.title}")
        """
        if "tas" not in self._resources:
            from .resources.tas_resource import TASResource

            self._resources["tas"] = TASResource(self)
        return self._resources["tas"]

    @property
    def award_accounts(self) -> AwardAccountsResource:
        """Access award federal accounts endpoints.

        Provides access to federal accounts associated with specific awards,
        including funding agency information and obligated amounts.

        Example:
            >>> # Get accounts for an award
            >>> award = client.awards.find_by_generated_id("CONT_AWD_123...")
            >>> for account in award.accounts:
            ...     print(f"{account.code}: ${account.obligated_amount or 0:,.2f}")
            >>>
            >>> # Or access directly
            >>> accounts = client.award_accounts.award_id("CONT_AWD_123...")
            >>> print(f"Total accounts: {accounts.count()}")
        """
        if "award_accounts" not in self._resources:
            from .resources.award_accounts_resource import AwardAccountsResource

            self._resources["award_accounts"] = AwardAccountsResource(self)
        return self._resources["award_accounts"]

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """A cacheable HTTP request method with fallback for cache failures."""
        if config.cache_enabled:
            try:
                cached_result = self._make_cached_request(
                    config.cache_namespace,
                    config.base_url,
                    method,
                    endpoint,
                    params=params,
                    json=json,
                    **kwargs,
                )
                # Validate that cache returned proper data
                if isinstance(cached_result, dict):
                    logger.debug(f"Cache hit for {method} {endpoint}")
                    return cached_result
                logger.warning(
                    f"Cache returned invalid data for {method} {endpoint}, falling back to uncached request"
                )
            except (USASpendingError, requests.RequestException):
                # A cache miss executes the request; its failures are not cache failures.
                raise
            except Exception as cache_error:
                logger.warning(
                    f"Cache operation failed for {method} {endpoint}: {cache_error}. Using uncached request."
                )

        return self._make_uncached_request(method, endpoint, params=params, json=json, **kwargs)

    def _make_cached_request_impl(
        self,
        cache_namespace: str,
        base_url: str,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Internal cached request method.

        Args:
            cache_namespace: Per-client namespace for cache isolation.  Not
                used in the method body -- it exists so cachier includes it
                in the hash key, isolating caches across namespaces.
            base_url: API base URL. Like ``cache_namespace``, it is only part of
                the hash key, so switching servers never serves another's data.
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json: JSON body for POST requests
            **kwargs: Additional arguments for requests
        """
        return self._make_uncached_request(method, endpoint, params=params, json=json, **kwargs)

    def _send_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Throttle and count each attempt using the current session."""
        self.rate_limiter.wait_if_needed()
        self._count_attempt()
        return self._session.request(method, url, **kwargs)

    def _count_attempt(self) -> None:
        """Count one request attempt, starting a fresh session once the limit is reached."""
        if self._request_count >= config.session_request_limit:
            logger.info(f"Proactively resetting session after {self._request_count} requests")
            self.reset_session()
        self._request_count += 1

    def _make_uncached_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
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
        response: requests.Response | None = None

        try:
            # Make request with retry
            response = self.retry_handler.execute(self._send_request, **request_kwargs)

            # Calculate duration
            duration = time.time() - start_time

            # Handle 400 Bad Request and 422 Unprocessable Entity (validation) responses
            # first. Both carry a descriptive body (e.g. {"detail": ...}) worth surfacing.
            if response.status_code in (400, 422):
                try:
                    data = response.json()
                    # Use "detail" property if available, otherwise fall back to generic message
                    error_msg = (
                        data.get("detail")
                        or data.get("error")
                        or data.get("message")
                        or f"HTTP {response.status_code} error"
                    )
                    error_msg_with_context = self._format_error_with_context(error_msg)
                    log_api_response(
                        logger,
                        response.status_code,
                        len(response.content) if response.content else None,
                        duration,
                        error_msg_with_context,
                    )
                    raise APIError(error_msg, status_code=response.status_code, response_body=data)
                except ValueError:
                    # If JSON parsing fails, use a generic status-aware error
                    error_msg = f"HTTP {response.status_code} error - Invalid JSON response"
                    error_msg_with_context = self._format_error_with_context(error_msg)
                    log_api_response(
                        logger,
                        response.status_code,
                        len(response.content) if response.content else None,
                        duration,
                        error_msg_with_context,
                    )
                    raise APIError(error_msg, status_code=response.status_code) from None

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
                ) from e

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
                raise APIError(f"Invalid JSON response: {e}") from e

            # Check for API errors (fallback for other error patterns)
            # Note: Don't treat "message" alone as an error indicator since some endpoints
            # (like download/status) include message as a normal response field
            if "error" in data:
                error_msg = data.get("error") or data.get("message") or "Unknown API error"
                error_msg_with_context = self._format_error_with_context(error_msg)
                log_api_response(
                    logger,
                    response.status_code,
                    len(response.content) if response.content else None,
                    duration,
                    error_msg_with_context,
                )
                raise APIError(error_msg, status_code=response.status_code, response_body=data)

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
            # response is None if the exception fired before the HTTP round-trip
            if response is not None:
                error_msg_with_context = self._format_error_with_context(str(e))
                log_api_response(
                    logger,
                    getattr(response, "status_code", 0),
                    None,
                    time.time() - start_time,
                    error_msg_with_context,
                )
            else:
                error_msg_with_context = self._format_error_with_context(
                    f"Request failed before response: {e}"
                )
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
        # Construct full URL
        if file_url.startswith("http"):
            download_url = file_url
        else:
            download_url = urljoin(config.base_url, file_url.lstrip("/"))

        logger.info(f"Downloading binary file from {download_url}")
        destination_dir = os.path.dirname(os.path.abspath(destination_path))
        file_name = os.path.basename(destination_path)

        def download_operation():
            current_url = download_url
            temporary_path = None
            try:
                # The final response may follow up to max_redirects redirects.
                for _ in range(self._session.max_redirects + 1):
                    parsed_download = urlparse(current_url)
                    if parsed_download.scheme != "https":
                        raise DownloadError(
                            f"Refusing to download over non-https scheme: {parsed_download.scheme!r}",
                            file_name=file_name,
                        )
                    if parsed_download.hostname not in config.allowed_download_hosts:
                        raise DownloadError(
                            f"Download host {parsed_download.hostname!r} is not in "
                            "config.allowed_download_hosts.",
                            file_name=file_name,
                        )

                    with self._send_request(
                        "GET", current_url, stream=True, timeout=600, allow_redirects=False
                    ) as response:
                        if 300 <= response.status_code < 400:
                            if not response.is_redirect:
                                raise DownloadError(
                                    "Invalid download redirects.", file_name=file_name
                                )
                            current_url = urljoin(current_url, response.headers["Location"])
                            continue
                        if response.status_code >= 400:
                            raise HTTPError(
                                f"HTTP {response.status_code}: {response.reason}",
                                status_code=response.status_code,
                            )

                        # Keep the previous export intact until the complete replacement is ready.
                        # Plain open() applies the live umask, unlike mkstemp's fixed 0600.
                        partial_path = os.path.join(
                            destination_dir, f".{file_name}.{uuid.uuid4().hex}"
                        )
                        with open(partial_path, "xb") as output:
                            temporary_path = partial_path
                            for chunk in response.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    output.write(chunk)
                        try:
                            destination_stat = os.stat(destination_path, follow_symlinks=False)
                        except FileNotFoundError:
                            pass
                        else:
                            if stat.S_ISREG(destination_stat.st_mode):
                                os.chmod(temporary_path, stat.S_IMODE(destination_stat.st_mode))
                        os.replace(temporary_path, destination_path)
                        temporary_path = None
                        return
                raise DownloadError("Too many download redirects.", file_name=file_name)
            finally:
                if temporary_path is not None:
                    try:
                        os.remove(temporary_path)
                    except OSError as e:
                        logger.warning(f"Could not remove partial download {temporary_path}: {e}")

        try:
            # Execute with retry handling
            self.retry_handler.execute(download_operation)
            logger.info(f"Successfully downloaded to {destination_path}")

        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            # Re-raise as DownloadError if not already
            if not isinstance(e, DownloadError):
                raise DownloadError(
                    f"Failed to download file from {download_url}",
                    file_name=file_name,
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

    def __enter__(self) -> USASpendingClient:
        """Enter context manager.

        Returns:
            Self for use in with statement

        Example:
            >>> with USASpendingClient() as client:
            ...     awards = client.awards.search().all()
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
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
        if not self._closed and hasattr(self, "_session") and self._session:
            logger.warning(
                f"USASpendingClient session was not explicitly closed after {self._request_count} requests. "
                "Consider using 'with USASpendingClient() as client:' or calling client.close()"
            )
            self.close()


def _refresh_cached_request_method() -> None:
    """Rebuild the cached request wrapper for the current config."""
    USASpendingClient._make_cached_request = cachier.cachier(  # type: ignore[attr-defined]
        **_cached_request_decorator_kwargs(),
    )(USASpendingClient._make_cached_request_impl)


register_cache_settings_observer(_refresh_cached_request_method)
_refresh_cached_request_method()
