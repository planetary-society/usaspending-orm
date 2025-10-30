# usaspending/models/lazy_record.py
from .base_model import ClientAwareModel
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import USASpendingClient


class LazyRecord(ClientAwareModel):
    """Enhanced LazyRecord that maintains client reference."""

    def __init__(self, data: Dict[str, Any], client: "USASpendingClient"):
        super().__init__(data, client)
        self._details_fetched = False

    def _ensure_details(self) -> None:
        """Fetch full details using the client."""
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

    def _fetch_details(self) -> Optional[Dict[str, Any]]:
        """Override in subclasses."""
        raise NotImplementedError

    def _lazy_get(self, *keys: str, default: Any = None) -> Any:
        """Get value, triggering lazy load if needed."""

        keys = list(keys)

        # If we've already lazy-loaded details, return whatever
        # values are present in the data
        if self._details_fetched:
            return self.get_value(keys, default=default)

        # Check if any of the keys exist in the current data
        key_found = False
        value = None

        for key in keys:
            if key in self._data:
                value = self._data[key]
                key_found = True
                break

        # If no key was found, or if the value is None (indicating missing data),
        # trigger lazy loading
        if not key_found or value is None:
            # Load full resource data from source
            self._ensure_details()

            # Set flag
            self._details_fetched = True

            # Attempt to return the value again
            value = self.get_value(keys, default=default)

        return value
