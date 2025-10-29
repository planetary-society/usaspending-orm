"""
AwardsSearch Query Builder for USAspending.gov API.

This module provides a fluent interface for querying award data from the USAspending.gov API.
It wraps the following API endpoints:

1. **Primary Search Endpoint**: `/api/v2/search/spending_by_award/`
   - Returns detailed award information based on complex filter criteria
   - Supports pagination, sorting, and field selection
   - Full documentation: https://github.com/fedspendingtransparency/usaspending-api/blob/102960f58c87e0a7b6490dc0317055cbfcaa9b7b/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md

2. **Count Endpoint**: `/api/v2/search/spending_by_award_count/`
   - Returns counts of awards grouped by type
   - Used internally by the count() method
   - Full documentation: https://github.com/fedspendingtransparency/usaspending-api/blob/102960f58c87e0a7b6490dc0317055cbfcaa9b7b/usaspending_api/api_contracts/contracts/v2/search/spending_by_award_count.md

## Overview

The AwardsSearch class provides a chainable query builder pattern for constructing complex
award searches using the USAspending API. All filter methods return a new instance,
allowing for immutable query construction.

## Award Types

USAspending.gov categorizes awards into several types, each with specific codes:

Due to limitations in the API, you cannot mix different award type categories. Any query
must include one of the following award types:

- **Contracts**: Types A, B, C, D - Procurement contracts
- **IDVs**: Types IDV_A through IDV_E - Indefinite Delivery Vehicles
- **Grants**: Types 02, 03, 04, 05 - Grant awards
- **Loans**: Types 07, 08 - Loan awards
- **Direct Payments**: Types 06, 10 - Direct payment awards
- **Other**: Types 09, 11, -1 - Other assistance awards

## Basic Usage Examples

### Example 1: Search for Recent Contracts

```python
from usaspending import USASpendingClient

client = USASpendingClient()

# Find contracts from FY2024 for small businesses
contracts = (
    client.awards.search()
    .contracts()  # Filter to contract types only
    .for_fiscal_year(2024)
    .with_recipient_types("small_business")
    .order_by("Last Modified Date", "desc")
    .limit(100)
)

for contract in contracts:
    print(f"{contract.recipient.name}: ${contract.award_amount:,.2f} ${contract.period_of_performance.last_modified_date}")
```

### Example 2: Search Grants by Agency

```python
# Find all grants from the Department of Education in 2023
grants = (
    client.awards.search()
    .grants()  # Filter to grant types
    .for_agency("Department of Education")
    .for_fiscal_year(2023)
)

print(f"Total grants: {grants.count()}")

# Iterate through results (automatically handles pagination)
for grant in grants:
    print(f"{grant.award_id}: {grant.description}")
```

### Example 3: Complex Multi-Filter Search

```python
# Search for NASA-related contracts in California since 2020
from datetime import date

results = (
    client.awards.search()
    .contracts()
    .for_agency("National Aeronautics and Space Administration")
    .in_time_period("2020-03-01", date.today().isoformat())
    .with_place_of_performance_locations(
        {"state_code": "CA", "country_code": "USA"}
    )
    .with_award_amounts(
        {"lower_bound": 100000, "upper_bound": 10000000}
    )
    .order_by("Last Modified Date", "desc")
)

for award in results.page(1):
    print(f"{award.award_id}: {award.recipient.name}")
```


## Important Notes

The same filtering limitations and requirements that apply to the USAspending.gov API also apply here:

1. **Required Award Type Filter**: Every query must include a filter for `award_type_codes`.
    Or use the conveinience methods `.contracts()`, `.grants()`, `.loans()`, `.idvs()`, `.direct_payments()`, or `.other_assistance()`
    to set the award type category.

2. **Single Category Restriction**: You cannot mix different award type categories
   (e.g., contracts and grants) in a single query. Use separate queries for each.

3. **Automatic Pagination**: Iterating over results automatically handles pagination.
   Use `limit()` to control returned result size.

"""

from __future__ import annotations

import datetime
from typing import Any, Optional, Union

from ..client import USASpendingClient
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
    AwardAmountFilter,
    AwardDateType,
    KeywordsFilter,
    LocationFilter,
    LocationScopeFilter,
    SimpleListFilter,
    TieredCodeFilter,
    TimePeriodFilter,
    TreasuryAccountComponentsFilter,
    parse_agency_tier,
    parse_agency_type,
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
    AWARD_TYPE_GROUPS,
)

logger = USASpendingLogger.get_logger(__name__)


