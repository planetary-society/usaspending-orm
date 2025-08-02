"""Main USASpending client."""

from __future__ import annotations
import time
from typing import Optional, Dict, Any, TYPE_CHECKING
from urllib.parse import urljoin

import requests
import cachier

from .config import config
from .exceptions import HTTPError, APIError
from .logging_config import USASpendingLogger, log_api_request, log_api_response

if TYPE_CHECKING:
    from .resources.base_resource import BaseResource
    from .resources.award_resource import AwardResource
    from .resources.transactions_resource import TransactionsResource
    from .resources.recipients_resource import RecipientsResource
    from .resources.spending_resource import SpendingResource
    from .resources.funding_resource import FundingResource
    from .utils.rate_limit import RateLimiter
    from .utils.retry import RetryHandler

logger = USASpendingLogger.get_logger(__name__)


class USASpending:
    """Main client for USASpending API.

    This client provides a centralized interface to the USASpending.gov API
    with automatic retry, rate limiting, and caching capabilities.

    Example:
        >>> client = USASpending()
        >>> awards = client.awards.search().for_agency("NASA").limit(10)
        >>> for award in awards:
        ...     print(f"{award.recipient_name}: ${award.amount:,.2f}")
    """

    def __init__(self):
        """Initialize USASpending client."""

        logger.debug(
            f"Initializing USASpending client with base URL: {config.base_url}"
        )

        # Initialize HTTP session
        self._session = self._create_session()

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

            self._retry_handler = RetryHandler()
        return self._retry_handler

    @property
    def awards(self) -> "AwardResource":
        """Access award endpoints."""
        if "awards" not in self._resources:
            from .resources.award_resource import AwardResource

            self._resources["awards"] = AwardResource(self)
        return self._resources["awards"]

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

    @cachier.cachier()
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """A cacheable HTTP request method that won't trigger rate-limiting or other unnecessary behaviors"""
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
                    log_api_response(
                        logger,
                        response.status_code,
                        len(response.content) if response.content else None,
                        duration,
                        error_msg,
                    )
                    raise APIError(error_msg, status_code=400, response_body=data)
                except ValueError:
                    # If JSON parsing fails, use generic 400 error
                    error_msg = "Bad Request - Invalid JSON response"
                    log_api_response(
                        logger,
                        response.status_code,
                        len(response.content) if response.content else None,
                        duration,
                        error_msg,
                    )
                    raise APIError(error_msg, status_code=400)

            # Handle other HTTP errors
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                log_api_response(
                    logger,
                    response.status_code,
                    len(response.content) if response.content else None,
                    duration,
                    str(e),
                )
                raise HTTPError(
                    f"HTTP {response.status_code}: {e}",
                    status_code=response.status_code,
                )

            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                log_api_response(
                    logger,
                    response.status_code,
                    len(response.content) if response.content else None,
                    duration,
                    f"Invalid JSON: {e}",
                )
                raise APIError(f"Invalid JSON response: {e}")

            # Check for API errors (fallback for other error patterns)
            if "error" in data or "message" in data:
                error_msg = data.get("error") or data.get("message")
                log_api_response(
                    logger,
                    response.status_code,
                    len(response.content) if response.content else None,
                    duration,
                    error_msg,
                )
                raise APIError(
                    error_msg, status_code=response.status_code, response_body=data
                )

            # Log messages from successful responses (200 status code)
            if response.status_code == 200 and "messages" in data:
                messages = data["messages"]
                if isinstance(messages, list):
                    for msg in messages:
                        logger.info(f"API Message: {msg}")
                else:
                    logger.info(f"API Message: {messages}")

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
                log_api_response(
                    logger,
                    getattr(response, "status_code", 0),
                    None,
                    time.time() - start_time,
                    str(e),
                )
            else:
                logger.error(f"Request failed before response: {e}")
            raise

    def close(self) -> None:
        """Close client and cleanup resources."""
        if self._session:
            self._session.close()
        logger.debug("USASpending client closed")
