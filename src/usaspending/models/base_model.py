# usaspending/models/base_model.py
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from weakref import ref

if TYPE_CHECKING:
    from ..client import USASpendingClient

from ..exceptions import ValidationError


class BaseModel:
    """Base class for all models with fundamental behaviors."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data or {}

    @staticmethod
    def validate_init_data(
        data_or_id: Any,
        model_name: str,
        id_field: Optional[str] = None,
        allow_string_id: bool = False
    ) -> Dict[str, Any]:
        """
        Validate and normalize initialization data for models.
        
        Args:
            data_or_id: Input data (dict, string, or other type)
            model_name: Name of the model for error messages
            id_field: Field name for ID when string is provided
            allow_string_id: Whether to accept string as ID
            
        Returns:
            Normalized dictionary of data
            
        Raises:
            ValidationError: If data is invalid
        """
        if data_or_id is None:
            raise ValidationError(
                f"{model_name} data cannot be None. This may indicate an API or caching issue."
            )
        
        if isinstance(data_or_id, dict):
            # Return a copy to avoid modifying the original
            return data_or_id.copy()
        
        if isinstance(data_or_id, str):
            if not allow_string_id:
                raise ValidationError(
                    f"{model_name} expects dict, got str"
                )
            
            if not id_field:
                raise ValidationError(
                    f"{model_name} expects dict, got str"
                )
            
            if not data_or_id.strip():
                raise ValidationError(
                    f"{model_name} ID cannot be empty or whitespace"
                )
            
            return {id_field: data_or_id}
        
        # Invalid type
        type_name = type(data_or_id).__name__
        if allow_string_id:
            raise ValidationError(
                f"{model_name} expects dict or string, got {type_name}"
            )
        else:
            raise ValidationError(
                f"{model_name} expects dict, got {type_name}"
            )

    @property
    def raw(self) -> Dict[str, Any]:
        """Get raw data dictionary."""
        return self._data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self._data

    def get_value(self, keys: List[str], default: Any = None) -> Any:
        """Return the first non-None value from the given keys."""
        if not isinstance(keys, list):
            keys = [keys]

        if not isinstance(self._data, dict):
            raise TypeError("Empty object data")
        for key in keys:
            if key in self._data:
                value = self._data[key]
                if value is not None:  # Check for non-None instead of truthiness
                    return value
        return default


class ClientAwareModel(BaseModel):
    """Base class for all models that need API client access."""

    def __init__(self, data: Dict[str, Any], client: "USASpendingClient"):
        super().__init__(data)
        self._client_ref = ref(client)  # Weak reference prevents circular refs

    @property
    def _client(self) -> Optional["USASpendingClient"]:
        """Get client instance if still alive."""
        return self._client_ref() if self._client_ref else None