class AwardsSearch(QueryBuilder["Award"]):
    """
    Builds and executes spending_by_award search queries with complex filtering.

    This class provides a fluent interface for constructing queries against the
    USAspending.gov API's spending_by_award endpoint. All methods return new
    instances, ensuring immutability.

    Attributes:
        _client: The USASpending client instance for API communication.
        _filter_objects: List of filter objects to apply to the query.
        _order_by: Field to sort results by.
        _order_direction: Sort direction ('asc' or 'desc').

    See module docstring for detailed usage examples.
    """

    def __init__(self, client: USASpendingClient):
        """
        Initialize the AwardsSearch query builder.

        Args:
            client: The USASpending client instance for API communication.

        Example:
            >>> client = USASpendingClient()
            >>> search = AwardsSearch(client)
        """
        super().__init__(client)

    @property
    def _endpoint(self) -> str:
        """
        Return the API endpoint for award searches.

        Returns:
            str: The endpoint path '/search/spending_by_award/'.
        """
        return "/search/spending_by_award/"

    def _clone(self) -> AwardsSearch:
        """
        Create an immutable copy of the query builder.

        This method ensures that all filter operations return new instances,
        maintaining immutability of the query builder.

        Returns:
            AwardsSearch: A new instance with copied filter objects.
        """
        clone = super()._clone()
        clone._filter_objects = self._filter_objects.copy()
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """
        Construct the API request payload from filter objects.

        Args:
            page: The page number to retrieve (1-indexed).

        Returns:
            dict[str, Any]: The complete payload for the API request.

        Raises:
            ValidationError: If required 'award_type_codes' filter is missing.
        """

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

        # Add sorting parameters if specified
        if self._order_by:
            payload["sort"] = self._order_by
            payload["order"] = self._order_direction

        return payload

    def _transform_result(self, result: dict[str, Any]) -> Award:
        """
        Transform a single API result into an Award model instance.

        This method determines the appropriate Award subclass based on the
        award type codes in the current filters.

        Args:
            result: A single result dictionary from the API response.

        Returns:
            Award: An appropriate Award subclass instance (Contract, Grant, etc.).
        """
        # Get award type codes from current filters
        award_type_codes = self._get_award_type_codes()

        # If we're filtering for a single award type category, add it to the result
        # This ensures the correct Award subclass is created even when the API
        # response doesn't include explicit type information
        if award_type_codes:
            if award_type_codes.issubset(CONTRACT_CODES):
                result["category"] = "contract"
            elif award_type_codes.issubset(IDV_CODES):
                result["category"] = "idv"
            elif award_type_codes.issubset(GRANT_CODES):
                result["category"] = "grant"
            elif award_type_codes.issubset(LOAN_CODES):
                result["category"] = "loan"

        return create_award(result, self._client)

    def _get_award_type_codes(self) -> set[str]:
        """
        Extract award type codes from current filters.

        Returns:
            set[str]: Set of award type codes from filters, or empty set if none.
        """
        for filter_obj in self._filter_objects:
            filter_dict = filter_obj.to_dict()
            if "award_type_codes" in filter_dict:
                return set(filter_dict["award_type_codes"])
        return set()

    def _validate_single_award_type_category(self, new_codes: set[str]) -> None:
        """
        Validate that only one category of award types is present.

        USAspending API does not support mixing different award type categories
        (e.g., contracts and grants) in a single query.

        Args:
            new_codes: New award type codes being added to the query.

        Raises:
            ValidationError: If the new codes would mix different award type
                categories with existing codes.

        Example:
            >>> # This would raise ValidationError:
            >>> search.with_award_types("A", "02")  # Contract + Grant
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

        This method uses the /search/spending_by_award_count/ endpoint to
        efficiently retrieve counts without downloading full result data.

        Returns:
            int: The total number of matching awards for the selected award type category.

        Raises:
            ValidationError: If award_type_codes filter is not set.

        Example:
            >>> contracts = client.awards.search().contracts().for_fiscal_year(2024)
            >>> total = contracts.count()
            >>> print(f"Found {total} contracts in FY2024")
        """
        logger.debug(f"{self.__class__.__name__}.count() called")

        # Aggregate filters to prepare for the count request
        final_filters = self._aggregate_filters()

        # The 'award_type_codes' filter is required by the API.
        if "award_type_codes" not in final_filters:
            raise ValidationError(
                "A filter for 'award_type_codes' is required. "
                "Use the .with_award_types() method."
            )

        # Make the API call to count awards by type
        results = self.count_awards_by_type()

        # Get the award type codes to determine which category to count
        award_type_codes = self._get_award_type_codes()

        # Determine the category based on award type codes
        category = self._get_award_type_category(award_type_codes)

        # Extract the count for the specific category
        total = results.get(category, 0)

        logger.info(f"{self.__class__.__name__}.count() = {total} ({category})")
        return total

    def count_awards_by_type(self) -> dict[str, int]:
        """
        Get counts of awards grouped by type category.

        This method calls the /search/spending_by_award_count/ endpoint to get
        counts for all award type categories matching the current filters.

        Returns:
            dict[str, int]: Dictionary mapping award type categories
                ('contracts', 'grants', 'loans', etc.) to their counts.

        Example:
            >>> search = client.awards.search().for_fiscal_year(2024)
            >>> counts = search.count_awards_by_type()
            >>> print(counts)  # {'contracts': 1234, 'grants': 567, ...}
        """
        endpoint = "/search/spending_by_award_count/"
        final_filters = self._aggregate_filters()

        payload = {
            "filters": final_filters,
        }

        from ..logging_config import log_query_execution

        log_query_execution(
            logger,
            "AwardsSearch._count_awards_by_type",
            self._filter_objects,
            endpoint,
        )

        # Send the request to the count endpoint
        response = self._client._make_request("POST", endpoint, json=payload)
        results = response.get("results", {})

        return results

    def _get_award_type_category(self, award_type_codes: set[str]) -> str:
        """
        Determine the award type category from award type codes.

        Args:
            award_type_codes: Set of award type codes (e.g., {'A', 'B', 'C'}).

        Returns:
            str: The category name as used in the count endpoint response
                (e.g., 'contracts', 'grants', 'loans').

        Raises:
            ValidationError: If no valid award type category is found.
        """
        # Map config category names to API response names
        category_mapping = {
            "contracts": "contracts",
            "idvs": "idvs",
            "loans": "loans",
            "grants": "grants",
            "direct_payments": "direct_payments",
            "other_assistance": "other",
        }

        for category_name, codes in AWARD_TYPE_GROUPS.items():
            if award_type_codes & frozenset(codes.keys()):
                return category_mapping[category_name]

        # Fail hard if no valid award type category is found
        raise ValidationError("No valid award type category found. ")

    def _get_fields(self) -> list[str]:
        """
        Determine the list of fields to request based on award type filters.

        The API returns different fields depending on the award type:
        - Contracts (A, B, C, D): Include contract-specific fields like PSC, NAICS
        - IDVs (IDV_*): Include IDV-specific fields like Last Date to Order
        - Loans (07, 08): Include loan-specific fields like Loan Value, Subsidy Cost
        - Grants/Assistance: Include assistance fields like CFDA Number, SAI Number

        Returns:
            list[str]: List of field names to request from the API, combining
                base Award fields with type-specific fields.
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
                    additional_fields.extend(
                        [f for f in Contract.SEARCH_FIELDS if f not in base_fields]
                    )
                elif category_name == "idvs":
                    # Use IDV.SEARCH_FIELDS but exclude base fields
                    additional_fields.extend(
                        [f for f in IDV.SEARCH_FIELDS if f not in base_fields]
                    )
                elif category_name == "loans":
                    # Use Loan.SEARCH_FIELDS but exclude base fields
                    additional_fields.extend(
                        [f for f in Loan.SEARCH_FIELDS if f not in base_fields]
                    )
                elif category_name in ["grants", "direct_payments", "other_assistance"]:
                    # Use Grant.SEARCH_FIELDS but exclude base fields
                    additional_fields.extend(
                        [f for f in Grant.SEARCH_FIELDS if f not in base_fields]
                    )

        # Combine base fields with additional fields, removing duplicates
        all_fields = base_fields + additional_fields
        return list(
            dict.fromkeys(all_fields)
        )  # Remove duplicates while preserving order

    def order_by(self, field: str, direction: str = "desc") -> AwardsSearch:
        """
        Set the sort field and direction for query results.

        Args:
            field: The field name to sort by. Must be a valid field from the
                current award type's available fields.
            direction: The sort direction, either "asc" or "desc".
                Defaults to "desc".

        Returns:
            AwardsSearch: A new instance with the ordering applied.

        Raises:
            ValidationError: If the field is not valid for the current
                award type configuration.

        Example:
            >>> # Sort contracts by award amount, highest first
            >>> results = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .order_by("Award Amount", "desc")
            ... )

            >>> # Sort grants by date, newest first
            >>> grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .order_by("Start Date", "desc")
            ... )
        """
        # Get the valid fields for the current award type configuration
        valid_fields = self._get_fields()

        # Validate that the field is in the list of valid fields
        if field not in valid_fields:
            # Build a helpful error message
            award_types = self._get_award_type_codes()
            if award_types:
                # Determine which category we're searching
                category_names = []
                for category_name, codes in AWARD_TYPE_GROUPS.items():
                    if award_types & frozenset(codes.keys()):
                        category_names.append(category_name)
                category_str = (
                    ", ".join(category_names)
                    if category_names
                    else "selected award types"
                )
            else:
                category_str = "all award types (no type filter applied)"

            raise ValidationError(
                f"Invalid sort field '{field}' for {category_str}. "
                f"Valid fields are: {', '.join(sorted(valid_fields))}"
            )

        # Call the parent class order_by method
        return super().order_by(field, direction)

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def with_keywords(self, *keywords: str) -> AwardsSearch:
        """
        Filter awards by keyword search.

        Keywords are searched across multiple fields including award descriptions,
        recipient names, and other text fields.

        Args:
            *keywords: One or more keywords to search for. Multiple keywords
            are combined with OR logic.

        Returns:
            AwardsSearch: A new instance with the keyword filter applied.

        Example:
            >>> # Search for outer planet-related contracts
            >>> results = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_keywords("Jupiter", "Saturn", "Neptune", "Uranus")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(KeywordsFilter(values=list(keywords)))
        return clone

    def in_time_period(
        self,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        new_awards_only: bool = False,
        date_type: Optional[str] = None,
    ) -> AwardsSearch:
        """
        Filter awards by a specific date range.

        Args:
            start_date: The start date of the period. Can be a datetime.date
                object or string in "YYYY-MM-DD" format.
            end_date: The end date of the period. Can be a datetime.date
                object or string in "YYYY-MM-DD" format.
            new_awards_only: If True, only returns awards that started within
                the given date range. Defaults to False.
            date_type: The type of date to filter on. Can be a string:
                "action_date", "date_signed", "last_modified_date", or
                "new_awards_only". If not specified, uses default date type.
                Case-insensitive.

        Returns:
            AwardsSearch: A new instance with the time period filter applied.

        Raises:
            ValidationError: If string dates are not in valid "YYYY-MM-DD" format.

        Example:
            >>> # Find all contracts from 2023
            >>> contracts_2023 = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .in_time_period("2023-01-01", "2023-12-31")
            ... )

            >>> # Find only NEW grants started in Q1 2024
            >>> new_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .in_time_period("2024-01-01", "2024-03-31", new_awards_only=True)
            ... )
        """

        # Parse string dates if needed
        if isinstance(start_date, str):
            try:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(
                    f"Invalid start_date format: '{start_date}'. Expected 'YYYY-MM-DD'."
                )

        if isinstance(end_date, str):
            try:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(
                    f"Invalid end_date format: '{end_date}'. Expected 'YYYY-MM-DD'."
                )

        # Convert string date_type to enum if needed
        date_type_enum = None
        if date_type is not None:
            date_type_enum = parse_award_date_type(date_type)

        # If convenience flag is set, use NEW_AWARDS_ONLY date type
        # and override any provided date_type
        if new_awards_only:
            date_type_enum = AwardDateType.NEW_AWARDS_ONLY

        clone = self._clone()
        clone._filter_objects.append(
            TimePeriodFilter(
                start_date=start_date, end_date=end_date, date_type=date_type_enum
            )
        )
        return clone

    def for_fiscal_year(
        self,
        year: int,
        new_awards_only: bool = False,
        date_type: Optional[str] = None,
    ) -> AwardsSearch:
        """
        Filter awards by US government fiscal year.

        A fiscal year runs from October 1 to September 30. For example,
        FY2024 runs from October 1, 2023 to September 30, 2024.

        Args:
            year: The fiscal year to filter by (e.g., 2024 for FY2024).
            new_awards_only: If True, only returns awards that started within
                the fiscal year. Defaults to False.
            date_type: The type of date to filter on. Can be a string:
                "action_date", "date_signed", "last_modified_date", or
                "new_awards_only". If not specified, uses default date type.
                Case-insensitive.

        Returns:
            AwardsSearch: A new instance with the fiscal year filter applied.

        Example:
            >>> # Get all contracts from FY2024
            >>> fy2024_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .for_fiscal_year(2024)
            ... )

            >>> # Get only NEW grants started in FY2023
            >>> new_fy2023_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .for_fiscal_year(2023, new_awards_only=True)
            ... )
        """
        start_date = datetime.date(year - 1, 10, 1)
        end_date = datetime.date(year, 9, 30)
        return self.in_time_period(
            start_date=start_date,
            end_date=end_date,
            new_awards_only=new_awards_only,
            date_type=date_type,
        )

    def with_place_of_performance_scope(self, scope: str) -> AwardsSearch:
        """
        Filter awards by domestic or foreign place of performance.

        Args:
            scope: Either "domestic" or "foreign" (case-insensitive).

        Returns:
            AwardsSearch: A new instance with the location scope filter applied.

        Raises:
            ValidationError: If scope is not "domestic" or "foreign".

        Example:
            >>> # Find foreign aid grants
            >>> foreign_aid = (
            ...     client.awards.search()
            ...     .grants()
            ...     .with_place_of_performance_scope("foreign")
            ... )

            >>> # Find domestic infrastructure contracts
            >>> domestic_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_place_of_performance_scope("domestic")
            ... )
        """
        location_scope = parse_location_scope(scope)

        clone = self._clone()
        clone._filter_objects.append(
            LocationScopeFilter(key="place_of_performance_scope", scope=location_scope)
        )
        return clone

    def with_place_of_performance_locations(
        self, *locations: dict[str, str]
    ) -> AwardsSearch:
        """
        Filter awards by specific geographic places of performance.

        Args:
            *locations: One or more location specifications as dictionaries.
                Each dictionary can contain:
                - country_code: Country code (required, e.g., "USA")
                - state_code: State code (optional, e.g., "TX", "CA")
                - county_code: County code (optional)
                - city_name: City name (optional)
                - district_original: Current congressional district (optional, e.g., "IA-03")
                - district_current: Congressional district when awarded (optional, e.g., "WA-01")
                - zip_code: ZIP code (optional)

        Returns:
            AwardsSearch: A new instance with the location filter applied.

        Example:
            >>> # Find contracts performed in specific Texas cities
            >>> texas_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_place_of_performance_locations(
            ...         {"state_code": "TX", "city_name": "Austin", "country_code": "USA"},
            ...         {"state_code": "TX", "city_name": "Houston", "country_code": "USA"},
            ...         {"state_code": "TX", "city_name": "Dallas", "country_code": "USA"},
            ...     )
            ... )

            >>> # Find awards in a specific ZIP code
            >>> local_awards = (
            ...     client.awards.search()
            ...     .with_award_types("A", "B")
            ...     .with_place_of_performance_locations(
            ...         {"zip_code": "20001", "country_code": "USA"}
            ...     )
            ... )
        """
        # Convert dicts to LocationSpec objects internally
        location_specs = [parse_location_spec(loc) for loc in locations]

        clone = self._clone()
        clone._filter_objects.append(
            LocationFilter(
                key="place_of_performance_locations", locations=location_specs
            )
        )
        return clone

    def for_agency(
        self,
        name: str,
        agency_type: str = "awarding",
        tier: str = "toptier",
    ) -> AwardsSearch:
        """
        Filter awards by a specific awarding or funding agency.

        Args:
            name: The name of the agency (e.g., "Department of Defense").
            agency_type: Whether to filter by "awarding" agency (who manages
                the award) or "funding" agency (who provides the money).
                Defaults to "awarding". Case-insensitive.
            tier: Whether to filter by "toptier" agency (main department) or
                "subtier" agency (sub-agency or office). Defaults to "toptier".
                Case-insensitive.

        Returns:
            AwardsSearch: A new instance with the agency filter applied.

        Raises:
            ValidationError: If agency_type is not "awarding" or "funding",
                or if tier is not "toptier" or "subtier".

        Example:
            >>> # Find all DOD contracts
            >>> dod_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .for_agency("Department of Defense")
            ... )

            >>> # Find awards funded by NASA (not necessarily awarded by them)
            >>> nasa_funded = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .for_agency(
            ...         "National Aeronautics and Space Administration",
            ...         agency_type="funding"
            ...     )
            ... )

            >>> # Find sub-agency awards
            >>> sub_agency_awards = (
            ...     client.awards.search()
            ...     .grants()
            ...     .for_agency(
            ...         "National Institute of Health",
            ...         tier="subtier"
            ...     )
            ... )
        """
        # Convert string inputs to enums
        agency_type_enum = parse_agency_type(agency_type)
        tier_enum = parse_agency_tier(tier)

        clone = self._clone()
        clone._filter_objects.append(
            AgencyFilter(agency_type=agency_type_enum, tier=tier_enum, name=name)
        )
        return clone

    def with_recipient_search_text(self, *search_terms: str) -> AwardsSearch:
        """
        Search for awards by recipient name, UEI, or DUNS.

        This performs a text search across recipient identifiers and names.

        Args:
            *search_terms: Text to search for across recipient name,
                UEI (Unique Entity Identifier), and DUNS number fields.

        Returns:
            AwardsSearch: A new instance with the recipient search filter applied.

        Example:
            >>> # Search by company name
            >>> lockheed_awards = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_recipient_search_text("Lockheed Martin")
            ... )

            >>> # Search by UEI
            >>> specific_recipient = (
            ...     client.awards.search()
            ...     .with_award_types("A", "B")
            ...     .with_recipient_search_text("ABCD1234567890")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_search_text", values=list(search_terms))
        )
        return clone

    def with_recipient_scope(self, scope: str) -> AwardsSearch:
        """
        Filter awards by domestic or foreign recipient location.

        Args:
            scope: Either "domestic" or "foreign" (case-insensitive).

        Returns:
            AwardsSearch: A new instance with the recipient scope filter applied.

        Raises:
            ValidationError: If scope is not "domestic" or "foreign".

        Example:
            >>> # Find contracts awarded to foreign companies
            >>> foreign_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_recipient_scope("foreign")
            ... )

            >>> # Find domestic recipients
            >>> domestic_awards = (
            ...     client.awards.search()
            ...     .grants()
            ...     .with_recipient_scope("domestic")
            ... )
        """
        location_scope = parse_location_scope(scope)

        clone = self._clone()
        clone._filter_objects.append(
            LocationScopeFilter(key="recipient_scope", scope=location_scope)
        )
        return clone

    def with_recipient_locations(self, *locations: dict[str, str]) -> AwardsSearch:
        """
        Filter awards by specific recipient locations.

        Args:
            *locations: One or more location specifications as dictionaries.
                Each dictionary can contain:
                - country_code: Country code (required, e.g., "USA")
                - state_code: State code (optional, e.g., "TX", "CA")
                - county_code: County code (optional)
                - city_name: City name (optional)
                - district_original: Current congressional district (optional)
                - district_current: Congressional district when awarded (optional)
                - zip_code: ZIP code (optional)

        Returns:
            AwardsSearch: A new instance with the recipient location filter applied.

        Example:
            >>> # Find awards to California-based companies
            >>> california_recipients = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_recipient_locations(
            ...         {"state_code": "CA", "country_code": "USA"}
            ...     )
            ... )

            >>> # Find awards to companies in specific cities
            >>> city_recipients = (
            ...     client.awards.search()
            ...     .grants()
            ...     .with_recipient_locations(
            ...         {"city_name": "Seattle", "state_code": "WA", "country_code": "USA"},
            ...         {"city_name": "Portland", "state_code": "OR", "country_code": "USA"}
            ...     )
            ... )
        """
        # Convert dicts to LocationSpec objects internally
        location_specs = [parse_location_spec(loc) for loc in locations]

        clone = self._clone()
        clone._filter_objects.append(
            LocationFilter(key="recipient_locations", locations=location_specs)
        )
        return clone

    def with_recipient_types(self, *type_names: str) -> AwardsSearch:
        """
        Filter awards by recipient or business types.

        Args:
            *type_names: The names of recipient types. Common values include:
                "small_business", "woman_owned_business", "veteran_owned_business",
                "minority_owned_business", "nonprofit", "higher_education", etc.

        Returns:
            AwardsSearch: A new instance with the recipient type filter applied.

        Example:
            >>> # Find contracts awarded to small businesses
            >>> small_biz_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_recipient_types("small_business")
            ... )

            >>> # Find grants to universities and nonprofits
            >>> education_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .with_recipient_types("higher_education", "nonprofit")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_type_names", values=list(type_names))
        )
        return clone

    def with_award_types(self, *award_codes: str) -> AwardsSearch:
        """
        Filter by one or more award type codes.

        **This filter is required** - the API requires at least one award type code.

        Award type codes include:
        - Contracts: A, B, C, D
        - IDVs: IDV_A, IDV_B, IDV_B_A, IDV_B_B, IDV_B_C, IDV_C, IDV_D, IDV_E
        - Grants: 02, 03, 04, 05
        - Loans: 07, 08
        - Direct Payments: 06, 10
        - Other: 09, 11, -1

        Args:
            *award_codes: A sequence of award type codes.

        Returns:
            AwardsSearch: A new instance with the award type filter applied.

        Raises:
            ValidationError: If mixing different award type categories
                (e.g., contracts and grants in the same query).

        Example:
            >>> # Search for specific contract types
            >>> contracts = (
            ...     client.awards.search()
            ...     .with_award_types("A", "B", "C", "D")
            ... )

            >>> # Search for grants only
            >>> grants = (
            ...     client.awards.search()
            ...     .with_award_types("02", "03", "04", "05")
            ... )

            >>> # This will raise ValidationError (mixing categories):
            >>> # client.awards.search().with_award_types("A", "02")  # Contract + Grant
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
        Filter to search for contract awards only.

        This is a convenience method that applies award type codes A, B, C, D.

        Returns:
            AwardsSearch: A new instance configured for contract awards.

        Example:
            >>> # Search for all contracts in FY2024
            >>> fy2024_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .for_fiscal_year(2024)
            ... )
        """
        return self.with_award_types(*CONTRACT_CODES)

    def idvs(self) -> AwardsSearch:
        """
        Filter to search for Indefinite Delivery Vehicle (IDV) awards only.

        IDVs are contract vehicles that provide for an indefinite quantity
        of supplies or services. This method applies all IDV type codes.

        Returns:
            AwardsSearch: A new instance configured for IDV awards.

        Example:
            >>> # Search for all IDVs from Department of Defense
            >>> dod_idvs = (
            ...     client.awards.search()
            ...     .idvs()
            ...     .for_agency("Department of Defense")
            ... )
        """
        return self.with_award_types(*IDV_CODES)

    def loans(self) -> AwardsSearch:
        """
        Filter to search for loan awards only.

        This applies award type codes 07 and 08 for loan awards.

        Returns:
            AwardsSearch: A new instance configured for loan awards.

        Example:
            >>> # Search for all SBA loans in 2023
            >>> sba_loans = (
            ...     client.awards.search()
            ...     .loans()
            ...     .for_agency("Small Business Administration")
            ...     .for_fiscal_year(2023)
            ... )
        """
        return self.with_award_types(*LOAN_CODES)

    def grants(self) -> AwardsSearch:
        """
        Filter to search for grant awards only.

        This applies award type codes 02, 03, 04, 05 for various grant types.

        Returns:
            AwardsSearch: A new instance configured for grant awards.

        Example:
            >>> # Search for education grants
            >>> education_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .for_agency("Department of Education")
            ...     .with_keywords("STEM", "research")
            ... )
        """
        return self.with_award_types(*GRANT_CODES)

    def direct_payments(self) -> AwardsSearch:
        """
        Filter to search for direct payment awards only.

        Direct payments include benefits to individuals and other direct
        assistance. This applies award type codes 06 and 10.

        Returns:
            AwardsSearch: A new instance configured for direct payment awards.

        Example:
            >>> # Search for social security direct payments
            >>> ss_payments = (
            ...     client.awards.search()
            ...     .direct_payments()
            ...     .for_agency("Social Security Administration")
            ... )
        """
        return self.with_award_types(*DIRECT_PAYMENT_CODES)

    def other_assistance(self) -> AwardsSearch:
        """
        Filter to search for other assistance awards.

        This includes insurance programs and other miscellaneous assistance.
        Applies award type codes 09, 11, and -1.

        Returns:
            AwardsSearch: A new instance configured for other assistance awards.

        Example:
            >>> # Search for insurance and other assistance programs
            >>> other_assistance = (
            ...     client.awards.search()
            ...     .other()
            ...     .for_fiscal_year(2024)
            ... )
        """
        return self.with_award_types(*OTHER_CODES)

    def with_award_ids(self, *award_ids: str) -> AwardsSearch:
        """
        Filter by specific award IDs.

        Award IDs can be FAIN (Federal Award Identification Number),
        PIID (Procurement Instrument Identifier), or URI (Unique Record
        Identifier) depending on the award type.

        Args:
            *award_ids: The exact award IDs to search for. Enclose IDs in
                double quotes for exact matching if they contain spaces.

        Returns:
            AwardsSearch: A new instance with the award ID filter applied.

        Example:
            >>> # Search for specific contracts by PIID
            >>> specific_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_award_ids("W58RGZ-20-C-0037", "W911QY-20-C-0012")
            ... )

            >>> # Search for a grant by FAIN
            >>> specific_grant = (
            ...     client.awards.search()
            ...     .grants()
            ...     .with_award_ids("1234567890ABCD")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="award_ids", values=list(award_ids))
        )
        return clone

    def with_award_amounts(
        self, *amounts: Union[dict[str, float], tuple[Optional[float], Optional[float]]]
    ) -> AwardsSearch:
        """
        Filter awards by amount ranges.

        Args:
            *amounts: One or more amount ranges specified as:
                - Dictionary with 'lower_bound' and/or 'upper_bound' keys
                - Tuple of (lower_bound, upper_bound) where None means unbounded

        Returns:
            AwardsSearch: A new instance with the award amount filter applied.

        Example:
            >>> # Find contracts between $1M and $10M
            >>> mid_size_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_award_amounts(
            ...         {"lower_bound": 1000000, "upper_bound": 10000000}
            ...     )
            ... )

            >>> # Using tuple notation
            >>> large_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_award_amounts(
            ...         (5000000, None)  # $5M or more
            ...     )
            ... )

            >>> # Find small grants (under $100K) or large grants (over $1M)
            >>> grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .with_award_amounts(
            ...         {"upper_bound": 100000},
            ...         {"lower_bound": 1000000}
            ...     )
            ... )
        """
        # Convert various input formats to AwardAmount objects
        award_amounts = [parse_award_amount(amt) for amt in amounts]

        clone = self._clone()
        clone._filter_objects.append(AwardAmountFilter(amounts=award_amounts))
        return clone

    def with_cfda_numbers(self, *program_numbers: str) -> AwardsSearch:
        """
        Filter by Catalog of Federal Domestic Assistance (CFDA) numbers.

        CFDA numbers identify specific federal assistance programs.
        Also known as Assistance Listing numbers.

        Args:
            *program_numbers: The CFDA/Assistance Listing numbers to filter by
                (e.g., "10.001", "84.063").

        Returns:
            AwardsSearch: A new instance with the CFDA filter applied.

        Example:
            >>> # Find Pell Grant awards (CFDA 84.063)
            >>> pell_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .with_cfda_numbers("84.063")
            ... )

            >>> # Find multiple agriculture programs
            >>> ag_programs = (
            ...     client.awards.search()
            ...     .grants()
            ...     .with_cfda_numbers("10.001", "10.310", "10.902")
            ... )
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
        Filter by North American Industry Classification System (NAICS) codes.

        NAICS codes classify business establishments for statistical purposes.

        Args:
            require: A list of NAICS codes that must be present.
            exclude: A list of NAICS codes to exclude from results.

        Returns:
            AwardsSearch: A new instance with the NAICS filter applied.

        Example:
            >>> # Find healthcare contracts (NAICS 62)
            >>> healthcare = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_naics_codes(require=["62"])
            ... )

            >>> # Find manufacturing contracts, excluding chemicals
            >>> manufacturing = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_naics_codes(
            ...         require=["31", "32", "33"],  # Manufacturing codes
            ...         exclude=["325"]  # Exclude chemical manufacturing
            ...     )
            ... )
        """
        clone = self._clone()
        # The API expects a list of lists, but for NAICS, each list contains one element.
        require_list = [[code] for code in require] if require else []
        exclude_list = [[code] for code in exclude] if exclude else []
        clone._filter_objects.append(
            TieredCodeFilter(
                key="naics_codes", require=require_list, exclude=exclude_list
            )
        )
        return clone

    def with_psc_codes(
        self,
        require: Optional[list[list[str]]] = None,
        exclude: Optional[list[list[str]]] = None,
    ) -> AwardsSearch:
        """
        Filter by Product and Service Codes (PSC).

        PSCs describe what the government is buying. They use a hierarchical
        structure with categories and subcategories.

        Args:
            require: A list of PSC code paths to require. Each path is a list
                representing the hierarchy (e.g., [["Service", "B", "B5"]]).
            exclude: A list of PSC code paths to exclude.

        Returns:
            AwardsSearch: A new instance with the PSC filter applied.

        Example:
            >>> # Find IT service contracts
            >>> it_services = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_psc_codes(
            ...         require=[["Service", "D"]],  # IT and Telecom services
            ...     )
            ... )

            >>> # Find research services, excluding medical research
            >>> research = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_psc_codes(
            ...         require=[["Service", "A"]],  # Research and Development
            ...         exclude=[["Service", "A", "AN"]]  # Exclude medical R&D
            ...     )
            ... )
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
        Filter contracts by pricing type.

        Common pricing types include fixed-price, cost-reimbursement,
        time-and-materials, etc.

        Args:
            *type_codes: The contract pricing type codes (e.g., "J" for
                firm fixed price, "A" for cost plus fixed fee).

        Returns:
            AwardsSearch: A new instance with the pricing type filter applied.

        Example:
            >>> # Find firm fixed price contracts
            >>> fixed_price = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_contract_pricing_types("J")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="contract_pricing_type_codes", values=list(type_codes))
        )
        return clone

    def with_set_aside_types(self, *type_codes: str) -> AwardsSearch:
        """
        Filter contracts by set-aside type.

        Set-asides reserve contracts for specific types of businesses
        (e.g., small businesses, minority-owned businesses).

        Args:
            *type_codes: The set-aside type codes (e.g., "SBA" for small
                business set-aside, "NONE" for no set-aside).

        Returns:
            AwardsSearch: A new instance with the set-aside filter applied.

        Example:
            >>> # Find small business set-aside contracts
            >>> small_biz_setaside = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_set_aside_types("SBA")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="set_aside_type_codes", values=list(type_codes))
        )
        return clone

    def with_extent_competed_types(self, *type_codes: str) -> AwardsSearch:
        """
        Filter contracts by competition level.

        Indicates how much competition was involved in awarding the contract.

        Args:
            *type_codes: The extent competed type codes (e.g., "A" for
                full and open competition, "G" for not competed).

        Returns:
            AwardsSearch: A new instance with the competition filter applied.

        Example:
            >>> # Find fully competed contracts
            >>> competed = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_extent_competed_types("A")
            ... )
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
        Filter by Treasury Account Symbols (TAS).

        TAS identify the specific Treasury accounts that fund awards.

        Args:
            require: A list of TAS code paths to require. Each path is a list
                representing the hierarchy.
            exclude: A list of TAS code paths to exclude.

        Returns:
            AwardsSearch: A new instance with the TAS filter applied.

        Example:
            >>> # Find awards funded by specific Treasury account
            >>> tas_filtered = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_tas_codes(
            ...         require=[["091"], ["097"]]
            ...     )
            ... )
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
        Filter by specific components of Treasury Accounts.

        Treasury Account components include Agency ID (aid), Main account (main),
        Sub-account (sub), and other identifiers.

        Args:
            *components: Dictionaries representing TAS components. Keys can include:
                - aid: Agency Identifier (3 characters, required)
                - main: Main Account Code (4 digits, required)
                - ata: Allocation Transfer Agency (3 characters, optional)
                - sub: Sub-Account Code (3 digits, optional)
                - bpoa: Beginning Period of Availability (4 digits, optional)
                - epoa: Ending Period of Availability (4 digits, optional)
                - a: Availability Type Code (X or null, optional)

        Returns:
            AwardsSearch: A new instance with the Treasury account filter applied.

        Example:
            >>> # Find awards from specific Treasury accounts
            >>> treasury_awards = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_treasury_account_components(
            ...         {"aid": "097", "main": "0100"},
            ...         {"aid": "012", "main": "3500"}
            ...     )
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            TreasuryAccountComponentsFilter(components=list(components))
        )
        return clone

    def with_def_codes(self, *def_codes: str) -> AwardsSearch:
        """
        Filter by Disaster Emergency Fund (DEF) codes.

        DEF codes identify awards related to specific disaster or emergency
        funding legislation (e.g., COVID-19 relief, infrastructure funding).

        Args:
            *def_codes: The DEF codes. Common codes include:
                - "L", "M", "N", "O", "P": COVID-19 related
                - "Z": Infrastructure Investment and Jobs Act
                - Others defined by specific legislation

        Returns:
            AwardsSearch: A new instance with the DEF code filter applied.

        Example:
            >>> # Find COVID-19 relief contracts
            >>> covid_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_def_codes("L", "M", "N", "O", "P")
            ...     .for_fiscal_year(2021)
            ... )

            >>> # Find infrastructure awards
            >>> infrastructure = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .with_def_codes("Z")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="def_codes", values=list(def_codes))
        )
        return clone
