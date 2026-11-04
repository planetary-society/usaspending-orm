"""Prime-award search with stored subaward counts and totals."""

from __future__ import annotations

from typing import Any, ClassVar

from ..exceptions import ValidationError
from ..models.award_types import ALL_AWARD_CODES, AWARD_CATEGORIES, validate_award_type_codes
from ..models.subaward_summary import SubAwardSummary
from ..utils.validations import validate_non_empty_string
from .filters import SimpleStringFilter
from .mixins import SortableQuery
from .query_builder import SearchQueryBuilder


class SubAwardSummarySearch(SortableQuery, SearchQueryBuilder[SubAwardSummary]):
    """Filter prime awards and retrieve their stored subaward summaries.

    Recipient, location and date filters apply to prime awards. Returned totals
    include all their recorded subawards, and awards with no subawards remain in
    the results. Award types are optional and may span multiple categories.

    Counting uses the prime-award count endpoint, so it does not fetch pages or
    encounter the search result window. Iteration and deep indexing remain
    subject to the API's 50,000-row window and propagate server errors.
    """

    _sort_field: str = "award_generated_internal_id"

    SORT_FIELD_MAP: ClassVar[dict[str, str]] = {
        "award_id": "award_id",
        "award_generated_internal_id": "award_generated_internal_id",
        "subaward_count": "subaward_count",
        "subaward_obligation": "subaward_obligation",
        "subaward_to_award_ratio": "subaward_to_award_ratio",
    }

    @property
    def _endpoint(self) -> str:
        """Return the grouped subaward endpoint."""
        return "/search/spending_by_subaward_grouped/"

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Build a prime-award request, including filters even when empty."""
        return {
            "filters": self._aggregate_filters(),
            "limit": self._get_effective_page_size(),
            "page": page,
            **self._sort_payload(),
        }

    def _execute_query(self, page: int) -> dict[str, Any]:
        """Normalize this endpoint's incorrect continuation metadata."""
        response = super()._execute_query(page)
        results = response.get("results", [])
        limit = self._get_effective_page_size()
        # shortcut: full final pages need an empty request until upstream fixes hasNext.
        # The trim keeps pages disjoint if upstream adopts a limit+1 lookahead fix.
        return {
            **response,
            "results": results[:limit],
            "page_metadata": {
                **response.get("page_metadata", {}),
                "hasNext": len(results) >= limit,
            },
        }

    def _transform_result(self, result: dict[str, Any]) -> SubAwardSummary:
        """Wrap one summary without fetching the prime award."""
        return SubAwardSummary(result)

    def _compute_raw_count(self) -> int:
        """Count matching prime awards in one request, without paging.

        The count endpoint rejects an empty ``filters`` object, so an unfiltered
        query counts every award type instead. The buckets cover exactly those
        types, so the total is unchanged.
        """
        filters = self._aggregate_filters() or {"award_type_codes": sorted(ALL_AWARD_CODES)}
        return self._count_via_bucketed_endpoint(
            "/search/spending_by_award_count/",
            filters,
            (category.api_count_key for category in AWARD_CATEGORIES),
        )

    def award_id(self, award_id: str) -> SubAwardSummarySearch:
        """Filter by an exact generated prime-award identifier.

        Args:
            award_id: Generated unique award ID, such as ``"ASST_NON_..._080"``.
                Surrounding whitespace is stripped. This is not the display ID
                that ``SubAwardSummary.award_id`` reports.

        Returns:
            SubAwardSummarySearch: A new query with the filter applied.

        Raises:
            ValidationError: If ``award_id`` is not a nonempty string.
        """
        return self._with_filter(
            SimpleStringFilter(
                key="award_unique_id", value=validate_non_empty_string(award_id, "award_id")
            )
        )

    def award_type_codes(self, *award_codes: str) -> SubAwardSummarySearch:
        """Select valid award codes, allowing multiple award categories.

        Args:
            *award_codes: One or more award type codes, such as ``"A"`` or ``"02"``.

        Returns:
            SubAwardSummarySearch: A new query with the award type filter applied.

        Raises:
            ValidationError: If no code is supplied or any code is invalid.
        """
        if not award_codes:
            raise ValidationError("At least one award type code is required")
        validate_award_type_codes(award_codes)
        return super().award_type_codes(*award_codes)

    def program_activities(self, *activities: dict[str, str]) -> SubAwardSummarySearch:
        """Reject program activities, which grouped summaries silently ignore.

        Args:
            *activities: Ignored.

        Raises:
            ValidationError: Always.
        """
        raise ValidationError("program_activities is not supported for subaward summaries.")
