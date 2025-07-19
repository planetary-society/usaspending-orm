# usaspendingapi/models/base.py
from typing import Optional, Dict, Any, TypeVar, List, TYPE_CHECKING
from weakref import ref

if TYPE_CHECKING:
    from usaspending.client import USASpending

T = TypeVar('T')

class BaseModel:
    """Base class for all models with fundamental behaviors."""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data or {}
    
    @property
    def raw(self) -> Dict[str, Any]:
        """Get raw data dictionary."""
        return self._data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self._data

    def get_value(self, keys: List[str], default: Any = None) -> Any:
        """ Return the first truthy value from the given keys."""
        if not isinstance(keys, list):
            keys = [keys]
        
        if not isinstance(self._data, dict):
            raise TypeError("Empty object data")
        for key in keys:
            if key in self._data:
                value = self._data[key]
                if value:  # Check for truthiness instead of just non-None
                    return value
        return default
        

class ClientAwareModel(BaseModel):
    """Base class for all models that need API client access."""
    
    def __init__(self, data: Dict[str, Any], client: 'USASpending'):
        super().__init__(data)
        self._client_ref = ref(client)  # Weak reference prevents circular refs
    
    @property
    def _client(self) -> Optional['USASpending']:
        """Get client instance if still alive."""
        return self._client_ref() if self._client_ref else None
    
