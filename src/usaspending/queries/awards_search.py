from __future__ import annotations

import datetime
from typing import Any, Optional, Union

from usaspending.client import USASpending
from usaspending.exceptions import ValidationError
from usaspending.models.award_factory import create_award
from usaspending.models import Award
from usaspending.models.contract import Contract
from usaspending.models.grant import Grant
from usaspending.models.idv import IDV
from usaspending.models.loan import Loan
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

# Import award type codes from config
# These are defined by USASpending.gov and represent different categories of awards

from ..config import (
    CONTRACT_CODES,
    IDV_CODES,
    LOAN_CODES,
    GRANT_CODES,
    DIRECT_PAYMENT_CODES,
    OTHER_CODES,
    AWARD_TYPE_GROUPS
)

class AwardsSearch(QueryBuilder["Award"]):
    """
    Builds and executes a spending_by_award search query, allowing for complex
    filtering on award data. This class follows a fluent interface pattern.
    """

    def __init__(self, client: USASpending):
        """
        Initializes the AwardsSearch query builder.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/v2/search/spending_by_award/"

    def _clone(self) -> AwardsSearch:
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._filter_objects = self._filter_objects.copy()
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload from the filter objects."""
        
        final_filters = self._aggregate_filters()

        # The 'award_type_codes' filter is required by the API.
        if "award_type_codes" not in final_filters:
            raise ValidationError(
                "A filter for 'award_type_codes' is required. "
                "Use the .with_award_types() method."
            )

        payload = {
            "filters": final_filters,
            "fields": self._get_fields(),
            "limit": self._get_effective_page_size(),
            "page": page,
        }
        return payload

    def _transform_result(self, result: dict[str, Any]) -> Award:
        """Transforms a single API result item into an Award model."""
        return create_award(result, self._client)

    def _get_award_type_codes(self) -> set[str]:
        """Extract award type codes from current filters."""
        for filter_obj in self._filter_objects:
            filter_dict = filter_obj.to_dict()
            if "award_type_codes" in filter_dict:
                return set(filter_dict["award_type_codes"])
        return set()

    def _validate_single_award_type_category(self, new_codes: set[str]) -> None:
        """
        Validate that only one category of award types is present.
        
        Args:
            new_codes: New award type codes being added
            
        Raises:
            ValidationError: If mixing award type categories
        """
        existing_codes = self._get_award_type_codes()
        all_codes = existing_codes | new_codes
        
        if not all_codes:
            return
        
        # Check how many categories are represented using the config mapping
        categories_present = 0
        category_names = []
        
        for category_name, codes in AWARD_TYPE_GROUPS.items():
            if all_codes & frozenset(codes.keys()):
                categories_present += 1
                category_names.append(category_name)
        
        if categories_present > 1:
            raise ValidationError(
                f"Cannot mix different award type categories: {', '.join(category_names)}. "
                "Use separate queries for each award type category."
            )

    def count(self) -> int:
        """
        Get the total count of results without fetching all items.
        
        Returns:
            The total number of matching awards for the selected award type category.
        """
        logger.debug(f"{self.__class__.__name__}.count() called")
        
        endpoint = '/v2/search/spending_by_award_count/'
        final_filters = self._aggregate_filters()
        
        # The 'award_type_codes' filter is required by the API.
        if "award_type_codes" not in final_filters:
            raise ValidationError(
                "A filter for 'award_type_codes' is required. "
                "Use the .with_award_types() method."
            )

        payload = {
            "filters": final_filters,
        }
        
        from ..logging_config import log_query_execution
        log_query_execution(logger, 'AwardsSearch.count', len(self._filter_objects), endpoint)
        
        # Send the request to the count endpoint
        response = self._client._make_request("POST", endpoint, json=payload)
        
        # Get the award type codes to determine which category to count
        award_type_codes = self._get_award_type_codes()
        
        # Determine the category based on award type codes
        category = self._get_award_type_category(award_type_codes)
        
        # Extract count from the appropriate category
        results = response.get("results", {})
        total = results.get(category, 0)
        
        logger.info(f"{self.__class__.__name__}.count() = {total} ({category})")
        return total
    
    def _get_award_type_category(self, award_type_codes: set[str]) -> str:
        """
        Determine the award type category based on the award type codes.
        
        Args:
            award_type_codes: Set of award type codes
            
        Returns:
            The category name as used in the count endpoint response
        """
        # Map config category names to API response names
        category_mapping = {
            "contracts": "contracts",
            "idvs": "idvs", 
            "loans": "loans",
            "grants": "grants",
            "direct_payments": "direct_payments",
            "other_assistance": "other"
        }
        
        for category_name, codes in AWARD_TYPE_GROUPS.items():
            if award_type_codes & frozenset(codes.keys()):
                return category_mapping[category_name]
        
        # Fail hard if no valid award type category is found
        raise ValidationError(
            "No valid award type category found. "
        )

    def _get_fields(self) -> list[str]:
        """
        Determines the list of fields to request based on award type filters.
        
        Returns different field sets depending on the award type codes:
        - Contracts (A, B, C, D): Include contract-specific fields
        - IDV (IDV_A, IDV_B, etc.): Include IDV-specific fields  
        - Loans (07, 08): Include loan-specific fields
        - Grants/Assistance (02, 03, 04, 05, 06, 09, 10, 11, -1): Include assistance fields
        """
        # Start with base fields from Award model
        base_fields = Award.SEARCH_FIELDS.copy()
        
        # Get award type codes from filters
        award_types = self._get_award_type_codes()
        additional_fields = []
        
        # Check each category and add appropriate fields based on model
        for category_name, codes in AWARD_TYPE_GROUPS.items():
            if award_types & frozenset(codes.keys()):
                if category_name == "contracts":
                    # Use Contract.SEARCH_FIELDS but exclude base fields
                    additional_fields.extend([f for f in Contract.SEARCH_FIELDS if f not in base_fields])
                elif category_name == "idvs":
                    # Use IDV.SEARCH_FIELDS but exclude base fields
                    additional_fields.extend([f for f in IDV.SEARCH_FIELDS if f not in base_fields])
                elif category_name == "loans":
                    # Use Loan.SEARCH_FIELDS but exclude base fields
                    additional_fields.extend([f for f in Loan.SEARCH_FIELDS if f not in base_fields])
                elif category_name in ["grants", "direct_payments", "other_assistance"]:
                    # Use Grant.SEARCH_FIELDS but exclude base fields
                    additional_fields.extend([f for f in Grant.SEARCH_FIELDS if f not in base_fields])
        
        # Combine base fields with additional fields, removing duplicates
        all_fields = base_fields + additional_fields
        return list(dict.fromkeys(all_fields))  # Remove duplicates while preserving order

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def with_keywords(self, *keywords: str) -> AwardsSearch:
        """
        Filter by a list of keywords.

        Args:
            *keywords: One or more keywords to search for.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
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
    ) -> AwardsSearch:
        """
        Filter by a specific date range.

        Args:
            start_date: The start date of the period (datetime.date or string in "YYYY-MM-DD" format).
            end_date: The end date of the period (datetime.date or string in "YYYY-MM-DD" format).
            new_awards_only: If True, filters by awards with a start date within the given range.
            date_type: The type of date to filter on (e.g., action_date).

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        
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
        # and override any provided date_type
        if new_awards_only:
            date_type = AwardDateType.NEW_AWARDS_ONLY
        clone = self._clone()
        clone._filter_objects.append(
            TimePeriodFilter(start_date=start_date, end_date=end_date, date_type=date_type)
        )
        return clone

    def for_fiscal_year(self, year: int, new_awards_only: bool = False, date_type: Optional[AwardDateType] = None) -> AwardsSearch:
        """
        Adds a time period filter for a single US government fiscal year
        (October 1 to September 30).

        Args:
            year: The fiscal year to filter by.
            new_awards_only: If True, filters by awards with a start date within the FY
            date_type: The type of date to filter on (e.g., action_date).

        Returns:
            A new `AwardsSearch` instance with the fiscal year filter applied.
        """
        start_date = datetime.date(year - 1, 10, 1)
        end_date = datetime.date(year, 9, 30)
        return self.in_time_period(start_date=start_date, end_date=end_date, new_awards_only=new_awards_only, date_type=date_type)

    def with_place_of_performance_scope(self, scope: LocationScope) -> AwardsSearch:
        """
        Filter awards by domestic or foreign place of performance.

        Args:
            scope: The scope, either DOMESTIC or FOREIGN.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            LocationScopeFilter(key="place_of_performance_scope", scope=scope)
        )
        return clone

    def with_place_of_performance_locations(self, *locations: Location) -> AwardsSearch:
        """
        Filter by one or more specific geographic places of performance.

        Args:
            *locations: One or more `Location` objects.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
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
    ) -> AwardsSearch:
        """
        Filter by a specific awarding or funding agency.

        Args:
            name: The name of the agency.
            agency_type: The type of agency (AWARDING or FUNDING).
            tier: The agency tier (TOPTIER or SUBTIER).

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            AgencyFilter(agency_type=agency_type, tier=tier, name=name)
        )
        return clone

    def with_recipient_search_text(self, *search_terms: str) -> AwardsSearch:
        """
        Filter by recipient name, UEI, or DUNS.

        Args:
            *search_terms: Text to search for across recipient identifiers.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_search_text", values=list(search_terms))
        )
        return clone

    def with_recipient_scope(self, scope: LocationScope) -> AwardsSearch:
        """
        Filter recipients by domestic or foreign scope.

        Args:
            scope: The scope, either DOMESTIC or FOREIGN.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(LocationScopeFilter(key="recipient_scope", scope=scope))
        return clone

    def with_recipient_locations(self, *locations: Location) -> AwardsSearch:
        """
        Filter by one or more specific recipient locations.

        Args:
            *locations: One or more `Location` objects.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            LocationFilter(key="recipient_locations", locations=list(locations))
        )
        return clone

    def with_recipient_types(self, *type_names: str) -> AwardsSearch:
        """
        Filter by one or more recipient or business types.

        Args:
            *type_names: The names of the recipient types (e.g., "small_business").

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_type_names", values=list(type_names))
        )
        return clone

    def with_award_types(self, *award_codes: str) -> AwardsSearch:
        """
        Filter by one or more award type codes. This filter is **required**.

        Args:
            *award_codes: A sequence of award type codes (e.g., "A", "B", "02").

        Returns:
            A new `AwardsSearch` instance with the filter applied.
            
        Raises:
            ValidationError: If mixing different award type categories.
        """
        new_codes = set(award_codes)
        self._validate_single_award_type_category(new_codes)
        
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="award_type_codes", values=list(award_codes))
        )
        return clone

    def contracts(self) -> AwardsSearch:
        """
        Filter to search for contract awards only (types A, B, C, D).
        
        Returns:
            A new `AwardsSearch` instance configured for contract awards.
        """
        return self.with_award_types(*CONTRACT_CODES)

    def idvs(self) -> AwardsSearch:
        """
        Filter to search for IDV awards only (types IDV_A, IDV_B, etc.).
        
        Returns:
            A new `AwardsSearch` instance configured for IDV awards.
        """
        return self.with_award_types(*IDV_CODES)

    def loans(self) -> AwardsSearch:
        """
        Filter to search for loan awards only (types 07, 08).
        
        Returns:
            A new `AwardsSearch` instance configured for loan awards.
        """
        return self.with_award_types(*LOAN_CODES)

    def grants(self) -> AwardsSearch:
        """
        Filter to search for grant and assistance awards only (types 02, 03, 04, 05).
        
        Returns:
            A new `AwardsSearch` instance configured for grant/assistance awards.
        """
        return self.with_award_types(*GRANT_CODES)

    def direct_payments(self) -> AwardsSearch:
        """
        Filter to search for direct payment awards only (types 06, 10).
        
        Returns:
            A new `AwardsSearch` instance configured for direct payment awards.
        """
        return self.with_award_types(*DIRECT_PAYMENT_CODES)

    def other(self) -> AwardsSearch:
        """
        Filter to search for other assistance awards only (types 09, 11, -1).
        
        Returns:
            A new `AwardsSearch` instance configured for other assistance awards.
        """
        return self.with_award_types(*OTHER_CODES)

    def with_award_ids(self, *award_ids: str) -> AwardsSearch:
        """
        Filter by specific award IDs (FAIN, PIID, URI).

        Args:
            *award_ids: The exact award IDs to search for.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(SimpleListFilter(key="award_ids", values=list(award_ids)))
        return clone

    def with_award_amounts(self, *amounts: AwardAmount) -> AwardsSearch:
        """
        Filter by one or more award amount ranges.

        Args:
            *amounts: One or more `AwardAmount` objects defining the ranges.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(AwardAmountFilter(amounts=list(amounts)))
        return clone

    def with_cfda_numbers(self, *program_numbers: str) -> AwardsSearch:
        """
        Filter by one or more CFDA program numbers.

        Args:
            *program_numbers: The CFDA numbers to filter by.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
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
    ) -> AwardsSearch:
        """
        Filter by NAICS codes, including or excluding specific codes.

        Args:
            require: A list of NAICS codes to require.
            exclude: A list of NAICS codes to exclude.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
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
    ) -> AwardsSearch:
        """
        Filter by Product and Service Codes (PSC), including or excluding codes.

        Args:
            require: A list of PSC code paths to require.
            exclude: A list of PSC code paths to exclude.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
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

    def with_contract_pricing_types(self, *type_codes: str) -> AwardsSearch:
        """
        Filter by one or more contract pricing type codes.

        Args:
            *type_codes: The contract pricing type codes.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="contract_pricing_type_codes", values=list(type_codes))
        )
        return clone

    def with_set_aside_types(self, *type_codes: str) -> AwardsSearch:
        """
        Filter by one or more set-aside type codes.

        Args:
            *type_codes: The set-aside type codes.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="set_aside_type_codes", values=list(type_codes))
        )
        return clone

    def with_extent_competed_types(self, *type_codes: str) -> AwardsSearch:
        """
        Filter by one or more extent competed type codes.

        Args:
            *type_codes: The extent competed type codes.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
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
    ) -> AwardsSearch:
        """
        Filter by Treasury Account Symbols (TAS), including or excluding codes.

        Args:
            require: A list of TAS code paths to require.
            exclude: A list of TAS code paths to exclude.

        Returns:
            A new `AwardsSearch` instance with the filter applied.
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
    ) -> AwardsSearch:
        """
        Filter by specific components of a Treasury Account.

        Args:
            *components: Dictionaries representing TAS components (aid, main, etc.).

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            TreasuryAccountComponentsFilter(components=list(components))
        )
        return clone

    def with_def_codes(self, *def_codes: str) -> AwardsSearch:
        """
        Filter by one or more Disaster Emergency Fund (DEF) codes.

        Args:
            *def_codes: The DEF codes (e.g., "L", "M", "N").

        Returns:
            A new `AwardsSearch` instance with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="def_codes", values=list(def_codes))
        )
        return clone