"""Funding search query builder for USASpending data."""

from __future__ import annotations

from typing import Any, ClassVar

from ..logging_config import USASpendingLogger
from ..models.funding import Funding
from .mixins import AwardScopedQuery, SortableQuery
from .query_builder import QueryBuilder

logger = USASpendingLogger.get_logger(__name__)


class FundingSearch(AwardScopedQuery, SortableQuery, QueryBuilder["Funding"]):
    """
    Builds and executes a funding search query, allowing for retrieval
    of federal account funding data for a specific award.
    """

    _sort_field: str = "reporting_fiscal_date"

    # Map user-friendly sort field names to API field names
    SORT_FIELD_MAP: ClassVar[dict[str, str]] = {
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

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/awards/funding/"

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload."""
        return {
            "award_id": self._require_award_id(),
            "limit": self._get_effective_page_size(),
            "page": page,
            **self._sort_payload(),
        }

    def _transform_result(self, result: dict[str, Any]) -> Funding:
        """Transforms a single API result item into a Funding model."""
        return Funding(result, client=self._client)

    def _compute_raw_count(self) -> int:
        """
        Counts the number of funding records for the award.

        Since the funding endpoint doesn't provide a count API,
        pages have to be walked and their results summed.
        """
        self._require_award_id()

        return self._count_via_paging()
