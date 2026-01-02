"""Sub-agency query implementation for retrieving agency sub-agencies with pagination."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..models.subtier_agency import SubTierAgency
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

    def __init__(self, client: USASpendingClient, toptier_code: str):
        """Initialize SubAgencyQuery.

        Args:
            client: USASpendingClient client instance
            toptier_code: The toptier code of the agency (3-4 digit string)
        """
        super().__init__(client)
        self._toptier_code = str(toptier_code).strip()
        self._validate_toptier_code()

        # Default filters
        self._fiscal_year: int | None = None
        self._agency_type: str = "awarding"
        self._award_type_codes: list[str] = []

        # Default sort (API defaults)
        self._order_by = "total_obligations"
        self._order_direction = "desc"

    def _validate_toptier_code(self) -> None:
        """Validate the toptier code format."""
        if not self._toptier_code:
            raise ValidationError("toptier_code is required")

        if not self._toptier_code.isdigit() or len(self._toptier_code) not in [3, 4]:
            raise ValidationError(
                f"Invalid toptier_code: {self._toptier_code}. Must be a 3-4 digit numeric string"
            )

    @property
    def _endpoint(self) -> str:
        """Endpoint for sub-agency retrieval."""
        return f"/agency/{self._toptier_code}/sub_agency/"

    def _clone(self) -> SubAgencyQuery:
        """Create an immutable copy of the query builder."""
        clone = SubAgencyQuery(self._client, self._toptier_code)
        clone._fiscal_year = self._fiscal_year
        clone._agency_type = self._agency_type
        clone._award_type_codes = self._award_type_codes.copy()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
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

    def _execute_query(self, page: int) -> dict[str, Any]:
        """Execute the query using GET instead of POST.

        The QueryBuilder base class assumes POST by default, but this endpoint
        uses GET with query parameters.
        """
        params = self._build_payload(page)

        from ..logging_config import log_query_execution

        log_query_execution(logger, "SubAgencyQuery", [], self._endpoint, page)
        logger.debug(f"Query params: {params}")

        response = self._client._make_request("GET", self._endpoint, params=params)

        if "page_metadata" in response:
            metadata = response["page_metadata"]
            logger.debug(
                f"Page metadata: page={metadata.get('page')}, "
                f"total={metadata.get('total')}, hasNext={metadata.get('hasNext')}"
            )

        return response

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

    def count(self) -> int:
        """Get total count of sub-agencies.

        This endpoint provides total count in page_metadata.
        """
        # Fetch first page to get metadata
        response = self._execute_query(1)
        return response.get("page_metadata", {}).get("total", 0)

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
        if type_val not in ("awarding", "funding"):
            raise ValidationError("agency_type must be 'awarding' or 'funding'")

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
        clone._award_type_codes = list(codes)
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

        if field not in valid_sorts:
            raise ValidationError(
                f"Invalid sort field: {field}. Valid fields are: {', '.join(sorted(valid_sorts))}"
            )

        if direction not in ("asc", "desc"):
            raise ValidationError("direction must be 'asc' or 'desc'")

        clone = self._clone()
        clone._order_by = field
        clone._order_direction = direction
        return clone
