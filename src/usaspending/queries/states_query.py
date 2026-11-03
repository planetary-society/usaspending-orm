"""Lazy state, district, and territory reference query."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .filter_tree_query import FilterTreeQuery

if TYPE_CHECKING:
    from ..models.state import State


class StatesQuery(FilterTreeQuery["State"]):
    """Fetch states, districts, and territories once, then filter in memory.

    ``code()`` and ``codes()`` match two-letter codes; ``description()`` searches
    names case-insensitively. FIPS codes remain strings with leading zeros.
    """

    ENDPOINT = "/references/states/"
    CODE_KEY = "code"
    KEYWORD_FIELDS = ("name",)

    def _scope(self) -> dict[str, str]:
        """Return no scope: this endpoint lists all states and territories."""
        return {}

    def _build_model(self, data: dict[str, Any]) -> State:
        """Build a state while preserving string codes and the API's name."""
        from ..models.state import State

        return State(
            fips=data.get("fips", ""), code=data.get("code", ""), name=data.get("name", "")
        )

    def _new_instance(self) -> StatesQuery:
        """Return a fresh query on the same client."""
        return self.__class__(self._client)
