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
from ..logging_config import USASpendingLogger, log_query_execution

T = TypeVar("T")

if TYPE_CHECKING:
    from ..client import USASpending

logger = USASpendingLogger.get_logger(__name__)

class QueryBuilder(ABC, Generic[T]):
    """Base query builder with automatic pagination support."""
    
    def __init__(self, client: "USASpending"):
        self._client = client
        self._filters: Dict[str, Any] = {}
        self._limit = 100  # Per page
        self._max_pages = None  # Limit total pages fetched
        self._order_by = None
        self._order_direction = "desc"
    
    def limit(self, num: int) -> "QueryBuilder[T]":
        """Set page size (max 100 per USASpending API)."""
        clone = self._clone()
        clone._limit = min(num, 100)
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
        """Iterate over all results, respecting the user's limit and handling pagination."""
        page = 1
        pages_fetched = 0
        items_yielded = 0  # Track the total number of items yielded

        query_type = self.__class__.__name__
        logger.info(
            f"Starting {query_type} iteration with total limit={self._limit}, "
            f"max_pages={self._max_pages}"
        )

        while True:
            # Primary exit condition: Stop if we've yielded the number of items the user wants.
            if self._limit is not None and items_yielded >= self._limit:
                logger.debug(f"User-defined limit of {self._limit} items reached. Halting.")
                break

            # Secondary exit condition for safety
            if self._max_pages and pages_fetched >= self._max_pages:
                logger.debug(f"Reached max_pages limit ({self._max_pages}). Halting.")
                break

            response = self._execute_query(page)
            results = response.get("results", [])
            has_next = response.get("page_metadata", {}).get("hasNext", False)

            logger.debug(f"Fetched page {page} with {len(results)} results. hasNext: {has_next}")

            # If a page comes back empty, there's no more data.
            if not results:
                logger.debug("Fetched an empty page. Halting.")
                break

            for item in results:
                # Check the limit again before each yield. This handles the case
                # where the limit is reached mid-page.
                if self._limit is not None and items_yielded >= self._limit:
                    break
                
                yield self._transform_result(item)
                items_yielded += 1

            # If the API says there's no next page, we are done.
            if not has_next:
                logger.debug("Last page reached (hasNext is false). Halting.")
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
    
    def count(self) -> int:
        """Get total count without fetching all results."""
        logger.debug(f"{self.__class__.__name__}.count() called")
        # Make a request with limit=1 to get total count
        original_limit = self._limit
        self._limit = 1
        
        response = self._execute_query(page=1)
        total = response.get("page_metadata", {}).get("total", 0)
        
        self._limit = original_limit
        logger.info(f"{self.__class__.__name__}.count() = {total}")
        return total
    
    @property
    def _endpoint(self) -> str:
        """API endpoint for this query."""
        pass
    
    @abstractmethod
    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Build request payload."""
        pass
    
    @abstractmethod
    def _transform_result(self, data: Dict[str, Any]) -> T:
        """Transform raw result to model instance."""
        pass
    
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
        clone._limit = self._limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        return clone