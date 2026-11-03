"""Lazy country reference query."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .filter_tree_query import FilterTreeQuery

if TYPE_CHECKING:
    from ..models.country import Country


class CountriesQuery(FilterTreeQuery["Country"]):
    """Fetch countries once, then filter by code or name in memory.

    ``code()`` and ``codes()`` match country codes; ``description()`` searches
    names case-insensitively. Country codes are preserved as the API reports
    them, including special locations such as AX2.
    """

    ENDPOINT = "/references/countries/"
    CODE_KEY = "code"
    KEYWORD_FIELDS = ("name",)

    def _scope(self) -> dict[str, str]:
        """Return no scope: this endpoint lists all countries."""
        return {}

    def _build_model(self, data: dict[str, Any]) -> Country:
        """Build a country while preserving the API's code and name."""
        from ..models.country import Country

        return Country(code=data.get("code", ""), name=data.get("name", ""))

    def _new_instance(self) -> CountriesQuery:
        """Return a fresh query on the same client."""
        return self.__class__(self._client)
