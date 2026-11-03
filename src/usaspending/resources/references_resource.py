"""Reference-data resource implementation."""

from __future__ import annotations

from ..queries.def_codes_query import DefCodesQuery
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
