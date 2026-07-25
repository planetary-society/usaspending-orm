"""TASAgenciesQuery - the top level of the TAS filter tree."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .filter_tree_query import FilterTreeQuery

if TYPE_CHECKING:
    from ..models.agency import Agency


class TASAgenciesQuery(FilterTreeQuery["Agency"]):
    """Lazy query for agencies that have Treasury Account Symbols.

    The root of the same tree ``FederalAccountsQuery`` and ``TASCodesQuery``
    read further down, so it fetches one unpaginated level once and filters it in
    memory. Being the root, it takes no scope: an agency code is what the level
    *returns*, not what selects it.

    Filters:
        - code(): Filter by agency toptier code.
        - codes(): Filter by multiple toptier codes.
        - description(): Filter by name text (substring, case-insensitive).

    Example:
        >>> agencies = client.tas.agencies_query
        >>> len(agencies)
        91
        >>> nasa = agencies.code("080").first()
    """

    ENDPOINT = "/references/filter_tree/tas/"

    #: Rows key the agency code under ``id``, but ``Agency`` exposes that as
    #: ``code``; its own ``id`` is the internal database ID and is None here, so
    #: leaving the default would make :meth:`code` match nothing.
    CODE_KEY = "code"

    #: ``Agency`` has no ``description``, so a keyword search reads its name.
    KEYWORD_FIELDS = ("name",)

    def _scope(self) -> dict[str, str]:
        """Return no scope: the root level selects nothing.

        An empty mapping is not the "unscoped, so answer nothing" case the base
        describes. That case is a scope whose *values* are empty; here there are
        no values to be missing, and ``all(())`` is True, so the fetch proceeds.
        """
        return {}

    def _build_model(self, data: dict[str, Any]) -> Agency:
        """Build an Agency from a filter-tree node.

        Filter-tree rows describe a node rather than an agency, so ``id`` and
        ``description`` are mapped onto the code and name an Agency expects.
        """
        from ..models.agency import Agency

        return Agency(
            {
                "toptier_code": data.get("id"),
                "code": data.get("id"),
                "name": data.get("description"),
                # Retained for reference: how many TAS this agency has.
                "_tas_count": data.get("count", 0),
            },
            self._client,
        )

    def _new_instance(self) -> TASAgenciesQuery:
        """Reconstruct; there is no scope to carry."""
        return self.__class__(self._client)
