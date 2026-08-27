"""Agencies search query implementation for agency/office autocomplete."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Union

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..models.agency import Agency
from ..models.subtier_agency import SubTierAgency
from ..utils.validations import validate_agency_type
from .mixins import MaterializedIndexingQuery
from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)

_AgencySearchResult = Union[Agency, SubTierAgency]


class AgenciesSearch(
    MaterializedIndexingQuery[_AgencySearchResult], QueryBuilder[_AgencySearchResult]
):
    """Search for funding or awarding agencies and offices by name using autocomplete.

    This query builder uses the /v2/autocomplete/funding_agency_office/ or
    /v2/autocomplete/awarding_agency_office/ endpoint depending on agency type.
    Results can be filtered by type (toptier, subtier, or office). The upstream
    ``limit`` applies independently to each of those three buckets, so
    ``page_size(n)`` can receive up to ``3n`` raw rows. ``limit(n)`` remains the
    client-wide bound on the flattened result.
    """

    _MAX_PAGE_SIZE = 500

    def __init__(
        self,
        client: USASpendingClient,
        agency_type: Literal["funding", "awarding"] = "funding",
    ):
        """Initialize AgenciesSearch with client.

        Args:
            client: USASpending client instance.
            agency_type: "funding" or "awarding" (defaults to "funding").
        """
        super().__init__(client)
        self._agency_type = validate_agency_type(agency_type)
        self._search_text = ""
        # Filter: None, "toptier", "subtier", "office"
        self._result_type: str | None = None

    @property
    def _endpoint(self) -> str:
        """API endpoint for agency autocomplete.

        Raises:
            ValidationError: If the agency type is neither awarding nor funding,
                which the constructor and :meth:`agency_type` both prevent.
        """
        validate_agency_type(self._agency_type)
        return f"/autocomplete/{self._agency_type}_agency_office/"

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Build request payload."""
        if not self._search_text:
            raise ValidationError("search_text is required. Use name() or search_text() method.")

        return {
            "search_text": self._search_text,
            "limit": self._get_effective_page_size(),
        }

    def _execute_query(self, page: int) -> dict[str, Any]:
        """Execute the autocomplete query.

        This endpoint doesn't support pagination, so only return results on page 1.
        """
        # No pagination - return empty after first page
        if page > 1:
            return {"results": [], "page_metadata": {"hasNext": False}}

        payload = self._build_payload(1)
        response = self._client._make_request("POST", self._endpoint, json=payload)

        # The response has results as an object with three arrays
        # We need to flatten this into a single results array for QueryBuilder
        results_obj = response.get("results", {})
        flat_results = []

        # Add results based on filter type
        if self._result_type is None:
            # No filter - return all types
            # Add toptier agencies
            for agency in results_obj.get("toptier_agency", []):
                flat_results.append({"type": "toptier", "data": agency})

            # Add subtier agencies
            for subtier in results_obj.get("subtier_agency", []):
                flat_results.append({"type": "subtier", "data": subtier})

            # Add offices
            for office in results_obj.get("office", []):
                flat_results.append({"type": "office", "data": office})

        elif self._result_type == "toptier":
            for agency in results_obj.get("toptier_agency", []):
                flat_results.append({"type": "toptier", "data": agency})

        elif self._result_type == "subtier":
            for subtier in results_obj.get("subtier_agency", []):
                flat_results.append({"type": "subtier", "data": subtier})

        elif self._result_type == "office":
            for office in results_obj.get("office", []):
                flat_results.append({"type": "office", "data": office})

        # Return flattened structure for QueryBuilder
        return {
            "results": flat_results,
            "page_metadata": {"hasNext": False},
            "messages": response.get("messages", []),
        }

    def _transform_result(self, result: dict[str, Any]) -> _AgencySearchResult | None:
        """Transform result into Agency object based on type."""
        if not result:
            return None

        result_type = result.get("type")
        data = result.get("data", {})

        if result_type == "toptier":
            # Direct toptier agency result
            agency_data = {
                "code": data.get("code"),
                "toptier_code": data.get("code"),
                "name": data.get("name"),
                "abbreviation": data.get("abbreviation"),
            }
            return Agency(agency_data, self._client)

        elif result_type == "subtier":
            # Include subtier data
            return SubTierAgency(data, self._client)

        elif result_type == "office":
            return SubTierAgency(data, self._client)

        return None

    def _max_rows_per_page(self) -> int:
        """Return the row bound of one request: three buckets, each capped at page size.

        Returns:
            int: The most flattened rows the single autocomplete response may hold.
        """
        return 3 * self._page_size

    def _compute_raw_count(self) -> int:
        """Get total count of matching agencies/offices.

        Returns:
            Total number of matching results
        """
        if not self._search_text:
            raise ValidationError("search_text is required. Use name() or search_text() method.")

        # Execute query to get all results
        response = self._execute_query(1)
        results = response.get("results", [])

        count = len(results)

        return count

    def search_text(self, search_text: str) -> AgenciesSearch:
        """Set the search text for the query.

        Args:
            search_text: Text to search for in agency names

        Returns:
            New AgenciesSearch instance with search text set
        """
        clone = self._clone()
        clone._search_text = search_text
        return clone

    def name(self, name: str) -> AgenciesSearch:
        """Set the search text for agency or office names.

        Args:
            name: Text to search for in agency names

        Returns:
            New AgenciesSearch instance with search text set
        """
        return self.search_text(name)

    def agency_type(self, agency_type: Literal["funding", "awarding"]) -> AgenciesSearch:
        """Set the agency type for the autocomplete endpoint.

        Args:
            agency_type: "funding" or "awarding"

        Returns:
            New AgenciesSearch instance with agency type set

        Raises:
            ValidationError: If agency_type is invalid
        """
        clone = self._clone()
        clone._agency_type = validate_agency_type(agency_type)
        return clone

    def toptier(self) -> AgenciesSearch:
        """Filter to only return toptier agency matches.

        Returns:
            New AgenciesSearch instance filtered to toptier agencies
        """
        clone = self._clone()
        clone._result_type = "toptier"
        return clone

    def subtier(self) -> AgenciesSearch:
        """Filter to only return subtier agency matches.

        Returns:
            New AgenciesSearch instance filtered to subtier agencies
        """
        clone = self._clone()
        clone._result_type = "subtier"
        return clone

    def office(self) -> AgenciesSearch:
        """Filter to only return office matches.

        Returns:
            New AgenciesSearch instance filtered to offices
        """
        clone = self._clone()
        clone._result_type = "office"
        return clone

    def _clone(self) -> AgenciesSearch:
        """Create immutable copy for chaining."""
        clone = super()._clone()
        clone._agency_type = self._agency_type
        clone._search_text = self._search_text
        clone._result_type = self._result_type
        return clone
