"""Funding search query builder for USASpending data."""

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

from ..exceptions import ValidationError
from ..models.funding import Funding
from .query_builder import QueryBuilder
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..client import USASpending

logger = USASpendingLogger.get_logger(__name__)


class FundingSearch(QueryBuilder["Funding"]):
    """
    Builds and executes a funding search query, allowing for retrieval
    of federal account funding data for a specific award.
    """

    # Map user-friendly sort field names to API field names
    SORT_FIELD_MAP = {
        "account_title": "account_title",
        "awarding_agency": "awarding_agency_name",
        "disaster_code": "disaster_emergency_fund_code",
        "federal_account": "federal_account",
        "funding_agency": "funding_agency_name",
        "gross_outlay": "gross_outlay_amount",
        "object_class": "object_class",
        "program_activity": "program_activity",
        "reporting_date": "reporting_fiscal_date",
        "fiscal_date": "reporting_fiscal_date",
        "obligated_amount": "transaction_obligated_amount",
        "obligation": "transaction_obligated_amount",
    }

    def __init__(self, client: "USASpending"):
        """
        Initializes the FundingSearch query builder.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)
        self._award_id: str = None
        self._sort_field: str = "reporting_fiscal_date"
        self._sort_order: str = "desc"

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/v2/awards/funding/"

    def _clone(self) -> FundingSearch:
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._award_id = self._award_id
        clone._sort_field = self._sort_field
        clone._sort_order = self._sort_order
        return clone

    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Constructs the final API request payload."""
        if not self._award_id:
            raise ValidationError(
                "An award_id is required. Use the .for_award() method."
            )

        payload = {
            "award_id": self._award_id,
            "limit": self._get_effective_page_size(),
            "page": page,
            "sort": self._sort_field,
            "order": self._sort_order,
        }

        return payload

    def _transform_result(self, result: Dict[str, Any]) -> Funding:
        """Transforms a single API result item into a Funding model."""
        return Funding(result)

    def count(self) -> int:
        """
        Counts the number of funding records for the award.

        Since the funding endpoint doesn't provide a count API,
        we need to iterate through all pages to get the count.
        """
        logger.debug(f"{self.__class__.__name__}.count() called")

        if not self._award_id:
            raise ValidationError(
                "An award_id is required. Use the .for_award() method."
            )

        # Iterate through all results to count
        count = 0
        for _ in self:
            count += 1

        logger.info(
            f"{self.__class__.__name__}.count() = {count} funding records "
            f"for award {self._award_id}"
        )
        return count

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def for_award(self, award_id: str) -> FundingSearch:
        """
        Filter funding records for a specific award.

        Args:
            award_id: The unique award identifier.

        Returns:
            A new FundingSearch instance with the award filter applied.
        """
        if not award_id:
            raise ValidationError("award_id cannot be empty")

        clone = self._clone()
        clone._award_id = str(award_id).strip()
        return clone

    def order_by(self, field: str, direction: str = "desc") -> FundingSearch:
        """
        Set the sort order for results.

        Args:
            field: The field to sort by. Can be a user-friendly name or API field name.
                   User-friendly names include:
                   - 'account_title', 'awarding_agency', 'disaster_code'
                   - 'federal_account', 'funding_agency', 'gross_outlay'
                   - 'object_class', 'program_activity', 'reporting_date'
                   - 'fiscal_date', 'obligated_amount', 'obligation'
            direction: Sort direction - 'asc' or 'desc' (default: 'desc')

        Returns:
            A new FundingSearch instance with the sort configuration applied.
        """
        # Validate direction
        if direction not in ["asc", "desc"]:
            raise ValidationError(
                f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'."
            )

        # Map user-friendly field names to API field names
        api_field = self.SORT_FIELD_MAP.get(field.lower(), field)

        # Validate that the field is supported by the API
        valid_api_fields = [
            "account_title",
            "awarding_agency_name",
            "disaster_emergency_fund_code",
            "federal_account",
            "funding_agency_name",
            "gross_outlay_amount",
            "object_class",
            "program_activity",
            "reporting_fiscal_date",
            "transaction_obligated_amount",
        ]

        if api_field not in valid_api_fields:
            raise ValidationError(
                f"Invalid sort field: {field}. "
                f"Valid fields are: {', '.join(self.SORT_FIELD_MAP.keys())}"
            )

        clone = self._clone()
        clone._sort_field = api_field
        clone._sort_order = direction
        return clone
