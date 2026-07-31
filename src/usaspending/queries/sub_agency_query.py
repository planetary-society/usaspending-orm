"""Sub-agency query implementation for retrieving agency sub-agencies with pagination."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..logging_config import USASpendingLogger
from ..models.subtier_agency import SubTierAgency
from ..utils.payloads import canonical_order
from ..utils.validations import (
    validate_agency_type,
    validate_sort_direction,
    validate_sort_field,
    validate_toptier_code,
)
from .filters import parse_fiscal_year
from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class SubAgencyQuery(QueryBuilder[SubTierAgency]):
    """Retrieve sub-agency data from the USAspending API.

    This query builder handles fetching sub-agency information including
    transaction counts and obligations filtered by fiscal year, agency type,
    and award type codes.
    """

    _http_method = "GET"

    def __init__(self, client: USASpendingClient, toptier_code: str):
        """Initialize SubAgencyQuery.

        Args:
            client: USASpendingClient client instance
            toptier_code: The toptier code of the agency (3-4 digit string)
        """
        super().__init__(client)
        self._toptier_code = validate_toptier_code(toptier_code)

        # Default filters
        self._fiscal_year: int | None = None
        self._agency_type: str = "awarding"
        self._award_type_codes: list[str] = []

        # Default sort (API defaults)
        self._order_by = "total_obligations"
        self._order_direction = "desc"

    @property
    def _endpoint(self) -> str:
        """Endpoint for sub-agency retrieval."""
        return f"/agency/{self._toptier_code}/sub_agency/"

    def _new_instance(self) -> SubAgencyQuery:
        """Reconstruct with the required toptier code."""
        return self.__class__(self._client, self._toptier_code)

    def _clone(self) -> SubAgencyQuery:
        """Create an immutable copy of the query builder."""
        clone = super()._clone()
        clone._fiscal_year = self._fiscal_year
        clone._agency_type = self._agency_type
        clone._award_type_codes = self._award_type_codes.copy()
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Build parameters for the API request."""
        params = {
            "agency_type": self._agency_type,
            "page": page,
            "limit": self._get_effective_page_size(),
            "sort": self._order_by,
            "order": self._order_direction,
        }

        if self._fiscal_year is not None:
            params["fiscal_year"] = self._fiscal_year

        if self._award_type_codes:
            params["award_type_codes"] = self._award_type_codes

        return params

    def _transform_result(self, result: dict[str, Any]) -> SubTierAgency | None:
        """Transform API result to SubTierAgency model.

        Args:
            result: Raw API result dictionary.

        Returns:
            SubTierAgency model, or None if result is not a valid dict.
        """
        if not isinstance(result, dict):
            return None
        return SubTierAgency(result, self._client)

    def _compute_raw_count(self) -> int:
        """Get total count of sub-agencies.

        This endpoint provides total count in page_metadata.
        """
        return self._count_via_page_metadata("total")

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def fiscal_year(self, year: int) -> SubAgencyQuery:
        """Filter by fiscal year.

        Args:
            year: Fiscal year (e.g., 2024).

        Returns:
            A new SubAgencyQuery instance with the filter applied.
        """
        year = parse_fiscal_year(year)
        clone = self._clone()
        clone._fiscal_year = year
        return clone

    def agency_type(self, type_val: str) -> SubAgencyQuery:
        """Filter by agency type ('awarding' or 'funding').

        Args:
            type_val: "awarding" or "funding".

        Returns:
            A new SubAgencyQuery instance with the filter applied.
        """
        validate_agency_type(type_val)

        clone = self._clone()
        clone._agency_type = type_val
        return clone

    def award_type_codes(self, *codes: str) -> SubAgencyQuery:
        """Filter by award type codes.

        Args:
            *codes: List of award type codes.

        Returns:
            A new SubAgencyQuery instance with the filter applied.
        """
        clone = self._clone()
        # Canonically ordered for the same reason the filter objects are: these
        # codes routinely arrive as a frozenset, and this builder puts them
        # straight into the request without going through a filter.
        clone._award_type_codes = canonical_order(codes)
        return clone

    def order_by(self, field: str, direction: str = "desc") -> SubAgencyQuery:
        """Set sort order.

        Args:
            field: Field to sort by ("name", "total_obligations",
                  "transaction_count", "new_award_count").
            direction: "asc" or "desc".

        Returns:
            A new SubAgencyQuery instance with ordering applied.
        """
        valid_sorts = {"name", "total_obligations", "transaction_count", "new_award_count"}

        validate_sort_field(field, valid_sorts)

        clone = self._clone()
        clone._order_by = field
        clone._order_direction = validate_sort_direction(direction)
        return clone
