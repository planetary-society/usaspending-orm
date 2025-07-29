"""Universal mock client for USASpending API tests."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock

from usaspending.client import USASpending
from usaspending.config import config
from usaspending.exceptions import APIError, HTTPError

from .response_builder import ResponseBuilder


class MockUSASpendingClient(USASpending):
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
            "/v2/search/spending_by_award/",
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
        **kwargs
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
            "timestamp": time.time()
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
                    response_body=error_data
                )
            else:
                raise HTTPError(
                    f"HTTP {status_code}: {error_data.get('error', 'Server Error')}",
                    status_code=status_code
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
        
        # Return empty response by default
        return ResponseBuilder.paginated_response([], has_next=False)
    
    def set_response(
        self,
        endpoint: str,
        response_data: Dict[str, Any],
        status_code: int = 200
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
                "status_code": status_code
            }
        else:
            self._default_responses[endpoint] = response_data
    
    def set_paginated_response(
        self,
        endpoint: str,
        items: List[Dict[str, Any]],
        page_size: int = 100
    ) -> None:
        """Automatically paginate a list of items.
        
        Args:
            endpoint: API endpoint
            items: List of all items to paginate
            page_size: Items per page
        """
        # Clear any existing responses
        self._responses[endpoint] = []
        
        # Create pages
        for i in range(0, len(items), page_size):
            page_items = items[i:i + page_size]
            page_num = (i // page_size) + 1
            has_next = (i + page_size) < len(items)
            
            response = ResponseBuilder.paginated_response(
                results=page_items,
                page=page_num,
                has_next=has_next
            )
            self._responses[endpoint].append(response)
        
        # If no items, add single empty response
        if not items:
            self._responses[endpoint].append(
                ResponseBuilder.paginated_response([], has_next=False)
            )
    
    def set_fixture_response(
        self,
        endpoint: str,
        fixture_name: str,
        transform: Optional[callable] = None
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
        detail: Optional[str] = None
    ) -> None:
        """Simulate API errors.
        
        Args:
            endpoint: API endpoint
            error_code: HTTP error code
            error_message: General error message
            detail: Detailed error message (for 400 errors)
        """
        error_data = ResponseBuilder.error_response(
            status_code=error_code,
            detail=detail,
            error=error_message
        )
        self.set_response(endpoint, error_data, status_code=error_code)
    
    def add_response_sequence(
        self,
        endpoint: str,
        responses: List[Dict[str, Any]]
    ) -> None:
        """Add multiple responses for sequential calls.
        
        Args:
            endpoint: API endpoint
            responses: List of responses to return in sequence
        """
        self._responses[endpoint].extend(responses)
    
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
    
    def get_last_request(self, endpoint: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
        params: Optional[Dict[str, Any]] = None
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
            if (request["endpoint"] == endpoint and
                request["method"] == method and
                (json is None or request["json"] == json) and
                (params is None or request["params"] == params)):
                return
                
        raise AssertionError(
            f"Request not found: {method} {endpoint} "
            f"with json={json}, params={params}"
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
    
    # Convenience methods for common scenarios
    
    def mock_award_search(
        self,
        awards: List[Dict[str, Any]],
        page_size: int = 100
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
                
        self.set_paginated_response(
            "/v2/search/spending_by_award/",
            awards,
            page_size
        )
        
        # Also mock the count endpoint since __len__ now calls count()
        # Default to contracts category for backward compatibility
        self.mock_award_count(contracts=len(awards))
    
    def mock_award_count(self, **counts) -> None:
        """Set up mock response for award count.
        
        Args:
            **counts: Keyword args for contracts, grants, etc.
        """
        response = ResponseBuilder.count_response(**counts)
        self.set_response("/v2/search/spending_by_award_count/", response)
    
    def mock_award_detail(self, award_id: str, **award_data) -> None:
        """Set up mock response for award detail.
        
        Args:
            award_id: Award identifier
            **award_data: Additional award fields
        """
        response = ResponseBuilder.award_detail_response(
            award_id=award_id,
            **award_data
        )
        self.set_response(f"/v2/awards/{award_id}/", response)

    def mock_transactions_for_award(
        self,
        award_id: str,
        fixture_name: Optional[str] = None,
        transactions: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Mock transactions response for a specific award.
        
        Args:
            award_id: Award identifier
            fixture_name: Name of fixture file (without .json)
            transactions: List of transaction data (overrides fixture)
        """
        if fixture_name:
            self.set_fixture_response("/v2/transactions/", fixture_name)
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
                    "previous": None
                }
            }
            self.set_response("/v2/transactions/", response)
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
                    "previous": None
                }
            }
            self.set_response("/v2/transactions/", response)