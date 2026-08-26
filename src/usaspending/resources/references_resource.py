"""Reference-data resource implementation."""

from __future__ import annotations

from ..models.def_code import DefCode
from .base_resource import BaseResource


class ReferencesResource(BaseResource):
    """Resource for USAspending reference-data endpoints."""

    _DEF_CODES_ENDPOINT = "/references/def_codes/"

    def def_codes(self) -> list[DefCode]:
        """Return the API's current Disaster Emergency Fund Code reference data."""
        response = self._client._make_request("GET", self._DEF_CODES_ENDPOINT)
        code_rows = response.get("codes", [])
        if not isinstance(code_rows, list):
            return []

        return [DefCode._from_api_data(row) for row in code_rows if isinstance(row, dict)]
