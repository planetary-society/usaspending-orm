"""Spending search query builder for USASpending spending by category endpoints."""

from __future__ import annotations

import datetime
from typing import Any, Optional, Union, Literal

from ..client import USASpendingClient
from usaspending.exceptions import ValidationError
from usaspending.models.spending import Spending
from usaspending.models.recipient_spending import RecipientSpending
from usaspending.models.district_spending import DistrictSpending
from usaspending.models.state_spending import StateSpending
from usaspending.queries.query_builder import SearchQueryBuilder
from usaspending.logging_config import USASpendingLogger
from usaspending.queries.filters import (
    AwardAmountFilter,
    AwardDateType,
    KeywordsFilter,
    LocationFilter,
    LocationScopeFilter,
    SimpleListFilter,
    TieredCodeFilter,
    TimePeriodFilter,
    TreasuryAccountComponentsFilter,
    parse_award_amount,
    parse_award_date_type,
    parse_location_scope,
    parse_location_spec,
)

# Import award type codes from models
# These are defined by USASpending.gov and represent different categories of awards
from ..models.award_types import (
    CONTRACT_CODES,
    IDV_CODES,
    LOAN_CODES,
    GRANT_CODES,
    DIRECT_PAYMENT_CODES,
    OTHER_CODES,
)


logger = USASpendingLogger.get_logger(__name__)

SpendingLevel = Literal["transactions", "awards", "subawards"]
SpendingCategory = Literal["recipient", "district", "state"]


class SpendingSearch(SearchQueryBuilder["Spending"]):
    """
    Builds and executes spending by category search queries, allowing for complex
    filtering on spending data. This class follows a fluent interface pattern.

    Supports both recipient and district spending searches with configurable
    spending levels (transactions, awards, subawards).
    """

    def __init__(self, client: USASpendingClient):
        """
        Initializes the SpendingSearch query builder.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)
        self._category: Optional[SpendingCategory] = None
        self._spending_level: SpendingLevel = "transactions"
        self._subawards: bool = False

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        if self._category == "recipient":
            return "/search/spending_by_category/recipient/"
        elif self._category == "district":
            return "/search/spending_by_category/district/"
        elif self._category == "state":
            return "/search/spending_by_category/state_territory/"
        else:
            raise ValidationError(
                "Category must be set. Use .by_recipient(), .by_district(), or .by_state() method."
            )

    def _clone(self) -> SpendingSearch:
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._category = self._category
        clone._spending_level = self._spending_level
        clone._subawards = self._subawards
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload from the filter objects."""

        if self._category is None:
            raise ValidationError(
                "Category must be set. Use .by_recipient(), .by_district(), or .by_state() method."
            )

        final_filters = self._aggregate_filters()

        payload = {
            "filters": final_filters,
            "category": self._category,
            "limit": self._get_effective_page_size(),
            "page": page,
            "spending_level": self._spending_level,
        }

        # Add deprecated subawards field if needed
        if self._subawards:
            payload["subawards"] = self._subawards

        return payload

    def _transform_result(self, result: dict[str, Any]) -> Spending:
        """Transforms a single API result item into appropriate Spending model."""
        # Add category info to result data for model initialization
        result_with_category = {
            **result,
            "category": self._category,
            "spending_level": self._spending_level,
        }

        if self._category == "recipient":
            return RecipientSpending(result_with_category, self._client)
        elif self._category == "district":
            return DistrictSpending(result_with_category, self._client)
        elif self._category == "state":
            return StateSpending(result_with_category, self._client)
        else:
            return Spending(result_with_category, self._client)

    def count(self) -> int:
        """
        Get the total count of results by iterating through pages.

        Respects pagination constraints like limit() and max_pages() to match
        the behavior of iteration. The spending by category endpoints don't
        have a total count in page_metadata, so we fetch pages and count results.

        Returns:
            The total number of matching spending records, up to any set limits.
        """
        logger.debug(f"{self.__class__.__name__}.count() called")

        # Early return for zero or negative limits
        if self._total_limit is not None and self._total_limit <= 0:
            logger.info(
                f"{self.__class__.__name__}.count() = 0 (limit: {self._total_limit})"
            )
            return 0

        total_count = 0
        page = 1
        pages_fetched = 0

        while True:
            # Check if we've reached the max pages limit
            if self._max_pages and pages_fetched >= self._max_pages:
                logger.debug(f"Max pages limit ({self._max_pages}) reached")
                break

            response = self._execute_query(page)
            results = response.get("results", [])

            # Count items, but respect total_limit
            items_to_count = len(results)
            if self._total_limit is not None:
                remaining = self._total_limit - total_count
                items_to_count = min(items_to_count, remaining)

            total_count += items_to_count

            # Stop if we've reached our limit
            if self._total_limit is not None and total_count >= self._total_limit:
                logger.debug(f"Total limit of {self._total_limit} items reached")
                break

            # Check if there are more pages
            page_metadata = response.get("page_metadata", {})
            has_next = page_metadata.get("hasNext", False)

            if not has_next or not results:
                break

            page += 1
            pages_fetched += 1

        logger.info(f"{self.__class__.__name__}.count() = {total_count}")
        return total_count

    # ==========================================================================
    # Category Selection Methods
    # ==========================================================================

    def by_recipient(self) -> SpendingSearch:
        """
        Configure search to return spending grouped by recipient.

        Returns:
            A new SpendingSearch instance configured for recipient spending.
        """
        clone = self._clone()
        clone._category = "recipient"
        return clone

    def by_district(self) -> SpendingSearch:
        """
        Configure search to return spending grouped by congressional district.

        Returns:
            A new SpendingSearch instance configured for district spending.
        """
        clone = self._clone()
        clone._category = "district"
        return clone

    def by_state(self) -> SpendingSearch:
        """
        Configure search to return spending grouped by state/territory.

        Returns:
            A new SpendingSearch instance configured for state spending.
        """
        clone = self._clone()
        clone._category = "state"
        return clone

    # ==========================================================================
    # Spending Level Configuration
    # ==========================================================================

    def spending_level(self, level: SpendingLevel) -> SpendingSearch:
        """
        Set the spending level for data aggregation.

        Args:
            level: The spending level - "transactions", "awards", or "subawards"

        Returns:
            A new SpendingSearch instance with the spending level configured.
        """
        clone = self._clone()
        clone._spending_level = level
        return clone

    def subawards_only(self, enabled: bool = True) -> SpendingSearch:
        """
        Enable subawards search (deprecated parameter).

        Args:
            enabled: Whether to search subawards instead of prime awards

        Returns:
            A new SpendingSearch instance with subawards flag set.
        """
        clone = self._clone()
        clone._subawards = enabled
        return clone

    # ==========================================================================
    # Filter Methods (same as AwardsSearch)
    # ==========================================================================

    def recipient_id(self, recipient_id: str) -> SpendingSearch:
        """
        Filter by specific recipient ID.

        Args:
            recipient_id: Unique identifier for the recipient.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_id", values=[recipient_id])
        )
        return clone

