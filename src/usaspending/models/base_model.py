# usaspending/models/base_model.py
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Any, ClassVar
from weakref import ref

if TYPE_CHECKING:
    from ..client import USASpendingClient

from ..exceptions import DetachedInstanceError, ValidationError


class BaseModel:
    """Base class for all models with fundamental behaviors.

    This class provides the basic structure for data-holding models,
    including initialization, data validation, and dictionary conversion.
    """

    def __init__(self, data: dict[str, Any]):
        """Initialize the model with data.

        Args:
            data: A dictionary containing the model data.
        """
        self._data = data or {}

    @staticmethod
    def validate_init_data(
        data_or_id: Any,
        model_name: str,
        id_field: str | None = None,
        allow_string_id: bool = False,
    ) -> dict[str, Any]:
        """Validate and normalize initialization data for models.

        Args:
            data_or_id: Input data (dict, string, or other type).
            model_name: Name of the model for error messages.
            id_field: Field name for ID when string is provided.
            allow_string_id: Whether to accept string as ID.

        Returns:
            Normalized dictionary of data.

        Raises:
            ValidationError: If data is invalid (None, wrong type, or empty string ID).
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
            raise ValidationError(f"{model_name} expects dict or string, got {type_name}")
        else:
            raise ValidationError(f"{model_name} expects dict, got {type_name}")

    @property
    def raw(self) -> dict[str, Any]:
        """Get the underlying raw data dictionary.

        Returns:
            Dict[str, Any]: The raw data dictionary used to initialize the model.
        """
        return self._data

    def to_dict(self) -> dict[str, Any]:
        """Convert the model data to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model data.
        """
        return self._data

    def get_value(self, keys: Iterable[str] | str, default: Any = None) -> Any:
        """Return the first non-None value from the given keys.

        Args:
            keys: A string key, or an iterable of keys tried in order.
            default: The value to return if no key is found or values are None.

        Returns:
            Any: The value found for the first matching key, or the default value.

        Raises:
            TypeError: If the underlying data is not a dictionary.
        """
        if isinstance(keys, str):
            keys = [keys]

        if not isinstance(self._data, dict):
            raise TypeError("Empty object data")
        for key in keys:
            value = self._data.get(key)
            if value is not None:
                return value
        return default


class ClientAwareModel(BaseModel):
    """Base class for all models that need API client access.

    This class extends BaseModel to include a weak reference to the USASpendingClient,
    allowing models to fetch additional data or lazy-load properties without
    creating circular references.
    """

    #: Names of caches of models to discard on a non-recursive :meth:`reattach`,
    #: whose models would otherwise go on serving the outgoing client. A recursive
    #: reattach rebinds them in place and keeps the cache instead, so an entry must
    #: hold models the walk can reach: a model, or a dict/list/tuple/set of them.
    #:
    #: Two subclasses override it, one filter-tree level each. Growing that past a
    #: couple is the signal to replace this with a descriptor that checks staleness
    #: when the level is read, which would retire the tuple and the non-recursive
    #: branch of :meth:`reattach` together, for under a microsecond per read.
    _REATTACH_INVALIDATES: ClassVar[tuple[str, ...]] = ()

    def __init__(self, data: dict[str, Any], client: USASpendingClient):
        """Initialize the client-aware model.

        Args:
            data: A dictionary containing the model data.
            client: The USASpendingClient instance to associate with this model.
        """
        if client is None:
            raise ValidationError(
                f"{self.__class__.__name__} requires a USASpendingClient instance."
            )
        super().__init__(data)
        self._client_ref = ref(client)  # Weak reference prevents circular refs

    @property
    def _client(self) -> USASpendingClient:
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
        client: USASpendingClient,
        recursive: bool = False,
        _visited: set[int] | None = None,
    ) -> None:
        """Reattach this model to a new client session.

        This method updates the model's client reference to point to a new
        USASpendingClient, allowing you to use objects created in one session
        within a different session context.

        Args:
            client: The new USASpendingClient to attach to.
            recursive: If True, recursively reattach nested models that hold the
                      client (e.g., award.recipient, award.awarding_agency, and the
                      models inside a cached level such as
                      agency.federal_accounts). Default False.
            _visited: Internal parameter for cycle detection. Do not pass manually.

        Example:
            >>> # Create objects in one session
            >>> with USASpendingClient() as client:
            ...     award = client.awards.find_by_award_id("123")
            ...     # Session closes here
            >>> # Later, reattach to a new session
            >>> with USASpendingClient() as new_client:
            ...     award.reattach(new_client)
            ...     print(award.subaward_count)  # Now works!
            >>> # Recursive reattach for nested objects
            >>> with USASpendingClient() as new_client:
            ...     award.reattach(new_client, recursive=True)
            ...     # Now award.recipient and award.awarding_agency also reattached
            ...     print(award.recipient.name)

        Note:
            QueryBuilder properties (like award.transactions) are not affected
            by reattach. They create new query builders when accessed, which
            automatically use the reattached client. Where such a property is served
            from a cache of already-built models, a recursive reattach rebinds those
            models in place, so the cache survives and its level is not fetched
            again. A non-recursive one cannot rebind them, so it discards the caches
            named in :attr:`_REATTACH_INVALIDATES` and the next read rebuilds them.
            Note the limit of that: a model the caller had already taken out of such
            a cache stays bound to the old client either way, so ``recursive=True``
            repairs the graph while the default only keeps this model working.

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

        if not recursive:
            # cached_property stores into the instance __dict__, so popping clears it.
            for name in self._REATTACH_INVALIDATES:
                self.__dict__.pop(name, None)
            return

        # Initialize visited set for cycle detection
        if _visited is None:
            _visited = set()

        # Prevent infinite recursion on circular references
        obj_id = id(self)
        if obj_id in _visited:
            return
        _visited.add(obj_id)

        # `_data` is skipped: it is the raw API payload, so models are built from it
        # rather than stored in it, and descending it walks the whole response node
        # by node. That is 93% of the work of reattaching an award.
        for name, attr_value in self.__dict__.items():
            if name == "_data":
                continue
            for nested in _iter_client_aware_models(attr_value):
                nested.reattach(client, recursive=True, _visited=_visited)


def _iter_client_aware_models(value: Any) -> Iterator[ClientAwareModel]:
    """Yield the client-aware models held in `value`, at any nesting depth.

    Reads only what is already in hand, never a property, so walking a model does
    not trigger a lazy fetch. Holding a client is what makes a model need
    rebinding, so :class:`ClientAwareModel` is what this tests, rather than
    :class:`~usaspending.models.lazy_record.LazyRecord`.

    Args:
        value: Any attribute value: a model, a container of them, or neither.

    Yields:
        ClientAwareModel: Each model found, in traversal order.
    """
    if isinstance(value, ClientAwareModel):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_client_aware_models(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _iter_client_aware_models(child)
