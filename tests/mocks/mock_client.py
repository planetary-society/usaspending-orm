"""Universal mock client for USASpending API tests."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from usaspending import USASpendingClient
from usaspending.config import config
from usaspending.exceptions import APIError, HTTPError

from .response_builder import ResponseBuilder


class MockUSASpendingClient(USASpendingClient):
    class Endpoints:
        """A collection of API endpoint constants."""
        AGENCY = "/agency/{toptier_code}/"
        AGENCY_SUBAGENCIES = "/agency/{toptier_code}/sub_agency/"
        AGENCY_AUTOCOMPLETE = "/autocomplete/funding_agency_office/"
        AWARDING_AGENCY_AUTOCOMPLETE = "/autocomplete/awarding_agency_office/"
        AWARD_SEARCH = "/search/spending_by_award/"
        AWARD_COUNT = "/search/spending_by_award_count/"
        AWARD_DETAIL = "/awards/{award_id}/"
        AWARD_FUNDING = "/awards/funding/"
        SUBWARD_COUNT = "/awards/count/subaward/{award_id}/"
        TRANSACTION_COUNT = "/awards/count/transaction/{award_id}/"
        TRANSACTIONS = "/transactions/"

        RECIPIENT_DETAIL = "/recipients/{recipient_id}/"
        RECIPIENT_SEARCH = "/recipient/"
        RECIPIENT_COUNT = "/recipient/count/"

        DOWNLOAD_ASSISTANCE = "/download/assistance/"
        DOWNLOAD_CONTRACT = "/download/contract/"
        DOWNLOAD_IDV = "/download/idv/"
        DOWNLOAD_STATUS = "/download/status"

        SPENDING_BY_RECIPIENT = "/search/spending_by_category/recipient/"
        SPENDING_BY_DISTRICT = "/search/spending_by_category/district/"

    """Mock USASpending client for testing.

    This class provides a comprehensive mocking system for the USASpending API,
    supporting:
    - Single and paginated responses
    - Fixture-based responses
    - Error simulation
    - Rate limiting simulation
    - Request tracking and assertions

    Example:
        ```python
        mock_client = MockUSASpendingClient()
        mock_client.set_paginated_response(
            "/search/spending_by_award/",
            items=[{"Award ID": f"AWD-{i}"} for i in range(250)],
            page_size=100
        )

        results = list(mock_client.awards.search().with_award_types("A"))
        assert len(results) == 250
        ```
    """

    def __init__(self):
        """Initialize mock client with test-friendly defaults."""
        # Configure test-friendly defaults
        # High rate limit to avoid interference with tests unless explicitly testing rate limiting
        config.configure(cache_enabled=False)

        # Initialize parent class
        super().__init__()

        # Response storage
        self._responses: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._default_responses: Dict[str, Dict[str, Any]] = {}
        self._error_responses: Dict[str, Dict[str, Any]] = {}

        # Request tracking
        self._request_history: List[Dict[str, Any]] = []
        self._request_counts: Dict[str, int] = defaultdict(int)

        # Rate limiting simulation
        self._simulate_rate_limit = False
        self._rate_limit_delay = 0.0

        # Fixture directory
        self._fixture_dir = Path(__file__).parent.parent / "fixtures"

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Mock implementation of _make_request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            json: Request payload
            params: Query parameters
            **kwargs: Additional arguments

        Returns:
            Mocked API response

        Raises:
            APIError: For mocked 400 errors
            HTTPError: For mocked non-400 errors
        """
        # Track request
        request_data = {
            "method": method,
            "endpoint": endpoint,
            "json": json,
            "params": params,
            "timestamp": time.time(),
        }
        self._request_history.append(request_data)
        self._request_counts[endpoint] += 1

        # Simulate rate limiting if enabled
        if self._simulate_rate_limit:
            time.sleep(self._rate_limit_delay)

        # Check for error response
        if endpoint in self._error_responses:
            error_data = self._error_responses[endpoint]
            status_code = error_data["status_code"]

            if status_code == 400:
                raise APIError(
                    error_data.get("detail", error_data.get("error", "Bad Request")),
                    status_code=status_code,
                    response_body=error_data,
                )
            else:
                raise HTTPError(
                    f"HTTP {status_code}: {error_data.get('error', 'Server Error')}",
                    status_code=status_code,
                )

        # Check for specific responses (with pagination support)
        if endpoint in self._responses and self._responses[endpoint]:
            # Pop the next response in sequence
            response = self._responses[endpoint].pop(0)

            # If it's a paginated response, update page metadata
            if "page_metadata" in response and json and "page" in json:
                response["page_metadata"]["page"] = json["page"]

            return response

        # Check for default response
        if endpoint in self._default_responses:
            response = self._default_responses[endpoint]

            # Log messages from successful responses (200 status code) - mimic real client behavior
            if "messages" in response:
                from usaspending.logging_config import USASpendingLogger

                logger = USASpendingLogger.get_logger(__name__)
                messages = response["messages"]
                if isinstance(messages, list):
                    for msg in messages:
                        logger.info(f"API Message: {msg}")
                else:
                    logger.info(f"API Message: {messages}")

            return response

        # Return appropriate default response based on endpoint
        if "count" in endpoint:
            # Count endpoints need a different structure
            return {"results": {}, "messages": []}
        else:
            # Search endpoints use paginated structure
            return ResponseBuilder.paginated_response([], has_next=False)

    def set_response(
        self, endpoint: str, response_data: Dict[str, Any], status_code: int = 200
    ) -> None:
        """Set a single response for an endpoint.

        Args:
            endpoint: API endpoint
            response_data: Response data to return
            status_code: HTTP status code (for error simulation)
        """
        if status_code >= 400:
            self._error_responses[endpoint] = {
                **response_data,
                "status_code": status_code,
            }
        else:
            self._default_responses[endpoint] = response_data

    def set_paginated_response(
        self,
        endpoint: str,
        items: List[Dict[str, Any]],
        page_size: int = 100,
        auto_count: bool = True,
    ) -> None:
        """Automatically paginate a list of items.

        Args:
            endpoint: API endpoint
            items: List of all items to paginate
            page_size: Items per page
            auto_count: Whether to automatically set up count endpoint
        """
        # Clear any existing responses
        self._responses[endpoint] = []

        # Create pages
        for i in range(0, len(items), page_size):
            page_items = items[i : i + page_size]
            page_num = (i // page_size) + 1
            has_next = (i + page_size) < len(items)

            response = ResponseBuilder.paginated_response(
                results=page_items, page=page_num, has_next=has_next
            )
            self._responses[endpoint].append(response)

        # If no items, add single empty response
        if not items:
            self._responses[endpoint].append(
                ResponseBuilder.paginated_response([], has_next=False)
            )

        # Automatically set up count endpoint if requested
        if auto_count:
            self._auto_setup_count_endpoint(endpoint, len(items))

    def set_fixture_response(
        self, endpoint: str, fixture_name: str, transform: Optional[callable] = None
    ) -> None:
        """Load response from fixture file.

        Args:
            endpoint: API endpoint
            fixture_name: Name of fixture file (without .json)
            transform: Optional function to transform fixture data
        """
        fixture_path = self._fixture_dir / f"{fixture_name}.json"

        with open(fixture_path) as f:
            data = json.load(f)

        if transform:
            data = transform(data)

        self.set_response(endpoint, data)

    def set_error_response(
        self,
        endpoint: str,
        error_code: int,
        error_message: Optional[str] = None,
        detail: Optional[str] = None,
        auto_count_error: bool = True,
    ) -> None:
        """Simulate API errors.

        Args:
            endpoint: API endpoint
            error_code: HTTP error code
            error_message: General error message
            detail: Detailed error message (for 400 errors)
            auto_count_error: Whether to also set the same error for count endpoints
        """
        error_data = ResponseBuilder.error_response(
            status_code=error_code, detail=detail, error=error_message
        )
        self.set_response(endpoint, error_data, status_code=error_code)

        # Also set error for corresponding count endpoint if requested
        if auto_count_error:
            count_endpoint_mapping = {
                "/search/spending_by_award/": "/search/spending_by_award_count/",
                "/transactions/": "/awards/count/transaction/",
                "/search/spending_by_recipient/": "/search/spending_by_recipient_count/",
            }

            count_endpoint = count_endpoint_mapping.get(endpoint)
            if count_endpoint:
                self.set_response(count_endpoint, error_data, status_code=error_code)

    def add_response_sequence(
        self, endpoint: str, responses: List[Dict[str, Any]], auto_count: bool = True
    ) -> None:
        """Add multiple responses for sequential calls.

        Args:
            endpoint: API endpoint
            responses: List of responses to return in sequence
            auto_count: Whether to automatically set up count endpoint
        """
        self._responses[endpoint].extend(responses)

        # Automatically set up count endpoint based on first response
        if auto_count and responses:
            first_response = responses[0]
            if "results" in first_response and isinstance(
                first_response["results"], list
            ):
                total_count = len(first_response["results"])
                self._auto_setup_count_endpoint(endpoint, total_count)

    def simulate_rate_limit(self, delay: float = 0.1) -> None:
        """Enable rate limiting simulation.

        Args:
            delay: Delay in seconds between requests
        """
        self._simulate_rate_limit = True
        self._rate_limit_delay = delay

    def disable_rate_limit(self) -> None:
        """Disable rate limiting simulation."""
        self._simulate_rate_limit = False
        self._rate_limit_delay = 0.0

    def _auto_setup_count_endpoint(
        self, search_endpoint: str, total_count: int
    ) -> None:
        """Automatically set up count endpoint for a search endpoint.

        Args:
            search_endpoint: The search endpoint (e.g., "/search/spending_by_award/")
            total_count: Total number of items
        """
        # Map search endpoints to their count endpoints
        count_endpoint_mapping = {
            "/search/spending_by_award/": "/search/spending_by_award_count/",
            "/transactions/": "/awards/count/transaction/",  # Would need award_id
            "/search/spending_by_recipient/": "/search/spending_by_recipient_count/",  # If it existed
            "/recipient/": "/recipient/count/",  # Recipients search count mapping
        }

        count_endpoint = count_endpoint_mapping.get(search_endpoint)
        if count_endpoint == "/search/spending_by_award_count/":
            # For awards, default to contracts category for backward compatibility
            self.mock_award_count(contracts=total_count)
        elif count_endpoint == "/recipient/count/":
            # For recipients, set up the count response with correct format
            response = {"count": total_count}
            self.set_response(count_endpoint, response)
        elif count_endpoint and "transaction" not in count_endpoint:
            # For other endpoints, set up a generic count response
            # This could be enhanced based on specific endpoint needs
            response = {"results": {"total": total_count}, "messages": []}
            self.set_response(count_endpoint, response)

    # Request tracking and assertions

    def get_request_count(self, endpoint: Optional[str] = None) -> int:
        """Get count of requests made.

        Args:
            endpoint: Specific endpoint to count, or None for total

        Returns:
            Number of requests
        """
        if endpoint:
            return self._request_counts[endpoint]
        return len(self._request_history)

    def get_last_request(
        self, endpoint: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the last request made.

        Args:
            endpoint: Filter by specific endpoint

        Returns:
            Last request data or None
        """
        if not self._request_history:
            return None

        if endpoint:
            # Find last request to this endpoint
            for request in reversed(self._request_history):
                if request["endpoint"] == endpoint:
                    return request
            return None

        return self._request_history[-1]

    def assert_called_with(
        self,
        endpoint: str,
        method: str = "GET",
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Assert that a specific request was made.

        Args:
            endpoint: Expected endpoint
            method: Expected HTTP method
            json: Expected request payload
            params: Expected query parameters

        Raises:
            AssertionError: If request not found
        """
        for request in self._request_history:
            if (
                request["endpoint"] == endpoint
                and request["method"] == method
                and (json is None or request["json"] == json)
                and (params is None or request["params"] == params)
            ):
                return

        raise AssertionError(
            f"Request not found: {method} {endpoint} with json={json}, params={params}"
        )

    def reset(self) -> None:
        """Reset all mock state."""
        self._responses.clear()
        self._default_responses.clear()
        self._error_responses.clear()
        self._request_history.clear()
        self._request_counts.clear()
        self._simulate_rate_limit = False
        self._rate_limit_delay = 0.0

    def _make_uncached_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Pass through to _make_request since caching is disabled in tests."""
        return self._make_request(method, endpoint, json=json, params=params, **kwargs)

    def _download_binary_file(self, file_url: str, destination_path: str) -> None:
        """Mock implementation of binary file download.
        
        For testing, we just create an empty file at the destination.
        Real download testing would be done in integration tests.
        """
        import os
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        with open(destination_path, 'wb') as f:
            f.write(b'Mock download content')

    def mock_download_queue(
        self, 
        download_type: str, 
        award_id: str, 
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mock download queue response.
        
        Args:
            download_type: "contract", "assistance", or "idv"
            award_id: Award identifier
            response_data: Custom response data, or None to use fixture default
        """
        if response_data is None:
            # Load default from fixture
            import json
            from copy import deepcopy
            fixture_path = self._fixture_dir / "download_assistance.json"
            with open(fixture_path) as f:
                response_data = deepcopy(json.load(f))
            
            # Customize for the specific request
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_H%M%S%f")
            file_name = f"{download_type.upper()}_{award_id}_{timestamp}.zip"
            response_data["file_name"] = file_name
            response_data["file_url"] = f"https://files.usaspending.gov/generated_downloads/{file_name}"
            response_data["status_url"] = f"https://api.usaspending.gov/api/v2/download/status?file_name={file_name}"
            
            # Update download_request fields
            response_data["download_request"]["award_id"] = award_id
            response_data["download_request"]["request_type"] = download_type
            response_data["download_request"]["is_for_contract"] = download_type == "contract"
            response_data["download_request"]["is_for_assistance"] = download_type == "assistance"
            response_data["download_request"]["is_for_idv"] = download_type == "idv"
        
        endpoint = f"/download/{download_type}/"
        self.set_response(endpoint, response_data)

    def mock_download_status(
        self,
        file_name: str,
        status: str = "finished",
        custom_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mock download status response.
        
        Args:
            file_name: Name of file to check status for
            status: Status to return ("ready", "running", "finished", "failed")
            custom_data: Complete custom response, or None to use template
        """
        if custom_data is not None:
            response_data = custom_data
        else:
            # Load and customize fixture template
            import json
            from copy import deepcopy
            fixture_path = self._fixture_dir / "download_status.json"
            with open(fixture_path) as f:
                response_data = deepcopy(json.load(f))
            
            response_data["file_name"] = file_name
            response_data["status"] = status
            response_data["file_url"] = f"https://files.usaspending.gov/generated_downloads/{file_name}"
            
            # Adjust fields based on status
            if status == "ready":
                response_data["seconds_elapsed"] = None
                response_data["total_size"] = None
                response_data["total_columns"] = None
                response_data["total_rows"] = None
            elif status == "running":
                response_data["seconds_elapsed"] = "5.123"
                response_data["total_size"] = None
                response_data["total_columns"] = None
                response_data["total_rows"] = None
            elif status == "failed":
                response_data["message"] = "Download failed: Internal server error"
                response_data["file_url"] = None
                response_data["seconds_elapsed"] = "10.456"
                response_data["total_size"] = None
                response_data["total_columns"] = None
                response_data["total_rows"] = None
        
        self.set_response("/download/status", response_data)

    # Convenience methods for common scenarios

    def mock_award_search(
        self, awards: List[Dict[str, Any]], page_size: int = 100
    ) -> None:
        """Set up mock responses for award search.

        Args:
            awards: List of award data
            page_size: Results per page
        """
        # Ensure awards have required fields
        for award in awards:
            if "Award ID" not in award:
                award["Award ID"] = f"AWARD-{id(award)}"
            if "Recipient Name" not in award:
                award["Recipient Name"] = "Test Recipient"

        self.set_paginated_response("/search/spending_by_award/", awards, page_size)

        # Also mock the count endpoint since __len__ now calls count()
        # Default to contracts category for backward compatibility
        self.mock_award_count(contracts=len(awards))

    def mock_award_count(self, **counts) -> None:
        """Set up mock response for award count.

        Args:
            **counts: Keyword args for contracts, grants, etc.
        """
        response = ResponseBuilder.count_response(**counts)
        self.set_response("/search/spending_by_award_count/", response)

    def mock_award_detail(self, award_id: str, **award_data) -> None:
        """Set up mock response for award detail.

        Args:
            award_id: Award identifier
            **award_data: Additional award fields
        """
        response = ResponseBuilder.award_detail_response(
            award_id=award_id, **award_data
        )
        self.set_response(f"/awards/{award_id}/", response)

    def mock_transactions_for_award(
        self,
        award_id: str,
        fixture_name: Optional[str] = None,
        transactions: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Mock transactions response for a specific award.

        Args:
            award_id: Award identifier
            fixture_name: Name of fixture file (without .json)
            transactions: List of transaction data (overrides fixture)
        """
        if fixture_name:
            self.set_fixture_response("/transactions/", fixture_name)
        elif transactions:
            response = {
                "results": transactions,
                "page_metadata": {
                    "total": len(transactions),
                    "count": len(transactions),
                    "page": 1,
                    "hasNext": False,
                    "hasPrevious": False,
                    "next": None,
                    "previous": None,
                },
            }
            self.set_response("/transactions/", response)
        else:
            # Default empty response
            response = {
                "results": [],
                "page_metadata": {
                    "total": 0,
                    "count": 0,
                    "page": 1,
                    "has_next": False,
                    "has_previous": False,
                    "next": None,
                    "previous": None,
                },
            }
            self.set_response("/transactions/", response)

    def mock_recipient_search(
        self, recipients: List[Dict[str, Any]], page_size: int = 50
    ) -> None:
        """Set up mock responses for recipient search.

        Args:
            recipients: List of recipient data
            page_size: Results per page
        """
        # Ensure recipients have required fields
        for recipient in recipients:
            if "id" not in recipient:
                recipient["id"] = f"RECIPIENT-{id(recipient)}"
            if "name" not in recipient:
                recipient["name"] = "Test Recipient"
            if "amount" not in recipient:
                recipient["amount"] = 1000000.0

        self.set_paginated_response(self.Endpoints.RECIPIENT_SEARCH, recipients, page_size)

        # Count endpoint is now automatically set up by _auto_setup_count_endpoint()

    def mock_recipient_count(self, count: int) -> None:
        """Set up mock response for recipient count.

        Args:
            count: Total number of recipients
        """
        response = {"count": count}
        self.set_response(self.Endpoints.RECIPIENT_COUNT, response)
