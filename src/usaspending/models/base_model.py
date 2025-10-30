# usaspending/models/base_model.py
from typing import Optional, Dict, Any, List, Set, TYPE_CHECKING
from weakref import ref

if TYPE_CHECKING:
    from ..client import USASpendingClient

from ..exceptions import ValidationError, DetachedInstanceError


class BaseModel:
    """Base class for all models with fundamental behaviors."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data or {}

    @staticmethod
    def validate_init_data(
        data_or_id: Any,
        model_name: str,
        id_field: Optional[str] = None,
        allow_string_id: bool = False,
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
                raise ValidationError(f"{model_name} expects dict, got str")

            if not id_field:
                raise ValidationError(f"{model_name} expects dict, got str")

            if not data_or_id.strip():
                raise ValidationError(f"{model_name} ID cannot be empty or whitespace")

            return {id_field: data_or_id}

        # Invalid type
        type_name = type(data_or_id).__name__
        if allow_string_id:
            raise ValidationError(
                f"{model_name} expects dict or string, got {type_name}"
            )
        else:
            raise ValidationError(f"{model_name} expects dict, got {type_name}")

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
    def _client(self) -> "USASpendingClient":
        """Get client instance if still alive and usable.

        Returns:
            USASpendingClient: The client instance.

        Raises:
            DetachedInstanceError: If the client has been closed or garbage collected.
        """
        client = self._client_ref() if self._client_ref else None

        if client is None:
            raise DetachedInstanceError(
                f"Cannot access {self.__class__.__name__} properties: "
                "the USASpendingClient has been garbage collected. "
                "Ensure the client remains in scope, or access all needed data "
                "within the 'with USASpendingClient()' context block."
            )

        if hasattr(client, "_closed") and client._closed:
            raise DetachedInstanceError(
                f"Cannot access {self.__class__.__name__} properties: "
                "the USASpendingClient session is closed. "
                "Access all lazy-loaded properties within the 'with' block, "
                "or use explicit cleanup (client.close()) only after you're done with the models."
            )

        return client

    def reattach(
        self,
        client: "USASpendingClient",
        recursive: bool = False,
        _visited: Optional[Set[int]] = None,
    ) -> None:
        """Reattach this model to a new client session.

        This method updates the model's client reference to point to a new
        USASpendingClient, allowing you to use objects created in one session
        within a different session context.

        Args:
            client: The new USASpendingClient to attach to.
            recursive: If True, recursively reattach nested LazyRecord objects
                      (e.g., award.recipient, award.awarding_agency). Default False.
            _visited: Internal parameter for cycle detection. Do not pass manually.

        Example:
            >>> # Create objects in one session
            >>> with USASpendingClient() as client:
            ...     award = client.awards.find_by_award_id("123")
            ...     # Session closes here
            ...
            >>> # Later, reattach to a new session
            >>> with USASpendingClient() as new_client:
            ...     award.reattach(new_client)
            ...     print(award.subaward_count)  # Now works!
            ...
            >>> # Recursive reattach for nested objects
            >>> with USASpendingClient() as new_client:
            ...     award.reattach(new_client, recursive=True)
            ...     # Now award.recipient and award.awarding_agency also reattached
            ...     print(award.recipient.name)

        Note:
            QueryBuilder properties (like award.transactions) are not affected
            by reattach. They create new query builders when accessed, which
            automatically use the reattached client.

        Raises:
            DetachedInstanceError: If the provided client is closed.
        """
        # Validate that the new client is usable
        if hasattr(client, "_closed") and client._closed:
            raise DetachedInstanceError(
                f"Cannot reattach {self.__class__.__name__} to a closed client. "
                "Ensure the client is active (within a 'with' block or before close())."
            )

        # Update this model's client reference
        self._client_ref = ref(client)

        # Handle recursive reattachment if requested
        if recursive:
            # Import here to avoid circular dependency
            from .lazy_record import LazyRecord

            # Initialize visited set for cycle detection
            if _visited is None:
                _visited = set()

            # Prevent infinite recursion on circular references
            obj_id = id(self)
            if obj_id in _visited:
                return
            _visited.add(obj_id)

            # Find and reattach all LazyRecord properties
            for attr_name in dir(self):
                # Skip private attributes and methods
                if attr_name.startswith("_"):
                    continue

                try:
                    attr = getattr(self, attr_name)

                    # Recursively reattach LazyRecord instances
                    if isinstance(attr, LazyRecord):
                        attr.reattach(client, recursive=True, _visited=_visited)

                except (AttributeError, Exception):
                    # Skip properties that raise errors during access
                    # (e.g., properties that require API calls, methods, etc.)
                    pass
