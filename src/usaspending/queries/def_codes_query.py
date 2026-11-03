"""DefCodesQuery - the Disaster Emergency Fund Code reference list."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .filter_tree_query import FilterTreeQuery

if TYPE_CHECKING:
    from ..models.def_code import DefCode


class DefCodesQuery(FilterTreeQuery["DefCode"]):
    """Lazy query for the API's current Disaster Emergency Fund Codes.

    The endpoint returns one unpaginated, unscoped list, the same shape as the
    root of a filter tree, so it is fetched once per query and filtered in memory.

    Filters:
        - code(): Filter by DEF code.
        - codes(): Filter by multiple DEF codes.
        - description(): Filter by title, public law, or disaster text
          (substring, case-insensitive).

    Example:
        >>> def_codes = DefCodesQuery(client)
        >>> covid = def_codes.description("covid").all()
        >>> infrastructure = def_codes.code("Z").first()
    """

    ENDPOINT = "/references/def_codes/"
    RESULTS_KEY = "codes"
    CODE_KEY = "code"
    KEYWORD_FIELDS = ("title", "public_law", "disaster")

    def _scope(self) -> dict[str, str]:
        """Return no scope: the list takes no path parameters.

        Returns:
            dict[str, str]: An empty mapping, so the fetch always proceeds.
        """
        return {}

    def _build_model(self, data: dict[str, Any]) -> DefCode:
        """Build a DefCode from one response row.

        Args:
            data: One DEF code row from the API response.

        Returns:
            DefCode: The parsed reference row.
        """
        from ..models.def_code import DefCode

        return DefCode._from_api_data(data)

    def _new_instance(self) -> DefCodesQuery:
        """Reconstruct; there is no scope to carry.

        Returns:
            DefCodesQuery: A new, unfetched query on the same client.
        """
        return self.__class__(self._client)
