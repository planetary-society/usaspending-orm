# usaspending/models/lazy_record.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base_model import ClientAwareModel

if TYPE_CHECKING:
    from ..client import USASpendingClient


class LazyRecord(ClientAwareModel):
    """Enhanced LazyRecord that maintains client reference."""

    def __init__(self, data: dict[str, Any], client: USASpendingClient):
        """Initialize LazyRecord.

        Args:
            data: Initial data dictionary.
            client: The USASpendingClient instance.
        """
        super().__init__(data, client)
        self._details_fetched = False

    def _ensure_details(self) -> None:
        """Fetch full details using the client if not already fetched."""
        if self._details_fetched:
            return

        new_data = self._fetch_details()
        if new_data:
            self._data.update(new_data)
        self._details_fetched = True

    def fetch_all_details(self) -> None:
        """Eagerly fetch all lazy-loadable data for this model.

        This method is useful when you need to access model properties outside
        of the client context manager. Call this method before the client session
        closes to ensure all data is fetched.

        Example:
            with USASpendingClient() as client:
                awards = client.awards.search().limit(10).all()
                for award in awards:
                    award.fetch_all_details()  # Fetch all lazy data
            # Now safe to use awards outside the context
            print(awards[0].subaward_count)

        Raises:
            DetachedInstanceError: If the client session is already closed.
        """
        self._ensure_details()

    def _fetch_details(self) -> dict[str, Any] | None:
        """Fetch details from the source.

        Override this method in subclasses to implement the specific
        fetching logic.

        The contract is narrow: return a plain dict of raw API fields, obtained
        **without constructing another model of this same type**. ``_ensure_details``
        merges the result into ``self._data``, so building a sibling model just to
        read its ``raw()`` wastes a construction and, for types whose own
        properties lazy-load, risks recursing back into this method.

        Note:
            The three implementations differ in shape and error policy, and that
            divergence is known rather than intended:

            * :meth:`Agency._fetch_details` asks a query object for a dict and
              swallows failures, returning None. This is the shape to copy.
            * :meth:`Recipient._fetch_details` issues a direct request and also
              swallows failures. It deliberately bypasses the resource layer to
              avoid a circular dependency, per commit 9033115; routing it back
              through ``client.recipients`` would both reintroduce that and build
              a throwaway ``Recipient`` only to read its ``raw()``.
            * :meth:`Award._fetch_details` goes through the public resource, then
              reads ``.raw`` off the returned model, and re-raises rather than
              swallowing. It is the outlier on both counts, and it is entangled
              with the deliberate ``__class__`` reassignment documented there, so
              it is left as-is.

            A caller therefore cannot assume that a failed lazy load surfaces as
            an exception: two of the three report it as absent data.

        Returns:
            Optional[Dict[str, Any]]: The fetched data dictionary, or None.

        Raises:
            NotImplementedError: If not implemented in subclass.
        """
        raise NotImplementedError

    def _lazy_get(self, *keys: str, default: Any = None) -> Any:
        """Get value, triggering lazy load if needed.

        Args:
            *keys: Variable length argument list of keys to look up.
            default: Default value to return if no key is found.

        Returns:
            Any: The value found for the first matching key, or the default value.
        """
        keys_list = list(keys)

        # If we haven't fetched details yet, check whether any key
        # exists in current data. If no key is present at all, trigger
        # a lazy load. A key present with a None value is treated as
        # legitimate API data (not missing), so it does NOT trigger a fetch.
        if not self._details_fetched and not any(key in self._data for key in keys_list):
            self._ensure_details()

        # Delegate to get_value for consistent multi-key lookup semantics:
        # it skips None values, tries alternate keys, and returns default.
        return self.get_value(keys_list, default=default)
