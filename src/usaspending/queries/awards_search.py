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
    .fiscal_year(2024)
    .recipient_type_names("small_business")
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
    .agency("Department of Education")
    .fiscal_year(2023)
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
    .agency("National Aeronautics and Space Administration")
    .time_period("2020-03-01", date.today().isoformat())
    .place_of_performance_locations(
        {"state_code": "CA", "country_code": "USA"}
    )
    .award_amounts(
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
    Use the `.award_type_codes()` method or convenience methods like `.contracts()`, `.grants()`, `.loans()`, `.idvs()`, `.direct_payments()`, or `.other_assistance()`
    to set the award type category.

2. **Single Category Restriction**: You cannot mix different award type categories
   (e.g., contracts and grants) in a single query. Use separate queries for each.

3. **Automatic Pagination**: Iterating over results automatically handles pagination.
   Use `limit()` to control returned result size.

"""

from __future__ import annotations

from typing import Any

from ..client import USASpendingClient
from usaspending.exceptions import ValidationError
from usaspending.models.award_factory import create_award
from usaspending.models import Award
from usaspending.models.contract import Contract
from usaspending.models.grant import Grant
from usaspending.models.idv import IDV
from usaspending.models.loan import Loan
from usaspending.queries.query_builder import SearchQueryBuilder
from usaspending.logging_config import USASpendingLogger
from usaspending.queries.filters import (
    SimpleListFilter,
)

# Import award type codes from models
# These are defined by USASpending.gov and represent different categories of awards
from ..models.award_types import (
    CONTRACT_CODES,
    IDV_CODES,
    LOAN_CODES,
    GRANT_CODES,
    AWARD_TYPE_GROUPS,
)

logger = USASpendingLogger.get_logger(__name__)


class AwardsSearch(SearchQueryBuilder["Award"]):
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
                "Use the .award_type_codes() method or a convenience method like .contracts()."
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
            >>> search.award_type_codes("A", "02")  # Contract + Grant
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
            >>> contracts = client.awards.search().contracts().fiscal_year(2024)
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
                "Use the .award_type_codes() method or a convenience method like .contracts()."
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
            >>> search = client.awards.search().fiscal_year(2024)
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

    def award_type_codes(self, *award_codes: str) -> AwardsSearch:
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
            ...     .award_type_codes("A", "B", "C", "D")
            ... )

            >>> # Search for grants only
            >>> grants = (
            ...     client.awards.search()
            ...     .award_type_codes("02", "03", "04", "05")
            ... )

            >>> # This will raise ValidationError (mixing categories):
            >>> # client.awards.search().award_type_codes("A", "02")  # Contract + Grant
        """
        new_codes = set(award_codes)
        self._validate_single_award_type_category(new_codes)

        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="award_type_codes", values=list(award_codes))
        )
        return clone

