from abc import ABC, abstractmethod
from typing import (
    Iterator,
    List,
    Dict,
    Any,
    Optional,
    TypeVar,
    Generic,
    TYPE_CHECKING,
    Union,
)
import datetime

# Import exceptions for use by all query builders
from ..exceptions import ValidationError

from .filters import (
    BaseFilter,
    KeywordsFilter,
    TimePeriodFilter,
    AwardDateType,
    LocationScopeFilter,
    LocationFilter,
    SimpleListFilter,
    AwardAmountFilter,
    TieredCodeFilter,
    TreasuryAccountComponentsFilter,
    parse_award_date_type,
    parse_location_scope,
    parse_location_spec,
    parse_agency_spec,
    AgencyFilter,
    parse_award_amount,
)

from ..logging_config import USASpendingLogger, log_query_execution

T = TypeVar("T")

# Import award type code constants for convenience methods
if TYPE_CHECKING:
    from ..models.award_types import (
        CONTRACT_CODES,
        IDV_CODES,
        LOAN_CODES,
        GRANT_CODES,
        DIRECT_PAYMENT_CODES,
        OTHER_CODES,
    )
else:
    # Import at runtime to avoid circular dependencies
    from ..models.award_types import (
        CONTRACT_CODES,
        IDV_CODES,
        LOAN_CODES,
        GRANT_CODES,
        DIRECT_PAYMENT_CODES,
        OTHER_CODES,
    )

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class QueryBuilder(ABC, Generic[T]):
    """Base query builder with automatic pagination support.

    Provides transparent pagination handling for USASpending API queries.
    - Use limit() to set the total number of items to retrieve across all pages
    - Use page_size() to control how many items are fetched per API request
    - Use max_pages() to limit the number of API requests made
    """

    def __init__(self, client: "USASpendingClient"):
        self._client = client
        self._filter_objects: list[BaseFilter] = []
        self._page_size = 100  # Items per page (max 100 per USASpending API)
        self._total_limit = None  # Total items to return (across all pages)
        self._max_pages = None  # Limit total pages fetched
        self._order_by = None
        self._order_direction = "desc"

    def limit(self, num: int) -> "QueryBuilder[T]":
        """Set the total number of items to return across all pages."""
        clone = self._clone()
        clone._total_limit = num
        return clone

    def page_size(self, num: int) -> "QueryBuilder[T]":
        """Set page size (max 100 per USASpending API)."""
        clone = self._clone()
        clone._page_size = min(num, 100)
        return clone

    def max_pages(self, num: int) -> "QueryBuilder[T]":
        """Limit total number of pages fetched."""
        clone = self._clone()
        clone._max_pages = num
        return clone

    def order_by(self, field: str, direction: str = "desc") -> "QueryBuilder[T]":
        """Set sort order."""
        clone = self._clone()
        clone._order_by = field
        clone._order_direction = direction
        return clone

    def __iter__(self) -> Iterator[T]:
        """Iterate over all results, handling pagination automatically."""
        page = 1
        pages_fetched = 0
        items_yielded = 0

        query_type = self.__class__.__name__
        effective_page_size = self._get_effective_page_size()
        logger.info(
            f"Starting {query_type} iteration with page_size={effective_page_size}, "
            f"total_limit={self._total_limit}, max_pages={self._max_pages}"
        )

        while True:
            # Check if we've reached the total limit
            if self._total_limit is not None and items_yielded >= self._total_limit:
                logger.debug(f"Total limit of {self._total_limit} items reached")
                break

            # Check if we've reached the max pages limit
            if self._max_pages and pages_fetched >= self._max_pages:
                logger.debug(f"Max pages limit ({self._max_pages}) reached")
                break

            response = self._execute_query(page)
            results = response.get("results", [])
            has_next = response.get("page_metadata", {}).get("hasNext", False)

            logger.debug(f"Page {page}: {len(results)} results, hasNext={has_next}")

            # Empty page means no more data
            if not results:
                logger.debug("Empty page returned")
                break

            for item in results:
                # Check limit before each yield to handle mid-page limits
                if self._total_limit is not None and items_yielded >= self._total_limit:
                    logger.debug(f"Stopping mid-page at item {items_yielded}")
                    return

                yield self._transform_result(item)
                items_yielded += 1

            # API indicates no more pages
            if not has_next:
                logger.debug("Last page reached (hasNext=false)")
                break

            page += 1
            pages_fetched += 1

    def first(self) -> Optional[T]:
        """Get first result only."""
        logger.debug(f"{self.__class__.__name__}.first() called")
        for result in self.limit(1):
            return result
        return None

    def all(self) -> List[T]:
        """Get all results as a list."""
        logger.debug(f"{self.__class__.__name__}.all() called")
        results = list(self)
        logger.info(f"{self.__class__.__name__}.all() returned {len(results)} results")
        return results

    def __len__(self) -> int:
        """Return the total number of items (delegates to count())."""
        return self.count()

    def __getitem__(self, key: Union[int, slice]) -> Union[T, List[T]]:
        """Support list-like indexing and slicing.

        Args:
            key: Integer index or slice object

        Returns:
            Single item for integer index, list of items for slice

        Raises:
            IndexError: If index is out of bounds
            TypeError: If key is not int or slice
        """
        if isinstance(key, int):
            # Handle single index
            total_count = self.count()

            # Convert negative index to positive
            if key < 0:
                key = total_count + key

            # Check bounds
            if key < 0 or key >= total_count:
                raise IndexError(
                    f"Index {key} out of range for query with {total_count} items"
                )

            # Calculate which page contains this item
            page_num = (key // self._page_size) + 1
            offset_in_page = key % self._page_size

            # Fetch just the page we need
            logger.debug(f"Fetching page {page_num} to get item at index {key}")
            response = self._execute_query(page_num)
            results = response.get("results", [])

            if offset_in_page < len(results):
                return self._transform_result(results[offset_in_page])
            else:
                raise IndexError(f"Index {key} not found in results")

        elif isinstance(key, slice):
            # Handle slice
            total_count = self.count()

            # Convert slice indices
            start, stop, step = key.indices(total_count)

            # If step is not 1, we need to fetch more data
            if step != 1:
                # For non-unit steps, fetch all items in range and then slice
                items = []
                for i in range(start, stop):
                    if (i - start) % step == 0:
                        items.append(self[i])  # Recursive call
                return items

            # For contiguous slices, optimize by fetching only needed pages
            if start >= stop:
                return []

            # Calculate page range
            start_page = (start // self._page_size) + 1
            end_page = ((stop - 1) // self._page_size) + 1

            items = []
            items_collected = 0

            logger.debug(
                f"Fetching pages {start_page} to {end_page} for slice [{start}:{stop}]"
            )

            for page in range(start_page, end_page + 1):
                response = self._execute_query(page)
                results = response.get("results", [])

                # Calculate which items to take from this page
                page_start_idx = (page - 1) * self._page_size

                # Determine overlap with requested slice
                take_start = max(0, start - page_start_idx)
                take_end = min(len(results), stop - page_start_idx)

                if take_start < take_end:
                    for i in range(take_start, take_end):
                        items.append(self._transform_result(results[i]))
                        items_collected += 1

                # Stop if we've collected all requested items
                if items_collected >= (stop - start):
                    break

            return items

        else:
            raise TypeError(
                f"indices must be integers or slices, not {type(key).__name__}"
            )

    @abstractmethod
    def count(self) -> int:
        """Get total count without fetching all results."""
        pass

    @property
    @abstractmethod
    def _endpoint(self) -> str:
        """API endpoint for this query."""
        pass

    @abstractmethod
    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Build request payload."""
        pass

    def _get_effective_page_size(self) -> int:
        """Get the effective page size based on limit and configured page size."""
        if self._total_limit is not None:
            return min(self._page_size, self._total_limit)
        return self._page_size

    @abstractmethod
    def _transform_result(self, data: Dict[str, Any]) -> T:
        """Transform raw result to model instance."""
        pass

    def _aggregate_filters(self) -> dict[str, Any]:
        """Aggregates all filter objects into a single dictionary payload."""
        final_filters: dict[str, Any] = {}

        # Aggregate filters
        for f in self._filter_objects:
            f_dict = f.to_dict()
            for key, value in f_dict.items():
                if key in final_filters and isinstance(final_filters[key], list):
                    final_filters[key].extend(value)
                # Skip keys with empty values to keep payload clean
                elif value:
                    final_filters[key] = value

        logger.debug(f"Applied {len(self._filter_objects)} filters to query")

        return final_filters

    def _fetch_page(self, page: int) -> List[Dict[str, Any]]:
        """Fetch a single page of results."""
        response = self._execute_query(page)
        return response.get("results", [])

    def _execute_query(self, page: int) -> Dict[str, Any]:
        """Execute the query and return raw response."""
        query_type = self.__class__.__name__
        endpoint = self._endpoint

        log_query_execution(logger, query_type, self._filter_objects, endpoint, page)

        payload = self._build_payload(page)
        logger.debug(f"Query payload: {payload}")

        response = self._client._make_request("POST", endpoint, json=payload)

        if "page_metadata" in response:
            metadata = response["page_metadata"]
            logger.debug(
                f"Page metadata: page={metadata.get('page')}, "
                f"total={metadata.get('total')}, hasNext={metadata.get('hasNext')}"
            )

        return response

    def _clone(self) -> "QueryBuilder[T]":
        """Create a copy for method chaining."""
        clone = self.__class__(self._client)
        clone._filter_objects = self._filter_objects.copy()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        return clone


# ==============================================================================
# SearchQueryBuilder - For endpoints with complex filter support
# ==============================================================================


class SearchQueryBuilder(QueryBuilder[T], ABC):
    """
    Base class for search query builders that support complex filtering.

    This intermediate class provides common filter methods for search endpoints
    that support complex filter objects.

    Some query builders (like TransactionsSearch) don't support this level
    of filtering and should extend QueryBuilder directly instead.
    """

    def keywords(self: T, *keywords: str) -> T:
        """
        Filter by keyword search.

        Keywords are searched across multiple fields including award descriptions,
        recipient names, and other text fields.

        Args:
            *keywords: One or more keywords to search for. Multiple keywords
            are combined with OR logic.

        Returns:
            A new instance with the keyword filter applied.

        Example:
            >>> results = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .keywords("Jupiter", "Saturn", "Neptune", "Uranus")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(KeywordsFilter(values=list(keywords)))
        return clone

    def time_period(
        self: T,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        new_awards_only: bool = False,
        date_type: Optional[str] = None,
    ) -> T:
        """
        Filter by a specific date range.

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
            A new instance with the time period filter applied.

        Raises:
            ValidationError: If string dates are not in valid "YYYY-MM-DD" format.

        Example:
            >>> # Find all contracts from 2023
            >>> contracts_2023 = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .time_period("2023-01-01", "2023-12-31")
            ... )

            >>> # Find only NEW grants started in Q1 2024
            >>> new_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .time_period("2024-01-01", "2024-03-31", new_awards_only=True)
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

    def fiscal_year(
        self: T,
        year: int,
        new_awards_only: bool = False,
        date_type: Optional[str] = None,
    ) -> T:
        """
        Convenience method to apply a `time_period` filter for a U.S. government fiscal year
        by applying the appropriate start and end dates.

        Args:
            year: The fiscal year to filter by (e.g., 2024 for FY2024).
            new_awards_only: If True, only returns awards that started within
                the fiscal year. Defaults to False.
            date_type: The type of date to filter on. Can be a string:
                "action_date", "date_signed", "last_modified_date", or
                "new_awards_only". If not specified, uses default date type.
                Case-insensitive.

        Returns:
            A new instance with the fiscal year filter applied.

        Example:
            >>> # Get all contracts from FY2024
            >>> fy2024_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .fiscal_year(2024)
            ... )

            >>> # Get only NEW grants started in FY2023
            >>> new_fy2023_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .fiscal_year(2023, new_awards_only=True)
            ... )
        """
        
        # A fiscal year is negatively offset to the calendar year by 3 months. For example,
        # FY 2024 ran from October 1, 2023 to September 30, 2024.

        if not isinstance(year, int) or year < 1000 or year > 9999:
            raise ValidationError(f"Fiscal year must be provided as a 4-digit integer: {year}")

        start_date = datetime.date(year - 1, 10, 1)
        end_date = datetime.date(year, 9, 30)
        
        return self.time_period(
            start_date=start_date,
            end_date=end_date,
            new_awards_only=new_awards_only,
            date_type=date_type,
        )

    def place_of_performance_scope(self: T, scope: str) -> T:
        """
        Filter by domestic or foreign place of performance.

        Args:
            scope: Either "domestic" or "foreign" (case-insensitive).

        Returns:
            A new instance with the location scope filter applied.

        Raises:
            ValidationError: If scope is not "domestic" or "foreign".

        Example:
            >>> foreign_aid = (
            ...     client.awards.search()
            ...     .grants()
            ...     .place_of_performance_scope("foreign")
            ... )
        """
        location_scope = parse_location_scope(scope)

        clone = self._clone()
        clone._filter_objects.append(
            LocationScopeFilter(key="place_of_performance_scope", scope=location_scope)
        )
        return clone

    def place_of_performance_locations(
        self: T, *locations: dict[str, str]
    ) -> T:
        """
        Filter by specific geographic places of performance.

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
            A new instance with the location filter applied.

        Example:
            >>> texas_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .place_of_performance_locations(
            ...         {"state_code": "TX", "city_name": "Austin", "country_code": "USA"},
            ...         {"state_code": "TX", "city_name": "Houston", "country_code": "USA"},
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

    def recipient_scope(self: T, scope: str) -> T:
        """
        Filter by domestic or foreign recipient location.

        Args:
            scope: Either "domestic" or "foreign" (case-insensitive).

        Returns:
            A new instance with the recipient scope filter applied.

        Raises:
            ValidationError: If scope is not "domestic" or "foreign".

        Example:
            >>> foreign_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .recipient_scope("foreign")
            ... )
        """
        location_scope = parse_location_scope(scope)

        clone = self._clone()
        clone._filter_objects.append(
            LocationScopeFilter(key="recipient_scope", scope=location_scope)
        )
        return clone

    def recipient_locations(self: T, *locations: dict[str, str]) -> T:
        """
        Filter by specific recipient locations.

        Args:
            *locations: One or more location specifications as dictionaries.
                Each dictionary can contain:
                - country_code: Country code (required, e.g., "USA")
                - state_code: State code (optional)
                - county_code: County code (optional)
                - city_name: City name (optional)
                - district_original: Current congressional district (optional)
                - district_current: Congressional district when awarded (optional)
                - zip_code: ZIP code (optional)

        Returns:
            A new instance with the recipient location filter applied.

        Example:
            >>> california_recipients = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .recipient_locations(
            ...         {"state_code": "CA", "country_code": "USA"}
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

    # ==========================================================================
    # Groups 3-6: Agency, Award, Code Filters, and Convenience Methods
    # ==========================================================================

    def agencies(self: T, *agencies: dict[str, str]) -> T:
        """
        Filter awards by one or more awarding or funding agencies.

        Args:
            *agencies: One or more agency specifications as dictionaries.
                Each dictionary must contain:
                - name: Agency name (required, e.g., "Department of Defense")
                - type: "awarding" or "funding" (required)
                - tier: "toptier" or "subtier" (required)
                - toptier_name: Parent agency name (optional, for scoping subtiers)

        Returns:
            T: A new instance with the agency filter applied.

        Raises:
            ValidationError: If required fields are missing or invalid.

        Example:
            >>> # Find DOD and NASA contracts
            >>> multi_agency = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .agencies(
            ...         {"name": "Department of Defense", "type": "awarding", "tier": "toptier"},
            ...         {"name": "National Aeronautics and Space Administration", "type": "awarding", "tier": "toptier"},
            ...     )
            ... )

            >>> # Find awards with specific subtier agency scoped to parent
            >>> subtier_awards = (
            ...     client.awards.search()
            ...     .grants()
            ...     .agencies(
            ...         {
            ...             "name": "Office of Inspector General",
            ...             "type": "awarding",
            ...             "tier": "subtier",
            ...             "toptier_name": "Department of Defense"
            ...         }
            ...     )
            ... )
        """
        from .filters import parse_agency_spec, AgencyFilter

        # Parse each agency dict into AgencySpec objects
        agency_specs = [parse_agency_spec(agency) for agency in agencies]

        clone = self._clone()
        clone._filter_objects.append(AgencyFilter(agencies=agency_specs))
        return clone


    def agency(
        self,
        name: str,
        agency_type: str = "awarding",
        tier: str = "toptier",
        toptier_name: str = None,
    ) -> T:
        """
        Helper method: Filter awards by a single agency (wraps agencies()).

        This is a convenience wrapper around the agencies() method for improved readability
        when filtering by a single agency.

        Args:
            name: The name of the agency (e.g., "Department of Defense").
            agency_type: Whether to filter by "awarding" agency (who manages
                the award) or "funding" agency (who provides the money).
                Defaults to "awarding".
            tier: Whether to filter by "toptier" agency (main department) or
                "subtier" agency (sub-agency or office). Defaults to "toptier".
            toptier_name: Parent agency name (optional, for scoping subtiers).

        Returns:
            T: A new instance with the agency filter applied.

        Example:
            >>> # Find NASA contracts (more readable than agencies())
            >>> nasa_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .agency("National Aeronautics and Space Administration")
            ... )
        """
        agency_dict = {
            "name": name,
            "type": agency_type,
            "tier": tier,
        }
        if toptier_name:
            agency_dict["toptier_name"] = toptier_name
        return self.agencies(agency_dict)


    def recipient_search_text(self: T, *search_terms: str) -> T:
        """
        Search for awards by recipient name, UEI, or DUNS.

        This performs a text search across recipient identifiers and names.

        Args:
            *search_terms: Text to search for across recipient name,
                UEI (Unique Entity Identifier), and DUNS number fields.

        Returns:
            T: A new instance with the recipient search filter applied.

        Example:
            >>> # Search by company name
            >>> lockheed_awards = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .recipient_search_text("Lockheed Martin")
            ... )

            >>> # Search by UEI
            >>> specific_recipient = (
            ...     client.awards.search()
            ...     .award_type_codes("A", "B")
            ...     .recipient_search_text("ABCD1234567890")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_search_text", values=list(search_terms))
        )
        return clone


    def recipient_type_names(self: T, *type_names: str) -> T:
        """
        Filter awards by recipient or business types.

        Args:
            *type_names: The names of recipient types. Common values include:
                "small_business", "woman_owned_business", "veteran_owned_business",
                "minority_owned_business", "nonprofit", "higher_education", etc.

        Returns:
            T: A new instance with the recipient type filter applied.

        Example:
            >>> # Find contracts awarded to small businesses
            >>> small_biz_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .recipient_type_names("small_business")
            ... )

            >>> # Find grants to universities and nonprofits
            >>> education_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .recipient_type_names("higher_education", "nonprofit")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="recipient_type_names", values=list(type_names))
        )
        return clone


    def award_ids(self: T, *award_ids: str) -> T:
        """
        Filter by specific award IDs.

        Award IDs can be FAIN (Federal Award Identification Number),
        PIID (Procurement Instrument Identifier), or URI (Unique Record
        Identifier) depending on the award type.

        Args:
            *award_ids: The exact award IDs to search for. Enclose IDs in
                double quotes for exact matching if they contain spaces.

        Returns:
            T: A new instance with the award ID filter applied.

        Example:
            >>> # Search for specific contracts by PIID
            >>> specific_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .award_ids("W58RGZ-20-C-0037", "W911QY-20-C-0012")
            ... )

            >>> # Search for a grant by FAIN
            >>> specific_grant = (
            ...     client.awards.search()
            ...     .grants()
            ...     .award_ids("1234567890ABCD")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="award_ids", values=list(award_ids))
        )
        return clone


    def award_amounts(
        self, *amounts: Union[dict[str, float], tuple[Optional[float], Optional[float]]]
    ) -> T:
        """
        Filter awards by amount ranges.

        Args:
            *amounts: One or more amount ranges specified as:
                - Dictionary with 'lower_bound' and/or 'upper_bound' keys
                - Tuple of (lower_bound, upper_bound) where None means unbounded

        Returns:
            T: A new instance with the award amount filter applied.

        Example:
            >>> # Find contracts between $1M and $10M
            >>> mid_size_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .award_amounts(
            ...         {"lower_bound": 1000000, "upper_bound": 10000000}
            ...     )
            ... )

            >>> # Using tuple notation
            >>> large_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .award_amounts(
            ...         (5000000, None)  # $5M or more
            ...     )
            ... )

            >>> # Find small grants (under $100K) or large grants (over $1M)
            >>> grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .award_amounts(
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


    def award_type_codes(self: T, *award_codes: str) -> T:
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
            T: A new instance with the award type filter applied.

        Note:
            AwardsSearch overrides this method to add validation that prevents
            mixing different award type categories (e.g., contracts and grants).

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
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="award_type_codes", values=list(award_codes))
        )
        return clone


    def contracts(self: T) -> T:
        """
        Filter to search for contract awards only.

        This is a convenience method that applies award type codes A, B, C, D.

        Returns:
            T: A new instance configured for contract awards.

        Example:
            >>> # Search for all contracts in FY2024
            >>> fy2024_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .fiscal_year(2024)
            ... )
        """
        return self.award_type_codes(*CONTRACT_CODES)


    def idvs(self: T) -> T:
        """
        Filter to search for Indefinite Delivery Vehicle (IDV) awards only.

        IDVs are contract vehicles that provide for an indefinite quantity
        of supplies or services. This method applies all IDV type codes.

        Returns:
            T: A new instance configured for IDV awards.

        Example:
            >>> # Search for all IDVs from Department of Defense
            >>> dod_idvs = (
            ...     client.awards.search()
            ...     .idvs()
            ...     .agency("Department of Defense")
            ... )
        """
        return self.award_type_codes(*IDV_CODES)


    def loans(self: T) -> T:
        """
        Filter to search for loan awards only.

        This applies award type codes 07 and 08 for loan awards.

        Returns:
            T: A new instance configured for loan awards.

        Example:
            >>> # Search for all SBA loans in 2023
            >>> sba_loans = (
            ...     client.awards.search()
            ...     .loans()
            ...     .agency("Small Business Administration")
            ...     .fiscal_year(2023)
            ... )
        """
        return self.award_type_codes(*LOAN_CODES)


    def grants(self: T) -> T:
        """
        Filter to search for grant awards only.

        This applies award type codes 02, 03, 04, 05 for various grant types.

        Returns:
            T: A new instance configured for grant awards.

        Example:
            >>> # Search for education grants
            >>> education_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .fiscal_year(2024)
            ...     .keywords("STEM", "research")
            ... )
        """
        return self.award_type_codes(*GRANT_CODES)


    def direct_payments(self: T) -> T:
        """
        Filter to search for direct payment awards only.

        Direct payments include benefits to individuals and other direct
        assistance. This applies award type codes 06 and 10.

        Returns:
            T: A new instance configured for direct payment awards.

        Example:
            >>> # Search for social security direct payments
            >>> ss_payments = (
            ...     client.awards.search()
            ...     .direct_payments()
            ...     .fiscal_year(2024)
            ... )
        """
        return self.award_type_codes(*DIRECT_PAYMENT_CODES)


    def other_assistance(self: T) -> T:
        """
        Filter to search for other assistance awards.

        This includes insurance programs and other miscellaneous assistance.
        Applies award type codes 09, 11, and -1.

        Returns:
            T: A new instance configured for other assistance awards.

        Example:
            >>> # Search for insurance and other assistance programs
            >>> other_assistance = (
            ...     client.awards.search()
            ...     .other_assistance()
            ...     .fiscal_year(2024)
            ... )
        """
        return self.award_type_codes(*OTHER_CODES)


    def program_numbers(self: T, *program_numbers: str) -> T:
        """
        Filter by program numbers (CFDA/Assistance Listing numbers).

        CFDA numbers identify specific federal assistance programs.
        Also known as Assistance Listing numbers or program numbers.

        Args:
            *program_numbers: The CFDA/Assistance Listing numbers to filter by
                (e.g., "10.001", "84.063").

        Returns:
            T: A new instance with the program number filter applied.

        Example:
            >>> # Find Pell Grant awards (CFDA 84.063)
            >>> pell_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .program_numbers("84.063")
            ... )

            >>> # Find multiple agriculture programs
            >>> ag_programs = (
            ...     client.awards.search()
            ...     .grants()
            ...     .program_numbers("10.001", "10.310", "10.902")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="program_numbers", values=list(program_numbers))
        )
        return clone


    def naics_codes(
        self,
        require: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
    ) -> T:
        """
        Filter by North American Industry Classification System (NAICS) codes.

        NAICS codes classify business establishments for statistical purposes.

        Args:
            require: A list of NAICS codes that must be present.
            exclude: A list of NAICS codes to exclude from results.

        Returns:
            T: A new instance with the NAICS filter applied.

        Example:
            >>> # Find healthcare contracts (NAICS 62)
            >>> healthcare = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .naics_codes(require=["62"])
            ... )

            >>> # Find manufacturing contracts, excluding chemicals
            >>> manufacturing = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .naics_codes(
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


    def psc_codes(
        self,
        require: Optional[list[list[str]]] = None,
        exclude: Optional[list[list[str]]] = None,
    ) -> T:
        """
        Filter by Product and Service Codes (PSC).

        PSCs describe what the government is buying. They use a hierarchical
        structure with categories and subcategories.

        Args:
            require: A list of PSC code paths to require. Each path is a list
                representing the hierarchy (e.g., [["Service", "B", "B5"]]).
            exclude: A list of PSC code paths to exclude.

        Returns:
            T: A new instance with the PSC filter applied.

        Example:
            >>> # Find IT service contracts
            >>> it_services = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .psc_codes(
            ...         require=[["Service", "D"]],  # IT and Telecom services
            ...     )
            ... )

            >>> # Find research services, excluding medical research
            >>> research = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .psc_codes(
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


    def contract_pricing_type_codes(self: T, *type_codes: str) -> T:
        """
        Filter contracts by pricing type.

        Common pricing types include fixed-price, cost-reimbursement,
        time-and-materials, etc.

        Args:
            *type_codes: The contract pricing type codes (e.g., "J" for
                firm fixed price, "A" for cost plus fixed fee).

        Returns:
            T: A new instance with the pricing type filter applied.

        Example:
            >>> # Find firm fixed price contracts
            >>> fixed_price = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .contract_pricing_type_codes("J")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="contract_pricing_type_codes", values=list(type_codes))
        )
        return clone


    def set_aside_type_codes(self: T, *type_codes: str) -> T:
        """
        Filter contracts by set-aside type.

        Set-asides reserve contracts for specific types of businesses
        (e.g., small businesses, minority-owned businesses).

        Args:
            *type_codes: The set-aside type codes (e.g., "SBA" for small
                business set-aside, "NONE" for no set-aside).

        Returns:
            T: A new instance with the set-aside filter applied.

        Example:
            >>> # Find small business set-aside contracts
            >>> small_biz_setaside = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .set_aside_type_codes("SBA")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="set_aside_type_codes", values=list(type_codes))
        )
        return clone


    def extent_competed_type_codes(self: T, *type_codes: str) -> T:
        """
        Filter contracts by competition level.

        Indicates how much competition was involved in awarding the contract.

        Args:
            *type_codes: The extent competed type codes (e.g., "A" for
                full and open competition, "G" for not competed).

        Returns:
            T: A new instance with the competition filter applied.

        Example:
            >>> # Find fully competed contracts
            >>> competed = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .extent_competed_type_codes("A")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="extent_competed_type_codes", values=list(type_codes))
        )
        return clone


    def tas_codes(
        self,
        require: Optional[list[list[str]]] = None,
        exclude: Optional[list[list[str]]] = None,
    ) -> T:
        """
        Filter by Treasury Account Symbols (TAS).

        TAS identify the specific Treasury accounts that fund awards.

        Args:
            require: A list of TAS code paths to require. Each path is a list
                representing the hierarchy.
            exclude: A list of TAS code paths to exclude.

        Returns:
            T: A new instance with the TAS filter applied.

        Example:
            >>> # Find awards funded by specific Treasury account
            >>> tas_filtered = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .tas_codes(
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


    def treasury_account_components(
        self, *components: dict[str, str]
    ) -> T:
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
            T: A new instance with the Treasury account filter applied.

        Example:
            >>> # Find awards from specific Treasury accounts
            >>> treasury_awards = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .treasury_account_components(
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


    def def_codes(self: T, *def_codes: str) -> T:
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
            T: A new instance with the DEF code filter applied.

        Example:
            >>> # Find COVID-19 relief contracts
            >>> covid_contracts = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .def_codes("L", "M", "N", "O", "P")
            ...     .fiscal_year(2021)
            ... )

            >>> # Find infrastructure awards
            >>> infrastructure = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .def_codes("Z")
            ... )
        """
        clone = self._clone()
        clone._filter_objects.append(
            SimpleListFilter(key="def_codes", values=list(def_codes))
        )
        return clone

