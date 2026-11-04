"""Reference-data resource implementation."""

from __future__ import annotations

from ..queries.countries_query import CountriesQuery
from ..queries.def_codes_query import DefCodesQuery
from ..queries.states_query import StatesQuery
from .base_resource import BaseResource


class ReferencesResource(BaseResource):
    """Resource for USAspending reference-data endpoints."""

    def def_codes(self) -> DefCodesQuery:
        """Return a query over the API's current Disaster Emergency Fund Codes.

        The query is lazy: it makes one GET request to ``/references/def_codes/``
        when first evaluated and reuses those rows for filtering and repeated
        reads. Each call returns a new, unfetched query.

        Returns:
            DefCodesQuery: Query supporting ``code()``, ``codes()``,
            ``description()``, iteration, ``len()``, indexing and ``all()``.

        Example:
            >>> for def_code in client.references.def_codes():
            ...     print(def_code.code, def_code.title)
            >>> covid = client.references.def_codes().description("covid").all()
        """
        return DefCodesQuery(self._client)

    def countries(self) -> CountriesQuery:
        """Return a lazy query over country and special-location reference data.

        Each call returns a fresh query. Its first evaluation fetches the full
        list; subsequent reads and filtering reuse those rows in memory.

        Returns:
            CountriesQuery: Query supporting ``code()``, ``codes()``,
            ``description()``, iteration, indexing, and ``all()``.

        Example:
            >>> canada = client.references.countries().code("CAN").first()
        """
        return CountriesQuery(self._client)

    def states(self) -> StatesQuery:
        """Return a lazy query over U.S. states, districts, and territories.

        Each call returns a fresh query. Its first evaluation fetches the full
        list; subsequent reads and filtering reuse those rows in memory.
        FIPS codes remain strings, preserving leading zeros.

        Returns:
            StatesQuery: Query supporting ``code()``, ``codes()``,
            ``description()``, iteration, indexing, and ``all()``.

        Example:
            >>> alaska = client.references.states().description("alaska").first()
        """
        return StatesQuery(self._client)
