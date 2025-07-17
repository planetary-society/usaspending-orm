from abc import ABC, abstractmethod
from typing import Iterator, List, Dict, Any, Optional, TypeVar, Generic, TYPE_CHECKING

# Import exceptions for use by all query builders
from ..exceptions import (
    USASpendingError,
    APIError,
    HTTPError,
    ValidationError,
    RateLimitError,
    ConfigurationError,
)

from .filters import BaseFilter

from ..logging_config import USASpendingLogger, log_query_execution

T = TypeVar("T")

if TYPE_CHECKING:
    from ..client import USASpending

logger = USASpendingLogger.get_logger(__name__)

class QueryBuilder(ABC, Generic[T]):
    """Base query builder with automatic pagination support.
    
    Provides transparent pagination handling for USASpending API queries.
    - Use limit() to set the total number of items to retrieve across all pages
    - Use page_size() to control how many items are fetched per API request
    - Use max_pages() to limit the number of API requests made
    """
    
    def __init__(self, client: "USASpending"):
        self._client = client
        self._filters: Dict[str, Any] = {}
        self._filter_objects: list[BaseFilter] = []
        self._page_size = 100  # Items per page (max 100 per USASpending API)
        self._total_limit = None  # Total items to return (across all pages)
        self._max_pages = None  # Limit total pages fetched
        self._order_by = None
        self._order_direction = "desc"
    
    def limit(self, num: int) -> "QueryBuilder[T]":
        """Set the total number of items to return across all pages."""
        clone = self._clone()
        clone._total_limit = num
        return clone
    
    def page_size(self, num: int) -> "QueryBuilder[T]":
        """Set page size (max 100 per USASpending API)."""
        clone = self._clone()
        clone._page_size = min(num, 100)
        return clone
    
    def max_pages(self, num: int) -> "QueryBuilder[T]":
        """Limit total number of pages fetched."""
        clone = self._clone()
        clone._max_pages = num
        return clone
    
    def order_by(self, field: str, direction: str = "desc") -> "QueryBuilder[T]":
        """Set sort order."""
        clone = self._clone()
        clone._order_by = field
        clone._order_direction = direction
        return clone
    
    def __iter__(self) -> Iterator[T]:
        """Iterate over all results, handling pagination automatically."""
        page = 1
        pages_fetched = 0
        items_yielded = 0

        query_type = self.__class__.__name__
        effective_page_size = self._get_effective_page_size()
        logger.info(
            f"Starting {query_type} iteration with page_size={effective_page_size}, "
            f"total_limit={self._total_limit}, max_pages={self._max_pages}"
        )

        while True:
            # Check if we've reached the total limit
            if self._total_limit is not None and items_yielded >= self._total_limit:
                logger.debug(f"Total limit of {self._total_limit} items reached")
                break

            # Check if we've reached the max pages limit
            if self._max_pages and pages_fetched >= self._max_pages:
                logger.debug(f"Max pages limit ({self._max_pages}) reached")
                break

            response = self._execute_query(page)
            results = response.get("results", [])
            has_next = response.get("page_metadata", {}).get("hasNext", False)

            logger.debug(f"Page {page}: {len(results)} results, hasNext={has_next}")

            # Empty page means no more data
            if not results:
                logger.debug("Empty page returned")
                break

            for item in results:
                # Check limit before each yield to handle mid-page limits
                if self._total_limit is not None and items_yielded >= self._total_limit:
                    logger.debug(f"Stopping mid-page at item {items_yielded}")
                    return
                
                yield self._transform_result(item)
                items_yielded += 1

            # API indicates no more pages
            if not has_next:
                logger.debug("Last page reached (hasNext=false)")
                break

            page += 1
            pages_fetched += 1
    
    def first(self) -> Optional[T]:
        """Get first result only."""
        logger.debug(f"{self.__class__.__name__}.first() called")
        for result in self.limit(1):
            return result
        return None
    
    def all(self) -> List[T]:
        """Get all results as a list."""
        logger.debug(f"{self.__class__.__name__}.all() called")
        results = list(self)
        logger.info(f"{self.__class__.__name__}.all() returned {len(results)} results")
        return results
    
    @abstractmethod
    def count(self) -> int:
        """Get total count without fetching all results."""
        pass
    
    @property
    def _endpoint(self) -> str:
        """API endpoint for this query."""
        pass
    
    @abstractmethod
    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Build request payload."""
        pass
    
    def _get_effective_page_size(self) -> int:
        """Get the effective page size based on limit and configured page size."""
        if self._total_limit is not None:
            return min(self._page_size, self._total_limit)
        return self._page_size
    
    @abstractmethod
    def _transform_result(self, data: Dict[str, Any]) -> T:
        """Transform raw result to model instance."""
        pass
    
    def _aggregate_filters(self) -> dict[str, Any]:
        """Aggregates all filter objects into a single dictionary payload."""
        final_filters: dict[str, Any] = {}

        # Aggregate filters
        for f in self._filter_objects:
            f_dict = f.to_dict()
            for key, value in f_dict.items():
                if key in final_filters and isinstance(final_filters[key], list):
                    final_filters[key].extend(value)
                # Skip keys with empty values to keep payload clean
                elif value:
                    final_filters[key] = value
        
        logger.debug(f"Applied {len(self._filter_objects)} filters to query")
        
        return final_filters
    
    
    def _fetch_page(self, page: int) -> List[Dict[str, Any]]:
        """Fetch a single page of results."""
        response = self._execute_query(page)
        return response.get("results", [])
    
    def _execute_query(self, page: int) -> Dict[str, Any]:
        """Execute the query and return raw response."""
        query_type = self.__class__.__name__
        filters_count = len(self._filters)
        endpoint = self._endpoint()
        
        log_query_execution(logger, query_type, filters_count, endpoint, page)
        
        payload = self._build_payload(page)
        logger.debug(f"Query payload: {payload}")
        
        response = self._client._make_request("POST", endpoint, json=payload)
        
        if "page_metadata" in response:
            metadata = response["page_metadata"]
            logger.debug(f"Page metadata: page={metadata.get('page')}, "
                       f"total={metadata.get('total')}, hasNext={metadata.get('hasNext')}")
        
        return response
    
    def _clone(self) -> "QueryBuilder[T]":
        """Create a copy for method chaining."""
        clone = self.__class__(self._client)
        clone._filters = self._filters.copy()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        return clone