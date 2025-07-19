# usaspendingapi/models/lazy.py
from .base_model import ClientAwareModel
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from usaspending.client import USASpending

class LazyRecord(ClientAwareModel):
    """Enhanced LazyRecord that maintains client reference."""
    
    def __init__(self, data: Dict[str, Any], client: 'USASpending'):
        super().__init__(data, client)
        self._details_fetched = False
    
    def _ensure_details(self) -> None:
        """Fetch full details using the client."""
        if self._details_fetched:
            return
        
        client = self._client
        new_data = self._fetch_details()
        if new_data:
            self._data.update(new_data)
        self._details_fetched = True
    
    def _fetch_details(self) -> Optional[Dict[str, Any]]:
        """Override in subclasses."""
        raise NotImplementedError
    
    def _get(self, *keys: str, default: Any = None) -> Any:
        """Get value, triggering lazy load if needed."""
        for key in keys:
            if key in self._data:
                return self._data[key]
        
        # Trigger lazy load
        if not self._details_fetched:
            self._ensure_details()
            for key in keys:
                if key in self._data:
                    return self._data[key]
        
        return default