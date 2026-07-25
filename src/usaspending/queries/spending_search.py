"""Spending search query builder for USASpending spending by category endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..models.district_spending import DistrictSpending
from ..models.download import SpendingLevel
from ..models.recipient_spending import RecipientSpending
from ..models.spending import Spending
from ..models.state_spending import StateSpending
from ..utils.validations import validate_non_empty_string
from .query_builder import SearchQueryBuilder

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)

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
        self._category: SpendingCategory | None = None
        self._spending_level: SpendingLevel = "transactions"
        self._subawards: bool = False
        self._recipient_id: str | None = None

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
        clone._recipient_id = self._recipient_id
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload from the filter objects."""

        if self._category is None:
            raise ValidationError(
                "Category must be set. Use .by_recipient(), .by_district(), or .by_state() method."
            )

        final_filters = self._aggregate_filters()

        # Sent as a bare string rather than through SimpleListFilter, because
        # this endpoint expects a scalar here and not an array.
        if self._recipient_id:
            final_filters["recipient_id"] = self._recipient_id

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

    def _compute_raw_count(self) -> int:
        """Count by walking pages.

        The spending-by-category endpoints report no total in page_metadata, so
        pages have to be walked and their results summed.

        Returns:
            The total number of matching spending records, up to any set limits.
        """
        return self._count_via_paging()

    # ==========================================================================
    # Category Selection Methods
    # ==========================================================================

    def by_recipient(self) -> SpendingSearch:
        """
        Configure search to return spending grouped by recipient.

        Groups spending data by recipient entity, returning aggregated
        amounts for each unique recipient that matches the filter criteria.

        Returns:
            SpendingSearch: A new instance configured for recipient spending.

        Note:
            Results are returned as RecipientSpending model instances
            with recipient name, UEI, and aggregated spending totals.

        Example:
            >>> # Find top recipients of DOD contracts
            >>> top_recipients = (
            ...     client.spending.search()
            ...     .by_recipient()
            ...     .agency("Department of Defense")
            ...     .contracts()
            ...     .fiscal_year(2024)
            ...     .limit(10)
            ... )
        """
        clone = self._clone()
        clone._category = "recipient"
        return clone

    def by_district(self) -> SpendingSearch:
        """
        Configure search to return spending grouped by congressional district.

        Groups spending data by the congressional district of the place of
        performance, returning aggregated amounts per district.

        Returns:
            SpendingSearch: A new instance configured for district spending.

        Note:
            Results are returned as DistrictSpending model instances
            with state, district number, and aggregated spending totals.

        Example:
            >>> # Find spending by congressional district for a state
            >>> ca_districts = (
            ...     client.spending.search()
            ...     .by_district()
            ...     .place_of_performance_locations({"state_code": "CA", "country_code": "USA"})
            ...     .contracts()
            ...     .fiscal_year(2024)
            ... )
        """
        clone = self._clone()
        clone._category = "district"
        return clone

    def by_state(self) -> SpendingSearch:
        """
        Configure search to return spending grouped by state/territory.

        Groups spending data by U.S. state or territory based on the
        place of performance, returning aggregated amounts per state.

        Returns:
            SpendingSearch: A new instance configured for state spending.

        Note:
            Results are returned as StateSpending model instances
            with state code, name, and aggregated spending totals.
            Includes all U.S. states and territories.

        Example:
            >>> # Find total grant spending by state
            >>> state_spending = client.spending.search().by_state().grants().fiscal_year(2024)
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

        Controls how spending amounts are aggregated when grouping by
        recipient, district, or state.

        Args:
            level: The aggregation level.

        Valid Spending Levels:
            "transactions" (default): Aggregate at the transaction level.
                Each transaction (modification) is counted separately.
                Provides the most detailed spending data.

            "awards": Aggregate at the award level.
                Groups by unique awards rather than transactions.
                Useful for counting distinct awards per category.

            "subawards": Aggregate subaward spending only.
                Includes only subaward amounts, not prime award data.
                Useful for analyzing pass-through spending.

        Returns:
            SpendingSearch: A new instance with the spending level configured.

        Example:
            >>> # Count distinct awards by recipient
            >>> award_counts = (
            ...     client.spending.search()
            ...     .by_recipient()
            ...     .spending_level("awards")
            ...     .contracts()
            ...     .fiscal_year(2024)
            ... )

            >>> # Analyze subaward spending by state
            >>> subaward_spending = (
            ...     client.spending.search().by_state().spending_level("subawards").grants()
            ... )

        Note:
            The spending level affects both the amounts returned and
            what counts are aggregated. Transaction-level provides
            the most granular data but may include multiple entries
            per award.
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

        The recipient ID is a unique identifier that includes the recipient hash
        and level suffix (e.g., "abc123-P" for parent, "abc123-C" for child).

        Note: This filter is not supported when using subawards mode.

        Args:
            recipient_id: Unique identifier for the recipient.

        Returns:
            A new SpendingSearch instance with the filter applied.

        Raises:
            ValidationError: If recipient_id is empty.
        """
        validated_id = validate_non_empty_string(recipient_id, "recipient_id")

        clone = self._clone()
        clone._recipient_id = validated_id
        return clone
