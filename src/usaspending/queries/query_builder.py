from abc import ABC, abstractmethod
from typing import Iterator, List, Dict, Any, Optional, TypeVar, Generic, TYPE_CHECKING

T = TypeVar("T")

if TYPE_CHECKING:
    from ..client import USASpending

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
        """Iterate over all results with automatic pagination."""
        page = 1
        pages_fetched = 0
        
        while True:
            # Check max pages limit
            if self._max_pages and pages_fetched >= self._max_pages:
                break
            
            # Fetch page
            results = self._fetch_page(page)
            
            # Yield results
            for item in results:
                yield self._transform_result(item)
            
            # Check if more pages
            if len(results) < self._limit:
                break  # Last page
            
            page += 1
            pages_fetched += 1
    
    def first(self) -> Optional[T]:
        """Get first result only."""
        for result in self.limit(1):
            return result
        return None
    
    def all(self) -> List[T]:
        """Get all results as a list."""
        return list(self)
    
    def count(self) -> int:
        """Get total count without fetching all results."""
        # Make a request with limit=1 to get total count
        original_limit = self._limit
        self._limit = 1
        
        response = self._execute_query(page=1)
        total = response.get("page_metadata", {}).get("total", 0)
        
        self._limit = original_limit
        return total
    
    @abstractmethod
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
        payload = self._build_payload(page)
        return self._client._make_request("POST", self._endpoint(), json=payload)
    
    def _clone(self) -> "QueryBuilder[T]":
        """Create a copy for method chaining."""
        clone = self.__class__(self._client)
        clone._filters = self._filters.copy()
        clone._limit = self._limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        return clone