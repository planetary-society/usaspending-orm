# usaspendingapi/models/lazy.py
from .base_model import ClientAwareModel
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from usaspending.client import USASpending


class LazyRecord(ClientAwareModel):
    """Enhanced LazyRecord that maintains client reference."""

    def __init__(self, data: Dict[str, Any], client: "USASpending"):
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
        else:
            # Try loading the value directly
            # If returned value is None, than try fetching
            # the source data
            value = None

            for key in keys:
                if key in self._data:
                    value = self._data[key]
                    break

            if value is None:
                # Load full resource data from source
                self._ensure_details()

                # Set flag
                self._details_fetched = True

                # Attempt to return the value again
                value = self.get_value(keys, default=default)
            return value
