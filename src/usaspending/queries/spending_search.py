"""Spending search query builder for USASpending spending by category endpoints."""

from __future__ import annotations

import datetime
from typing import Any, Optional, Union, Literal

from usaspending.client import USASpending
from usaspending.exceptions import ValidationError
from usaspending.models.spending import Spending
from usaspending.models.recipient_spending import RecipientSpending
from usaspending.models.district_spending import DistrictSpending
from usaspending.queries.query_builder import QueryBuilder
from usaspending.logging_config import USASpendingLogger
from usaspending.queries.filters import (
    AgencyFilter,
    AgencyTier,
    AgencyType,
    AwardAmount,
    AwardAmountFilter,
    AwardDateType,
    KeywordsFilter,
    Location,
    LocationFilter,
    LocationScope,
    LocationScopeFilter,
    SimpleListFilter,
    TieredCodeFilter,
    TimePeriodFilter,
    TreasuryAccountComponentsFilter,
)

logger = USASpendingLogger.get_logger(__name__)

SpendingLevel = Literal["transactions", "awards", "subawards"]
SpendingCategory = Literal["recipient", "district"]


class SpendingSearch(QueryBuilder["Spending"]):
    """
    Builds and executes spending by category search queries, allowing for complex
    filtering on spending data. This class follows a fluent interface pattern.
    
    Supports both recipient and district spending searches with configurable
    spending levels (transactions, awards, subawards).
    """

    def __init__(self, client: USASpending):
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
            return "/api/v2/search/spending_by_category/recipient/"
        elif self._category == "district":
            return "/api/v2/search/spending_by_category/district/"
        else:
            raise ValidationError(
                "Category must be set. Use .by_recipient() or .by_district() method."
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
                "Category must be set. Use .by_recipient() or .by_district() method."
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
        result_with_category = {**result, "category": self._category, "spending_level": self._spending_level}
        
        if self._category == "recipient":
            return RecipientSpending(result_with_category, self._client)
        elif self._category == "district":
            return DistrictSpending(result_with_category, self._client)
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
            logger.info(f"{self.__class__.__name__}.count() = 0 (limit: {self._total_limit})")
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

    def with_keywords(self, *keywords: str) -> SpendingSearch:
        """
        Filter by a list of keywords.

        Args:
            *keywords: One or more keywords to search for.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(KeywordsFilter(values=list(keywords)))
        return clone

    def in_time_period(
        self,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        new_awards_only: bool = False,
        date_type: Optional[AwardDateType] = None,
    ) -> SpendingSearch:
        """
        Filter by a specific date range.

        Args:
            start_date: The start date of the period (datetime.date or string in "YYYY-MM-DD" format).
            end_date: The end date of the period (datetime.date or string in "YYYY-MM-DD" format).
            new_awards_only: If True, filters by awards with a start date within the given range.
            date_type: The type of date to filter on (e.g., action_date).

        Returns:
            A new SpendingSearch instance with the filter applied.
        
        Raises:
            ValidationError: If string dates are not in valid "YYYY-MM-DD" format.
        """
        
        # Parse string dates if needed
        if isinstance(start_date, str):
            try:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(f"Invalid start_date format: '{start_date}'. Expected 'YYYY-MM-DD'.")
        
        if isinstance(end_date, str):
            try:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(f"Invalid end_date format: '{end_date}'. Expected 'YYYY-MM-DD'.")
        
        # If convenience flag is set, use NEW_AWARDS_ONLY date type
        if new_awards_only:
            date_type = AwardDateType.NEW_AWARDS_ONLY
            
        clone = self._clone()
        clone._filter_objects.append(
            TimePeriodFilter(start_date=start_date, end_date=end_date, date_type=date_type)
        )
        return clone

    def for_fiscal_year(self, year: int, new_awards_only: bool = False, date_type: Optional[AwardDateType] = None) -> SpendingSearch:
        """
        Adds a time period filter for a single US government fiscal year
        (October 1 to September 30).

        Args:
            year: The fiscal year to filter by.
            new_awards_only: If True, filters by awards with a start date within the FY
            date_type: The type of date to filter on (e.g., action_date).

        Returns:
            A new SpendingSearch instance with the fiscal year filter applied.
        """
        start_date = datetime.date(year - 1, 10, 1)
        end_date = datetime.date(year, 9, 30)
        return self.in_time_period(start_date=start_date, end_date=end_date, new_awards_only=new_awards_only, date_type=date_type)

    def with_place_of_performance_scope(self, scope: LocationScope) -> SpendingSearch:
        """
        Filter spending by domestic or foreign place of performance.

        Args:
            scope: The scope, either DOMESTIC or FOREIGN.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            LocationScopeFilter(key="place_of_performance_scope", scope=scope)
        )
        return clone

    def with_place_of_performance_locations(self, *locations: Location) -> SpendingSearch:
        """
        Filter by one or more specific geographic places of performance.

        Args:
            *locations: One or more Location objects.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            LocationFilter(key="place_of_performance_locations", locations=list(locations))
        )
        return clone

    def for_agency(
        self,
        name: str,
        agency_type: AgencyType = AgencyType.AWARDING,
        tier: AgencyTier = AgencyTier.TOPTIER,
    ) -> SpendingSearch:
        """
        Filter by a specific awarding or funding agency.

        Args:
            name: The name of the agency.
            agency_type: The type of agency (AWARDING or FUNDING).
            tier: The agency tier (TOPTIER or SUBTIER).

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            AgencyFilter(agency_type=agency_type, tier=tier, name=name)
        )
        return clone

    def with_recipient_search_text(self, *search_terms: str) -> SpendingSearch:
        """
        Filter by recipient name, UEI, or DUNS.

        Args:
            *search_terms: Text to search for across recipient identifiers.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_search_text", values=list(search_terms))
        )
        return clone

    def with_recipient_id(self, recipient_id: str) -> SpendingSearch:
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

    def with_recipient_scope(self, scope: LocationScope) -> SpendingSearch:
        """
        Filter recipients by domestic or foreign scope.

        Args:
            scope: The scope, either DOMESTIC or FOREIGN.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(LocationScopeFilter(key="recipient_scope", scope=scope))
        return clone

    def with_recipient_locations(self, *locations: Location) -> SpendingSearch:
        """
        Filter by one or more specific recipient locations.

        Args:
            *locations: One or more Location objects.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            LocationFilter(key="recipient_locations", locations=list(locations))
        )
        return clone

    def with_recipient_types(self, *type_names: str) -> SpendingSearch:
        """
        Filter by one or more recipient or business types.

        Args:
            *type_names: The names of the recipient types (e.g., "small_business").

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_type_names", values=list(type_names))
        )
        return clone

    def with_award_types(self, *award_codes: str) -> SpendingSearch:
        """
        Filter by one or more award type codes.

        Args:
            *award_codes: A sequence of award type codes (e.g., "A", "B", "02").

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="award_type_codes", values=list(award_codes))
        )
        return clone

    def with_award_ids(self, *award_ids: str) -> SpendingSearch:
        """
        Filter by specific award IDs (FAIN, PIID, URI).

        Args:
            *award_ids: The exact award IDs to search for.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(SimpleListFilter(key="award_ids", values=list(award_ids)))
        return clone

    def with_award_amounts(self, *amounts: AwardAmount) -> SpendingSearch:
        """
        Filter by one or more award amount ranges.

        Args:
            *amounts: One or more AwardAmount objects defining the ranges.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(AwardAmountFilter(amounts=list(amounts)))
        return clone

    def with_cfda_numbers(self, *program_numbers: str) -> SpendingSearch:
        """
        Filter by one or more CFDA program numbers.

        Args:
            *program_numbers: The CFDA numbers to filter by.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="program_numbers", values=list(program_numbers))
        )
        return clone

    def with_naics_codes(
        self,
        require: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
    ) -> SpendingSearch:
        """
        Filter by NAICS codes, including or excluding specific codes.

        Args:
            require: A list of NAICS codes to require.
            exclude: A list of NAICS codes to exclude.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        # The API expects a list of lists, but for NAICS, each list contains one element.
        require_list = [[code] for code in require] if require else []
        exclude_list = [[code] for code in exclude] if exclude else []
        clone._filter_objects.append(
            TieredCodeFilter(key="naics_codes", require=require_list, exclude=exclude_list)
        )
        return clone

    def with_psc_codes(
        self,
        require: Optional[list[list[str]]] = None,
        exclude: Optional[list[list[str]]] = None,
    ) -> SpendingSearch:
        """
        Filter by Product and Service Codes (PSC), including or excluding codes.

        Args:
            require: A list of PSC code paths to require.
            exclude: A list of PSC code paths to exclude.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            TieredCodeFilter(
                key="psc_codes",
                require=require or [],
                exclude=exclude or [],
            )
        )
        return clone

    def with_contract_pricing_types(self, *type_codes: str) -> SpendingSearch:
        """
        Filter by one or more contract pricing type codes.

        Args:
            *type_codes: The contract pricing type codes.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="contract_pricing_type_codes", values=list(type_codes))
        )
        return clone

    def with_set_aside_types(self, *type_codes: str) -> SpendingSearch:
        """
        Filter by one or more set-aside type codes.

        Args:
            *type_codes: The set-aside type codes.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="set_aside_type_codes", values=list(type_codes))
        )
        return clone

    def with_extent_competed_types(self, *type_codes: str) -> SpendingSearch:
        """
        Filter by one or more extent competed type codes.

        Args:
            *type_codes: The extent competed type codes.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="extent_competed_type_codes", values=list(type_codes))
        )
        return clone

    def with_tas_codes(
        self,
        require: Optional[list[list[str]]] = None,
        exclude: Optional[list[list[str]]] = None,
    ) -> SpendingSearch:
        """
        Filter by Treasury Account Symbols (TAS), including or excluding codes.

        Args:
            require: A list of TAS code paths to require.
            exclude: A list of TAS code paths to exclude.

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            TieredCodeFilter(
                key="tas_codes",
                require=require or [],
                exclude=exclude or [],
            )
        )
        return clone

    def with_treasury_account_components(
        self, *components: dict[str, str]
    ) -> SpendingSearch:
        """
        Filter by specific components of a Treasury Account.

        Args:
            *components: Dictionaries representing TAS components (aid, main, etc.).

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            TreasuryAccountComponentsFilter(components=list(components))
        )
        return clone

    def with_def_codes(self, *def_codes: str) -> SpendingSearch:
        """
        Filter by one or more Disaster Emergency Fund (DEF) codes.

        Args:
            *def_codes: The DEF codes (e.g., "L", "M", "N").

        Returns:
            A new SpendingSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="def_codes", values=list(def_codes))
        )
        return clone