from __future__ import annotations

import datetime
import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    TypeVar,
)

from ..config import config

# Import exceptions for use by all query builders
from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger, log_query_execution

# Import award type code constants for convenience methods
from ..models.award_types import (
    CONTRACT_CODES,
    DIRECT_PAYMENT_CODES,
    GRANT_CODES,
    IDV_CODES,
    LOAN_CODES,
    OTHER_CODES,
)
from ..utils.validations import validate_non_empty_string
from .base_query import BaseQuery
from .filters import (
    AgencyFilter,
    AwardAmountFilter,
    AwardDateType,
    BaseFilter,
    KeywordsFilter,
    LocationFilter,
    LocationScopeFilter,
    NAICSFilter,
    PSCFilter,
    SimpleListFilter,
    SimpleStringFilter,
    TieredCodeFilter,
    TimePeriodFilter,
    TreasuryAccountComponentsFilter,
    parse_agency_spec,
    parse_api_date,
    parse_award_amount,
    parse_award_date_type,
    parse_fiscal_year,
    parse_location_scope,
    parse_location_spec,
    validate_date_range,
)

# Element type produced by a query (an Award, a Transaction, ...).
T = TypeVar("T")

# Self type for chainable filter methods. Distinct from T: a filter returns
# another builder of the same concrete class, not one of its result items.
SQB = TypeVar("SQB", bound="SearchQueryBuilder[Any]")

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class QueryBuilder(BaseQuery[T], ABC):
    """Base query builder with automatic pagination support.

    Provides transparent pagination handling for USASpending API queries.
    - Use limit() to set the total number of items to retrieve across all pages
    - Use page_size() to control how many items are fetched per API request
    - Use max_pages() to limit the number of API requests made
    """

    #: HTTP method this endpoint expects. GET endpoints send their payload as
    #: query parameters; POST sends a JSON body.
    _http_method: ClassVar[Literal["GET", "POST"]] = "POST"

    def __init__(self, client: USASpendingClient) -> None:
        super().__init__()
        self._client = client
        self._filter_objects: list[BaseFilter] = []
        # The result of count(), memoized for indexing so that walking pages does
        # not re-count. count() deliberately does not read it, so that repeated
        # calls observe fresh data.
        self._cached_count: int | None = None

    def __iter__(self) -> Iterator[T]:
        """Iterate over all results, handling pagination automatically.

        If no explicit limit is set and config.default_result_limit is configured,
        that default will be applied automatically. A warning is logged when
        config.warn_on_large_result_set is enabled and the result set exceeds
        config.large_result_threshold.
        """
        page = 1
        pages_fetched = 0
        items_yielded = 0

        # Apply default limit if no explicit limit was set
        effective_limit = self._total_limit
        if effective_limit is None and config.default_result_limit is not None:
            effective_limit = config.default_result_limit
            logger.info(
                f"No limit set. Using default limit of {effective_limit}. "
                "Set explicit limit() or configure default_result_limit=None to disable."
            )

        query_type = self.__class__.__name__
        effective_page_size = self._get_effective_page_size()
        logger.info(
            f"Starting {query_type} iteration with page_size={effective_page_size}, "
            f"total_limit={effective_limit}, max_pages={self._max_pages}"
        )

        while True:
            # Check if we've reached the total limit
            if effective_limit is not None and items_yielded >= effective_limit:
                logger.debug(f"Total limit of {effective_limit} items reached")
                break

            # Check if we've reached the max pages limit
            if self._max_pages is not None and pages_fetched >= self._max_pages:
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
                if effective_limit is not None and items_yielded >= effective_limit:
                    logger.debug(f"Stopping mid-page at item {items_yielded}")
                    return

                transformed = self._transform_result(item)
                if transformed is not None and self._row_passes(transformed):
                    yield transformed
                    items_yielded += 1

            # API indicates no more pages
            if not has_next:
                logger.debug("Last page reached (hasNext=false)")
                break

            page += 1
            pages_fetched += 1

    def first(self) -> T | None:
        """Get first result only."""
        logger.debug(f"{self.__class__.__name__}.first() called")
        return super().first()

    def all(self) -> list[T]:
        """Get all results as a list."""
        logger.debug(f"{self.__class__.__name__}.all() called")
        results = super().all()
        logger.info(f"{self.__class__.__name__}.all() returned {len(results)} results")
        return results

    def _get_cached_count(self) -> int:
        """Get the count, using the cached value if one is available.

        Holds what :meth:`count` reports, so it honors ``limit()`` and
        ``max_pages()`` too. This avoids redundant count API calls during
        indexing/slicing operations.
        """
        if self._cached_count is None:
            self._cached_count = self.count()
        return self._cached_count

    def __getitem__(self, key: int | slice) -> T | list[T]:
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
            total_count = self._get_cached_count()

            # Convert negative index to positive
            if key < 0:
                key = total_count + key

            # Check bounds
            if key < 0 or key >= total_count:
                raise IndexError(f"Index {key} out of range for query with {total_count} items")

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
            total_count = self._get_cached_count()

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

            logger.debug(f"Fetching pages {start_page} to {end_page} for slice [{start}:{stop}]")

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
            raise TypeError(f"indices must be integers or slices, not {type(key).__name__}")

    @property
    @abstractmethod
    def _endpoint(self) -> str:
        """API endpoint for this query."""
        pass

    @abstractmethod
    def _build_payload(self, page: int) -> dict[str, Any]:
        """Build request payload."""
        pass

    @abstractmethod
    def _transform_result(self, data: dict[str, Any]) -> T | None:
        """Transform raw result to model instance.

        Args:
            data: Raw API result dictionary.

        Returns:
            Model instance, or None to skip invalid/filtered items.
        """
        pass

    def _aggregate_filters(self) -> dict[str, Any]:
        """Aggregates all filter objects into a single dictionary payload."""
        final_filters: dict[str, Any] = {}

        # Aggregate filters
        for f in self._filter_objects:
            f_dict = f.to_dict()
            for key, value in f_dict.items():
                if isinstance(value, list):
                    # Copy: filters hand back their internal list and _clone()
                    # shares filter objects between a query and its clones.
                    value = list(value)
                if isinstance(final_filters.get(key), list):
                    final_filters[key] += value
                # Skip keys with empty values to keep payload clean
                elif value:
                    final_filters[key] = value

        logger.debug(f"Applied {len(self._filter_objects)} filters to query")

        return final_filters

    def to_filters_payload(self) -> dict[str, Any]:
        """Return the assembled API ``filters`` object for this query.

        Exposes the filter block that paginated search payloads embed, so callers
        (such as the download resource) can obtain the filters without executing a
        search. The returned dictionary is the same one used under the ``filters``
        key of the request payload.

        Returns:
            dict[str, Any]: The aggregated filter payload built from this query's
            filter methods.
        """
        return self._aggregate_filters()

    def _execute_query(self, page: int) -> dict[str, Any]:
        """Execute the query and return raw response.

        Most of these endpoints take a POST body. A GET endpoint sets
        ``_http_method`` and its payload is sent as query parameters instead,
        which is the only thing that differed between them.
        """
        query_type = self.__class__.__name__
        endpoint = self._endpoint

        log_query_execution(logger, query_type, self._filter_objects, endpoint, page)

        payload = self._build_payload(page)
        logger.debug(f"Query payload: {payload}")

        # A GET carries its payload as query parameters; everything else as a body.
        channel = {"params": payload} if self._http_method == "GET" else {"json": payload}
        response = self._client._make_request(self._http_method, endpoint, **channel)

        if "page_metadata" in response:
            metadata = response["page_metadata"]
            logger.debug(
                f"Page metadata: page={metadata.get('page')}, "
                f"total={metadata.get('total')}, hasNext={metadata.get('hasNext')}"
            )

        return response

    # ==========================================================================
    # Counting
    #
    # count() is shared and not overridden: it owns the capping and the logging.
    # Subclasses implement _compute_raw_count() and pick one of the mechanisms
    # below, which cover everything these endpoints actually offer. Keeping the
    # capping here is what stops some counts from honoring a bound and others not.
    # ==========================================================================

    def count(self) -> int:
        """Return how many results this query yields.

        ``limit()`` and ``max_pages()`` are the caller's own bounds, so they apply
        here as they do to iteration: ``count()``, ``len()`` and ``len(all())``
        always agree. For the server's total under a set of filters, count before
        bounding the query. ``config.default_result_limit`` is deliberately not
        applied; see :meth:`_count_via_paging`.

        This always asks the API, so repeated calls observe fresh data. The only
        count cache is :meth:`_get_cached_count`, which indexing uses to avoid
        re-counting while walking pages.

        Returns:
            int: Matching results, held to whatever bounds are set.
        """
        logger.debug(f"{self.__class__.__name__}.count() called")

        # Bounds that forbid every result answer the question themselves, so the
        # request is skipped rather than made and then discarded by the cap.
        count = 0 if self._yields_nothing() else self._cap(self._compute_raw_count())
        logger.info(f"{self.__class__.__name__}.count() = {count}")
        return count

    @abstractmethod
    def _compute_raw_count(self) -> int:
        """Return the matching total, before :meth:`count` applies the bounds.

        Usually the API's own figure. A query that filters rows in memory must
        instead report what it would yield, or :meth:`count` disagrees with
        iteration.

        Implement using one of the ``_count_*`` mechanisms below where possible.

        Returns:
            int: Total matching results.
        """

    def _count_via_endpoint(
        self,
        endpoint: str,
        key: str,
        method: str = "GET",
        json: dict[str, Any] | None = None,
    ) -> int:
        """Count using a dedicated count endpoint.

        Args:
            endpoint: Count endpoint path.
            key: Key in the response holding the count.
            method: HTTP method the endpoint expects.
            json: Request body, for endpoints that take one.

        Returns:
            int: The reported count.
        """
        # These endpoints derive their scope from the URL or the supplied body,
        # so log the filters only when they are actually part of the request.
        log_query_execution(
            logger,
            f"{self.__class__.__name__}.count",
            self._filter_objects if json else [],
            endpoint,
        )
        response = self._client._make_request(method, endpoint, json=json)
        return response.get(key, 0)

    def _count_via_page_metadata(self, key: str) -> int:
        """Count from the page metadata of the first page of results.

        Args:
            key: Key within ``page_metadata`` holding the total.

        Returns:
            int: The reported count.
        """
        response = self._execute_query(1)
        return response.get("page_metadata", {}).get(key, 0)

    def _row_passes(self, item: T) -> bool:
        """Report whether a fetched row belongs in the result set.

        True for every row, unless a subclass filters in memory because the
        endpoint offers no server-side equivalent. Consulted before the row is
        yielded and before it counts toward ``limit()``, so such a filter narrows
        the results rather than the fetch: ``limit(1)`` means one matching row, not
        one row that may then be discarded. That is what lets :meth:`first` and
        ``bool()`` agree with :meth:`__len__` on a filtered query.

        A subclass that overrides this should also override :meth:`_countable_rows`
        if it counts by paging, since the two answer for different layers: this one
        decides what iteration yields, that one what the count reports.

        Args:
            item: A transformed row.

        Returns:
            bool: True if the row should be yielded.
        """
        return True

    def _countable_rows(self, results: list[dict[str, Any]]) -> int:
        """Return how many of one page's rows count toward the total.

        Every row, since the default :meth:`_row_passes` keeps them all. A subclass
        that filters in memory overrides this too, or its count reports rows that
        iterating the same query never yields. Kept separate from
        :meth:`_row_passes` so that counting stays cheap for the builders that do
        not filter: this receives raw rows and need not build a model per row.

        Args:
            results: The raw rows from one page of the response.

        Returns:
            int: How many of them the caller would see.
        """
        return len(results)

    def _count_via_paging(self) -> int:
        """Count by walking pages and summing result lengths.

        The only correct mechanism for endpoints that report no count at all.
        Unlike iterating the query, this counts raw response rows, so by default it
        does not build a model per row only to discard it, and it deliberately does
        not apply ``config.default_result_limit`` -- that default exists to stop
        unbounded *fetches*, and letting it cap a count would silently report
        10,000 for any larger result set.

        Explicit ``limit()`` and ``max_pages()`` are honored here as well as in
        :meth:`count`, which is not redundant: stopping early is what keeps a
        bounded query from paging the whole result set, and capping an already
        bounded figure changes nothing.

        Returns:
            int: Number of matching rows.
        """
        total = 0
        page = 1
        pages_fetched = 0

        while True:
            if self._max_pages is not None and pages_fetched >= self._max_pages:
                logger.debug(f"Max pages limit ({self._max_pages}) reached while counting")
                break

            response = self._execute_query(page)
            results = response.get("results", [])

            countable = self._countable_rows(results)
            if self._total_limit is not None:
                countable = min(countable, self._total_limit - total)
            total += countable

            if self._total_limit is not None and total >= self._total_limit:
                logger.debug(f"Total limit of {self._total_limit} reached while counting")
                break

            if not results or not response.get("page_metadata", {}).get("hasNext", False):
                break

            page += 1
            pages_fetched += 1

        return total

    def _new_instance(self) -> QueryBuilder[T]:
        """Construct an empty instance bound to the same client."""
        return self.__class__(self._client)

    def _clone(self) -> QueryBuilder[T]:
        """Copy the query, including its filters.

        ``_cached_count`` is deliberately not carried over: the clone starts
        fresh, and its filters may differ from this one's.

        Returns:
            QueryBuilder: A copy carrying the same filters and pagination state.
        """
        clone = super()._clone()
        clone._filter_objects = self._filter_objects.copy()
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

    def _with_filter(self: SQB, filter_obj: BaseFilter) -> SQB:
        """Return a clone with one more filter applied.

        Every filter method below reduces to this: validate the arguments, build
        the filter object, and hand it here. Keeping the clone-and-append in one
        place is what lets those methods stay a single expression.

        Args:
            filter_obj: The filter to add.

        Returns:
            A new instance of the same class with the filter appended.
        """
        clone = self._clone()
        clone._filter_objects.append(filter_obj)
        return clone

    def keywords(self: SQB, *keywords: str) -> SQB:
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
        return self._with_filter(KeywordsFilter(values=list(keywords)))

    def time_period(
        self: SQB,
        start_date: datetime.date | str,
        end_date: datetime.date | str,
        new_awards_only: bool = False,
        date_type: str | None = None,
    ) -> SQB:
        """
        Filter by a specific date range.

        Args:
            start_date: Start of date range. Accepts datetime.date or "YYYY-MM-DD" string.
            end_date: End of date range. Accepts datetime.date or "YYYY-MM-DD" string.
            new_awards_only: If True, only includes awards that started in the period.
            date_type: The date field to filter on (case-insensitive).

        Valid Date Types:
            "action_date" (default): The date the action (transaction) occurred.
                Most common choice for spending analysis.
            "date_signed": The date the award was signed/executed.
                Useful for tracking when commitments were made.
            "last_modified_date": When the record was last updated.
                Useful for finding recently changed records.
            "new_awards_only": Only awards that originated in the period.
                Equivalent to setting new_awards_only=True.

        Validation Rules:
            - Minimum date: 2007-10-01 (start of FY2008)
            - USASpending.gov data begins with FY2008
            - String dates must be in YYYY-MM-DD format
            - Dates before the minimum raise ValidationError

        Returns:
            T: A new instance with the time period filter applied.

        Raises:
            ValidationError: If date format is invalid or date is before 2007-10-01.

        Example:
            >>> # Find all contracts from 2023
            >>> contracts_2023 = (
            ...     client.awards.search().contracts().time_period("2023-01-01", "2023-12-31")
            ... )

            >>> # Find NEW grants started in Q1 2024
            >>> new_grants = (
            ...     client.awards.search()
            ...     .grants()
            ...     .time_period("2024-01-01", "2024-03-31", new_awards_only=True)
            ... )

            >>> # Find awards by signature date
            >>> signed_2024 = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .time_period("2024-01-01", "2024-12-31", date_type="date_signed")
            ... )

            >>> # Find recently modified records
            >>> recent_changes = (
            ...     client.awards.search()
            ...     .grants()
            ...     .time_period("2024-11-01", "2024-12-31", date_type="last_modified_date")
            ... )

        Note:
            For subaward searches, only "action_date" and "last_modified_date"
            are supported. See SubAwardsSearch.time_period() for details.
        """
        # Parse each bound and hold it to the API's floor, then check the range.
        start_date = parse_api_date(start_date, "start_date")
        end_date = parse_api_date(end_date, "end_date")
        validate_date_range(start_date, end_date)

        # Convert string date_type to enum if needed
        date_type_enum = None
        if date_type is not None:
            date_type_enum = parse_award_date_type(date_type)

        # If convenience flag is set, use NEW_AWARDS_ONLY date type
        # and override any provided date_type
        if new_awards_only:
            date_type_enum = AwardDateType.NEW_AWARDS_ONLY

        return self._with_filter(
            TimePeriodFilter(start_date=start_date, end_date=end_date, date_type=date_type_enum)
        )

    def fiscal_year(
        self: SQB,
        year: int,
        new_awards_only: bool = False,
        date_type: str | None = None,
    ) -> SQB:
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
            >>> fy2024_contracts = client.awards.search().contracts().fiscal_year(2024)

            >>> # Get only NEW grants started in FY2023
            >>> new_fy2023_grants = (
            ...     client.awards.search().grants().fiscal_year(2023, new_awards_only=True)
            ... )
        """
        # Validate fiscal year (must be >= 2008, earliest supported by USASpending.gov)
        year = parse_fiscal_year(year)

        # A fiscal year is negatively offset to the calendar year by 3 months. For example,
        # FY 2024 ran from October 1, 2023 to September 30, 2024.
        start_date = datetime.date(year - 1, 10, 1)
        end_date = datetime.date(year, 9, 30)

        return self.time_period(
            start_date=start_date,
            end_date=end_date,
            new_awards_only=new_awards_only,
            date_type=date_type,
        )

    def _add_scope_filter(self: SQB, key: str, scope: str) -> SQB:
        """Add a location scope filter (domestic/foreign).

        Args:
            key: The filter key (e.g., "place_of_performance_scope").
            scope: Either "domestic" or "foreign".

        Returns:
            A new instance with the scope filter applied.
        """
        location_scope = parse_location_scope(scope)
        return self._with_filter(LocationScopeFilter(key=key, scope=location_scope))

    def _add_location_filter(self: SQB, key: str, locations: tuple[dict, ...]) -> SQB:
        """Add a location filter with parsed LocationSpec objects.

        Args:
            key: The filter key (e.g., "place_of_performance_locations").
            locations: Location specification dictionaries.

        Returns:
            A new instance with the location filter applied.
        """
        location_specs = [parse_location_spec(loc) for loc in locations]
        return self._with_filter(LocationFilter(key=key, locations=location_specs))

    def place_of_performance_scope(self: SQB, scope: str) -> SQB:
        """
        Filter by domestic or foreign place of performance.

        Args:
            scope: Either "domestic" or "foreign" (case-insensitive).

        Returns:
            A new instance with the location scope filter applied.

        Raises:
            ValidationError: If scope is not "domestic" or "foreign".

        Example:
            >>> foreign_aid = client.awards.search().grants().place_of_performance_scope("foreign")
        """
        return self._add_scope_filter("place_of_performance_scope", scope)

    def place_of_performance_locations(self: SQB, *locations: dict[str, str]) -> SQB:
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
        return self._add_location_filter("place_of_performance_locations", locations)

    def recipient_scope(self: SQB, scope: str) -> SQB:
        """
        Filter by domestic or foreign recipient location.

        Args:
            scope: Either "domestic" or "foreign" (case-insensitive).

        Returns:
            A new instance with the recipient scope filter applied.

        Raises:
            ValidationError: If scope is not "domestic" or "foreign".

        Example:
            >>> foreign_contracts = client.awards.search().contracts().recipient_scope("foreign")
        """
        return self._add_scope_filter("recipient_scope", scope)

    def recipient_locations(self: SQB, *locations: dict[str, str]) -> SQB:
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
            ...     .recipient_locations({"state_code": "CA", "country_code": "USA"})
            ... )
        """
        return self._add_location_filter("recipient_locations", locations)

    # ==========================================================================
    # Groups 3-6: Agency, Award, Code Filters, and Convenience Methods
    # ==========================================================================

    def agencies(self: SQB, *agencies: dict[str, str]) -> SQB:
        """
        Filter awards by one or more awarding or funding agencies.

        Args:
            *agencies: Agency specification dictionaries with required and optional fields.

        Required Fields:
            name (str): The agency name. Must match exactly (case-insensitive).
                Examples: "Department of Defense", "Small Business Administration"

            type (str): Whether this is the awarding or funding agency.
                "awarding": The agency that manages/administers the award
                "funding": The agency that provides the money (may differ from awarding)

            tier (str): The organizational level.
                "toptier": Top-level department (e.g., "Department of Defense")
                "subtier": Sub-agency or office (e.g., "Army", "Defense Logistics Agency")

        Optional Fields:
            toptier_name (str): Parent agency name to disambiguate subtiers.
                Required when the subtier name exists under multiple toptiers.
                Example: "Office of Inspector General" exists in many departments.

        Returns:
            T: A new instance with the agency filter applied.

        Raises:
            ValidationError: If required fields (name, type, tier) are missing
                or contain invalid values.

        Common Agency Combinations:
            Top-tier Awarding: Find who is managing the award
                {"name": "Department of Defense", "type": "awarding", "tier": "toptier"}

            Top-tier Funding: Find who is paying for the award
                {"name": "Department of Energy", "type": "funding", "tier": "toptier"}

            Subtier with Parent: Disambiguate common subtier names
                {"name": "Office of Inspector General", "type": "awarding",
                 "tier": "subtier", "toptier_name": "Department of Defense"}

        Example:
            >>> # Find DOD and NASA contracts
            >>> multi_agency = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .agencies(
            ...         {"name": "Department of Defense", "type": "awarding", "tier": "toptier"},
            ...         {
            ...             "name": "National Aeronautics and Space Administration",
            ...             "type": "awarding",
            ...             "tier": "toptier",
            ...         },
            ...     )
            ... )

            >>> # Find awards funded by Department of Energy but managed by other agencies
            >>> doe_funded = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .agencies(
            ...         {"name": "Department of Energy", "type": "funding", "tier": "toptier"}
            ...     )
            ... )

            >>> # Find specific subtier with disambiguation
            >>> army_awards = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .agencies(
            ...         {
            ...             "name": "Department of the Army",
            ...             "type": "awarding",
            ...             "tier": "subtier",
            ...             "toptier_name": "Department of Defense",
            ...         }
            ...     )
            ... )

        Note:
            Multiple agencies use OR logic. An award matches if it involves
            any of the specified agencies.
        """

        # Parse each agency dict into AgencySpec objects
        agency_specs = [parse_agency_spec(agency) for agency in agencies]

        return self._with_filter(AgencyFilter(agencies=agency_specs))

    def agency(
        self: SQB,
        name: str,
        agency_type: str = "awarding",
        tier: str = "toptier",
        toptier_name: str | None = None,
    ) -> SQB:
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

    def recipient_search_text(self: SQB, search_term: str) -> SQB:
        """
        Search for awards by recipient name, UEI, or DUNS.

        This performs a text search across recipient identifiers and names.
        Per API documentation, only a single search term is supported.

        Args:
            search_term: Text to search for across recipient name,
                UEI (Unique Entity Identifier), and DUNS number fields.

        Returns:
            T: A new instance with the recipient search filter applied.

        Raises:
            ValidationError: If search_term is empty.

        Example:
            >>> # Search by company name
            >>> lockheed_awards = (
            ...     client.awards.search().contracts().recipient_search_text("Lockheed Martin")
            ... )

            >>> # Search by UEI
            >>> specific_recipient = (
            ...     client.awards.search()
            ...     .award_type_codes("A", "B")
            ...     .recipient_search_text("ABCD1234567890")
            ... )
        """
        validated_term = validate_non_empty_string(search_term, "recipient_search_text")

        return self._with_filter(
            SimpleListFilter(key="recipient_search_text", values=[validated_term])
        )

    def recipient_type_names(self: SQB, *type_names: str) -> SQB:
        """
        Filter awards by recipient or business types.

        Args:
            *type_names: One or more recipient type names (case-sensitive).

        Valid Recipient Types:
            Small Business Types:
                "small_business": Small Business
                "other_than_small_business": Other Than Small Business
                "category_business": Category Business

            Socioeconomic Business Types:
                "woman_owned_business": Woman-Owned Business
                "sba_certified_8a_program_participant": 8(a) Program Participant
                "historically_underutilized_business_firm": HUBZone Firm
                "service_disabled_veteran_owned_business": SDVOSB
                "women_owned_small_business": Women-Owned Small Business
                "economically_disadvantaged_women_owned_small_business": EDWOSB
                "joint_venture_women_owned_small_business": Joint Venture WOSB
                "joint_venture_economically_disadvantaged_women_owned_small_bus": JV EDWOSB
                "veteran_owned_business": Veteran-Owned Business
                "minority_owned_business": Minority-Owned Business
                "subcontinent_asian_indian_american_owned": Subcontinent Asian Indian American Owned
                "asian_pacific_american_owned_business": Asian Pacific American Owned
                "black_american_owned_business": Black American Owned
                "hispanic_american_owned_business": Hispanic American Owned
                "native_american_owned_business": Native American Owned
                "other_minority_owned_business": Other Minority Owned

            Entity Types:
                "corporate_entity_not_tax_exempt": Corporate Entity (Not Tax Exempt)
                "corporate_entity_tax_exempt": Corporate Entity (Tax Exempt)
                "partnership_or_limited_liability_partnership": Partnership/LLP
                "sole_proprietorship": Sole Proprietorship
                "limited_liability_corporation": LLC
                "subchapter_s_corporation": Subchapter S Corporation

            Government Entities:
                "government": Government
                "us_state_government": U.S. State Government
                "county_local_government": County/Local Government
                "city_local_government": City Government
                "township_local_government": Township Government
                "municipality_local_government": Municipality
                "us_federal_government": U.S. Federal Government
                "indian_tribe_federally_recognized": Federally Recognized Tribal Government
                "foreign_government": Foreign Government
                "regional_and_state_government": Regional/State Government

            Nonprofit & Educational:
                "nonprofit": Nonprofit Organization
                "higher_education": Higher Education Institution
                "private_university_or_college": Private University/College
                "state_controlled_institution_of_higher_learning": State College
                "hospital": Hospital
                "foundation": Foundation

            Other Types:
                "individual": Individual
                "foreign_entity": Foreign Entity
                "for_profit_organization": For-Profit Organization
                "other_nonprofit": Other Nonprofit
                "other": Other

        Returns:
            T: A new instance with the recipient type filter applied.

        Note:
            Multiple types use OR logic (matches any specified type).
            Type names are case-sensitive and use underscores.

        Example:
            >>> # Find contracts awarded to small businesses
            >>> small_biz = (
            ...     client.awards.search().contracts().recipient_type_names("small_business")
            ... )

            >>> # Find grants to universities and nonprofits
            >>> education = (
            ...     client.awards.search()
            ...     .grants()
            ...     .recipient_type_names("higher_education", "nonprofit")
            ... )

            >>> # Find veteran-owned business contracts
            >>> veteran = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .recipient_type_names(
            ...         "veteran_owned_business", "service_disabled_veteran_owned_business"
            ...     )
            ... )
        """
        return self._with_filter(
            SimpleListFilter(key="recipient_type_names", values=list(type_names))
        )

    def award_ids(self: SQB, *award_ids: str) -> SQB:
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
            >>> specific_grant = client.awards.search().grants().award_ids("1234567890ABCD")
        """
        return self._with_filter(SimpleListFilter(key="award_ids", values=list(award_ids)))

    def award_amounts(
        self: SQB, *amounts: dict[str, float] | tuple[float | None, float | None]
    ) -> SQB:
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
            ...     .award_amounts({"lower_bound": 1000000, "upper_bound": 10000000})
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
            ...     .award_amounts({"upper_bound": 100000}, {"lower_bound": 1000000})
            ... )
        """
        # Convert various input formats to AwardAmount objects
        award_amounts = [parse_award_amount(amt) for amt in amounts]

        return self._with_filter(AwardAmountFilter(amounts=award_amounts))

    def award_type_codes(self: SQB, *award_codes: str) -> SQB:
        """
        Filter by one or more award type codes.

        **This filter is required** - the API requires at least one award type code.

        Args:
            *award_codes: One or more award type codes from the categories below.

        Valid Award Type Codes:
            Contracts (Procurement):
                "A": BPA Call
                "B": Purchase Order
                "C": Delivery Order
                "D": Definitive Contract

            Indefinite Delivery Vehicles (IDVs):
                "IDV_A": GWAC (Government-Wide Acquisition Contract)
                "IDV_B": IDC (Indefinite Delivery Contract)
                "IDV_B_A": IDC / Requirements
                "IDV_B_B": IDC / Indefinite Quantity
                "IDV_B_C": IDC / Definite Quantity
                "IDV_C": FSS (Federal Supply Schedule)
                "IDV_D": BOA (Basic Ordering Agreement)
                "IDV_E": BPA (Blanket Purchase Agreement)

            Grants (Assistance):
                "02": Block Grant
                "03": Formula Grant
                "04": Project Grant
                "05": Cooperative Agreement

            Loans:
                "07": Direct Loan
                "08": Guaranteed/Insured Loan

            Direct Payments:
                "06": Direct Payment for Specified Use
                "10": Direct Payment with Unrestricted Use

            Other Financial Assistance:
                "09": Insurance
                "11": Other Financial Assistance
                "-1": Not Specified (unknown/legacy data)

        Returns:
            T: A new instance with the award type filter applied.

        Note:
            AwardsSearch overrides this method to add validation that prevents
            mixing different award type categories (e.g., contracts and grants).
            This is because different award types have different available fields
            and filtering options.

        Example:
            >>> # Search for specific contract types
            >>> contracts = client.awards.search().award_type_codes("A", "B", "C", "D")

            >>> # Search for grants only
            >>> grants = client.awards.search().award_type_codes("02", "03", "04", "05")

        Reference:
            https://api.usaspending.gov/api/v2/references/filter_tree/psc/
        """
        return self._with_filter(SimpleListFilter(key="award_type_codes", values=list(award_codes)))

    def contracts(self: SQB) -> SQB:
        """
        Filter to search for contract awards only.

        This is a convenience method that applies award type codes A, B, C, D.

        Returns:
            T: A new instance configured for contract awards.

        Example:
            >>> # Search for all contracts in FY2024
            >>> fy2024_contracts = client.awards.search().contracts().fiscal_year(2024)
        """
        return self.award_type_codes(*CONTRACT_CODES)

    def idvs(self: SQB) -> SQB:
        """
        Filter to search for Indefinite Delivery Vehicle (IDV) awards only.

        IDVs are contract vehicles that provide for an indefinite quantity
        of supplies or services. This method applies all IDV type codes.

        Returns:
            T: A new instance configured for IDV awards.

        Example:
            >>> # Search for all IDVs from Department of Defense
            >>> dod_idvs = client.awards.search().idvs().agency("Department of Defense")
        """
        return self.award_type_codes(*IDV_CODES)

    def loans(self: SQB) -> SQB:
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

    def grants(self: SQB) -> SQB:
        """
        Filter to search for grant awards only.

        This applies award type codes 02, 03, 04, 05 for various grant types.

        Returns:
            T: A new instance configured for grant awards.

        Example:
            >>> # Search for education grants
            >>> education_grants = (
            ...     client.awards.search().grants().fiscal_year(2024).keywords("STEM", "research")
            ... )
        """
        return self.award_type_codes(*GRANT_CODES)

    def direct_payments(self: SQB) -> SQB:
        """
        Filter to search for direct payment awards only.

        Direct payments include benefits to individuals and other direct
        assistance. This applies award type codes 06 and 10.

        Returns:
            T: A new instance configured for direct payment awards.

        Example:
            >>> # Search for social security direct payments
            >>> ss_payments = client.awards.search().direct_payments().fiscal_year(2024)
        """
        return self.award_type_codes(*DIRECT_PAYMENT_CODES)

    def other_assistance(self: SQB) -> SQB:
        """
        Filter to search for other assistance awards.

        This includes insurance programs and other miscellaneous assistance.
        Applies award type codes 09, 11, and -1.

        Returns:
            T: A new instance configured for other assistance awards.

        Example:
            >>> # Search for insurance and other assistance programs
            >>> other_assistance = client.awards.search().other_assistance().fiscal_year(2024)
        """
        return self.award_type_codes(*OTHER_CODES)

    def program_numbers(self: SQB, *program_numbers: str) -> SQB:
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
            >>> pell_grants = client.awards.search().grants().program_numbers("84.063")

            >>> # Find multiple agriculture programs
            >>> ag_programs = (
            ...     client.awards.search().grants().program_numbers("10.001", "10.310", "10.902")
            ... )
        """
        return self._with_filter(
            SimpleListFilter(key="program_numbers", values=list(program_numbers))
        )

    def naics_codes(
        self: SQB,
        require: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> SQB:
        """
        Filter by North American Industry Classification System (NAICS) codes.

        NAICS codes classify business establishments for statistical purposes.
        The API uses **prefix matching**, so code "33" matches all codes starting
        with "33" (e.g., 331110, 332710, 333999).

        Args:
            require: NAICS code prefixes to include (matches if starts with).
            exclude: NAICS code prefixes to exclude from results.

        NAICS Code Structure:
            2-digit: Sector (broadest classification)
            3-digit: Subsector
            4-digit: Industry Group
            5-digit: NAICS Industry
            6-digit: National Industry (most specific)

        Common NAICS Sectors:
            "11": Agriculture, Forestry, Fishing and Hunting
            "21": Mining, Quarrying, and Oil/Gas Extraction
            "22": Utilities
            "23": Construction
            "31-33": Manufacturing
                "31": Food, Beverage, Tobacco, Textiles
                "32": Wood, Paper, Petroleum, Chemicals, Plastics
                "33": Metals, Machinery, Electronics, Transportation
            "42": Wholesale Trade
            "44-45": Retail Trade
            "48-49": Transportation and Warehousing
            "51": Information (Publishing, Broadcasting, Telecom, IT)
            "52": Finance and Insurance
            "53": Real Estate and Rental/Leasing
            "54": Professional, Scientific, and Technical Services
            "55": Management of Companies
            "56": Administrative, Support, Waste Management
            "61": Educational Services
            "62": Health Care and Social Assistance
            "71": Arts, Entertainment, and Recreation
            "72": Accommodation and Food Services
            "81": Other Services (Repair, Personal, Religious)
            "92": Public Administration

        Returns:
            T: A new instance with the NAICS filter applied.

        Note:
            Use prefix matching strategically - "54" matches all professional
            services (541110 Legal, 541330 Engineering, 541511 Custom Programming).

        Example:
            >>> # Find all IT services contracts
            >>> it_services = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .naics_codes(require=["5415"])  # Computer Systems Design
            ... )

            >>> # Find manufacturing, excluding chemicals
            >>> manufacturing = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .naics_codes(
            ...         require=["31", "32", "33"],
            ...         exclude=["325"],  # Exclude Chemical Manufacturing
            ...     )
            ... )

            >>> # Find aerospace manufacturing specifically
            >>> aerospace = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .naics_codes(require=["336411", "336412", "336413"])
            ... )

        Reference:
            U.S. Census Bureau NAICS Codes
            https://www.census.gov/naics/
        """
        return self._with_filter(
            NAICSFilter(
                require=list(require) if require else [],
                exclude=list(exclude) if exclude else [],
            )
        )

    def psc_codes(
        self: SQB,
        *codes: str,
        require: list[list[str]] | None = None,
        exclude: list[list[str]] | None = None,
    ) -> SQB:
        """
        Filter by Product and Service Codes (PSC).

        PSCs describe what the government is buying. Supports two formats:
        1. **Simple format**: Pass codes directly as string arguments
        2. **Hierarchical format**: Use require/exclude with nested path lists

        Args:
            *codes: PSC codes for exact matching (e.g., "1510", "D302").
            require: PSC code paths to include (hierarchical format).
            exclude: PSC code paths to exclude (hierarchical format).

        PSC Code Structure:
            Products (4-digit numeric codes starting with digits):
                10-19: Weapons & Ammunition
                20-29: Ships, Small Craft, and Pontoons
                30-39: Mechanized Equipment and Vehicles
                40-49: Electronics and Electrical Equipment
                50-59: Clothing, Textiles, and Subsistence
                60-69: Materials, Instruments, and Supplies
                70-79: General Equipment
                80-89: Containers, Packaging, and Packing
                90-99: Non-Metallic Crude Materials

            Services (Codes starting with letters):
                A: Research and Development
                B: Special Studies and Analysis
                C: Architect and Engineering Services
                D: IT and Telecommunications Services
                    D3: IT and Telecom - Software Development
                    D301: IT and Telecom - Facility Operation
                    D302: IT and Telecom - Systems Development
                E: Purchase of Structures and Facilities
                F: Natural Resources and Conservation
                G: Social Services
                H: Quality Control, Testing, and Inspection
                J: Maintenance, Repair, and Rebuilding of Equipment
                K: Modification of Equipment
                L: Technical Representative Services
                M: Operation of Government-Owned Facilities
                N: Installation of Equipment
                P: Salvage Services
                Q: Medical Services
                R: Professional, Administrative, and Management Support
                    R4: Program Management/Support
                    R7: Administrative Support
                S: Utilities and Housekeeping Services
                T: Photographic, Mapping, and Publishing Services
                U: Education and Training Services
                V: Transportation, Travel, and Relocation Services
                W: Lease or Rental of Equipment
                Y: Construction of Structures and Facilities
                Z: Maintenance, Repair, or Alteration of Real Property

        Hierarchical Format:
            Use nested lists representing the PSC tree path:
            - ["Product", "15"] - All products in FSC 15 (Aircraft)
            - ["Service", "D"] - All IT/Telecom services
            - ["Service", "D", "D3"] - IT Software services specifically

        Returns:
            T: A new instance with the PSC filter applied.

        Raises:
            ValidationError: If both simple codes and require/exclude are used.

        Example:
            >>> # Simple format - specific codes
            >>> aircraft = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .psc_codes("1510", "1520", "1560")  # Aircraft and components
            ... )

            >>> # Hierarchical - all IT services
            >>> it_services = (
            ...     client.awards.search().contracts().psc_codes(require=[["Service", "D"]])
            ... )

            >>> # R&D services, excluding medical research
            >>> research = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .psc_codes(
            ...         require=[["Service", "A"]],
            ...         exclude=[["Service", "A", "AN"]],  # Exclude medical R&D
            ...     )
            ... )

        Reference:
            GSA PSC Manual
            https://www.acquisition.gov/psc-manual
        """
        # Validate that user doesn't mix formats
        if codes and (require or exclude):
            raise ValidationError(
                "Cannot mix simple PSC codes with require/exclude format. "
                "Use either psc_codes('1510', '1520') or psc_codes(require=[...], exclude=[...])."
            )

        return self._with_filter(
            PSCFilter(
                codes=list(codes) if codes else [],
                require=require or [],
                exclude=exclude or [],
            )
        )

    def contract_pricing_type_codes(self: SQB, *type_codes: str) -> SQB:
        """
        Filter contracts by pricing type (FAR Part 16).

        Pricing types define how the contractor is compensated - fixed-price
        contracts shift risk to the contractor, while cost-reimbursement
        contracts shift risk to the government.

        Args:
            *type_codes: One or more contract pricing type codes.

        Valid Pricing Type Codes:
            Fixed-Price Contracts:
                "A": Fixed Price Redetermination
                "B": Fixed Price Level of Effort
                "J": Firm Fixed Price
                "K": Fixed Price with Economic Price Adjustment
                "L": Fixed Price Incentive
                "M": Fixed Price Award Fee

            Cost-Reimbursement Contracts:
                "R": Cost Plus Award Fee
                "S": Cost No Fee
                "T": Cost Sharing
                "U": Cost Plus Fixed Fee
                "V": Cost Plus Incentive Fee

            Time and Materials / Labor Hour:
                "Y": Time and Materials
                "Z": Labor Hours

            Other:
                "1": Order Dependent (for IDVs - pricing varies by order)
                "2": Combination (multiple pricing types)
                "3": Other

        Returns:
            T: A new instance with the pricing type filter applied.

        Note:
            This filter applies only to contract awards (types A, B, C, D
            and IDVs). It has no effect on grants, loans, or other assistance.

        Example:
            >>> # Find firm fixed price contracts
            >>> fixed_price = client.awards.search().contracts().contract_pricing_type_codes("J")

            >>> # Find cost-reimbursement contracts
            >>> cost_plus = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .contract_pricing_type_codes("R", "S", "T", "U", "V")
            ... )

        Reference:
            FAR Part 16 - Types of Contracts
            https://www.acquisition.gov/far/part-16
        """
        return self._with_filter(
            SimpleListFilter(key="contract_pricing_type_codes", values=list(type_codes))
        )

    def set_aside_type_codes(self: SQB, *type_codes: str) -> SQB:
        """
        Filter contracts by set-aside type.

        Set-asides reserve contracts for specific types of businesses
        (e.g., small businesses, minority-owned, veteran-owned).

        Args:
            *type_codes: One or more set-aside type codes.

        Valid Set-Aside Codes:
            No Set-Aside:
                "NONE": No Set-Aside Used

            Small Business Programs:
                "SBA": Small Business Set-Aside - Total
                "SBP": Small Business Set-Aside - Partial

            8(a) Business Development Program:
                "8A": 8(a) Competed
                "8AN": 8(a) Sole Source

            HUBZone Program:
                "HZC": HUBZone Set-Aside
                "HZS": HUBZone Sole Source

            Service-Disabled Veteran-Owned Small Business (SDVOSB):
                "SDVOSBC": SDVOSB Set-Aside
                "SDVOSBS": SDVOSB Sole Source

            Women-Owned Small Business (WOSB):
                "WOSB": WOSB Set-Aside
                "WOSBSS": WOSB Sole Source
                "EDWOSB": Economically Disadvantaged WOSB Set-Aside
                "EDWOSBSS": Economically Disadvantaged WOSB Sole Source

            Veteran-Owned Small Business:
                "VSA": Veteran-Owned Small Business Set-Aside
                "VSS": Veteran-Owned Small Business Sole Source

            Other:
                "IEE": Indian Economic Enterprise
                "ISBEE": Indian Small Business Economic Enterprise
                "RSB": Emerging Small Business Set-Aside
                "HS2": Combined HUBZone/8(a)
                "HS3": HUBZone/Small Business Set-Aside

        Returns:
            T: A new instance with the set-aside filter applied.

        Note:
            This filter applies only to contract awards. Multiple codes use
            OR logic (matches any specified set-aside type).

        Example:
            >>> # Find small business set-aside contracts
            >>> small_biz = client.awards.search().contracts().set_aside_type_codes("SBA", "SBP")

            >>> # Find veteran-owned business contracts
            >>> veteran_owned = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .set_aside_type_codes("SDVOSBC", "SDVOSBS", "VSA", "VSS")
            ... )

        Reference:
            FAR Part 19 - Small Business Programs
            https://www.acquisition.gov/far/part-19
        """
        return self._with_filter(
            SimpleListFilter(key="set_aside_type_codes", values=list(type_codes))
        )

    def extent_competed_type_codes(self: SQB, *type_codes: str) -> SQB:
        """
        Filter contracts by extent of competition.

        Indicates how much competition was involved in awarding the contract,
        ranging from full and open competition to sole source awards.

        Args:
            *type_codes: One or more extent competed type codes.

        Valid Competition Codes:
            Full Competition:
                "A": Full and Open Competition
                "D": Full and Open Competition after Exclusion of Sources
                "E": Follow On to Competed Action
                "F": Competed under SAP (Simplified Acquisition Procedures)

            Limited Competition:
                "B": Not Available for Competition
                "C": Not Competed
                "G": Not Competed under SAP

            Delivery/Task Orders:
                "CDO": Competitive Delivery Order
                "NDO": Non-Competitive Delivery Order

        Returns:
            T: A new instance with the competition filter applied.

        Note:
            This filter applies only to contract awards. It helps identify
            whether awards were competitively bid or sole-sourced.

        Example:
            >>> # Find fully competed contracts only
            >>> competed = client.awards.search().contracts().extent_competed_type_codes("A", "D")

            >>> # Find sole source / non-competed contracts
            >>> sole_source = (
            ...     client.awards.search().contracts().extent_competed_type_codes("B", "C", "NDO")
            ... )

        Reference:
            FAR Part 6 - Competition Requirements
            https://www.acquisition.gov/far/part-6
        """
        return self._with_filter(
            SimpleListFilter(key="extent_competed_type_codes", values=list(type_codes))
        )

    def tas_codes(
        self: SQB,
        require: list[list[str]] | None = None,
        exclude: list[list[str]] | None = None,
    ) -> SQB:
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
            ...     client.awards.search().contracts().tas_codes(require=[["091"], ["097"]])
            ... )
        """
        return self._with_filter(
            TieredCodeFilter(
                key="tas_codes",
                require=require or [],
                exclude=exclude or [],
            )
        )

    def treasury_account_components(self: SQB, *components: dict[str, str]) -> SQB:
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
            ...         {"aid": "097", "main": "0100"}, {"aid": "012", "main": "3500"}
            ...     )
            ... )
        """
        return self._with_filter(TreasuryAccountComponentsFilter(components=list(components)))

    def def_codes(self: SQB, *def_codes: str) -> SQB:
        """
        Filter by Disaster Emergency Fund (DEF) codes.

        DEF codes identify awards funded through specific disaster or emergency
        appropriations legislation. Use this to find COVID-19 relief spending,
        infrastructure investments, and other emergency funding.

        Args:
            *def_codes: One or more DEF codes.

        Valid DEF Codes:
            COVID-19 Relief (2020-2021):
                "L": Coronavirus Preparedness and Response Supplemental
                     (P.L. 116-123, March 2020)
                "M": Families First Coronavirus Response Act
                     (P.L. 116-127, March 2020)
                "N": CARES Act - Coronavirus Aid, Relief, and Economic Security
                     (P.L. 116-136, March 2020)
                "O": Paycheck Protection Program and Health Care Enhancement
                     (P.L. 116-139, April 2020)
                "P": Coronavirus Response and Relief Supplemental
                     (P.L. 116-260, December 2020)
                "U": American Rescue Plan Act
                     (P.L. 117-2, March 2021)

            Infrastructure (2021+):
                "Z": Infrastructure Investment and Jobs Act (IIJA)
                     (P.L. 117-58, November 2021)

            Inflation Reduction Act (2022+):
                "1": IRA - Climate and Energy (P.L. 117-169)
                "2": IRA - Healthcare (P.L. 117-169)

            Legacy Disaster Codes:
                "A": Disaster Relief - General
                "B": Disaster Relief (Hurricane Sandy, etc.)
                "C": Disaster Relief (legacy)
                "D": Disaster Relief (legacy)

        Returns:
            T: A new instance with the DEF code filter applied.

        Note:
            Multiple codes use OR logic (matches any specified code).
            DEF codes are assigned at the transaction level, so awards may
            have multiple funding sources with different DEF codes.

        Example:
            >>> # Find all COVID-19 relief spending
            >>> covid = client.awards.search().contracts().def_codes("L", "M", "N", "O", "P", "U")

            >>> # Find Infrastructure Investment and Jobs Act awards
            >>> infrastructure = client.awards.search().contracts().def_codes("Z")

            >>> # Find Inflation Reduction Act climate investments
            >>> ira_climate = client.awards.search().grants().def_codes("1")

        Reference:
            USASpending.gov COVID-19 Spending Profile
            https://www.usaspending.gov/disaster/covid-19
        """
        return self._with_filter(SimpleListFilter(key="def_codes", values=list(def_codes)))

    def description(self: SQB, text: str) -> SQB:
        """
        Filter awards by description text.

        Unlike keywords(), this filter specifically searches the award
        description field only, rather than multiple text fields.

        Args:
            text: The text to search for in award descriptions.

        Returns:
            T: A new instance with the description filter applied.

        Example:
            >>> # Find contracts with "climate" in description
            >>> climate_contracts = (
            ...     client.awards.search().contracts().description("climate change research")
            ... )
        """
        validated_text = validate_non_empty_string(text, "description")

        return self._with_filter(SimpleStringFilter(key="description", value=validated_text))

    def program_activity(self: SQB, *activity_codes: int) -> SQB:
        """
        Filter by program activity codes (deprecated).

        .. deprecated::
            Use :meth:`program_activities` instead. The USASpending API removed the
            ``program_activity`` filter in favor of ``program_activities``. This method
            now forwards to ``program_activities`` (sending each code as a string) and
            will be removed in a future release. Note that the forwarded codes are not
            zero-padded; use :meth:`program_activities` directly for full control.

        Program activity codes are numeric identifiers that categorize
        federal programs for budgeting and reporting purposes.

        Args:
            *activity_codes: One or more program activity codes as integers.

        Returns:
            T: A new instance with the program activities filter applied.

        Raises:
            ValidationError: If no codes are provided or any code is not an integer.

        Example:
            >>> # Prefer program_activities(); this still works but emits a warning:
            >>> programs = client.awards.search().grants().program_activity(1, 2, 3)
        """
        if not activity_codes:
            raise ValidationError("At least one program activity code is required")

        # Validate all codes are integers
        for code in activity_codes:
            if not isinstance(code, int):
                raise ValidationError(
                    f"Program activity codes must be integers, got {type(code).__name__}"
                )

        warnings.warn(
            "program_activity is deprecated. Use program_activities() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # The API now expects program_activities objects with string codes.
        return self.program_activities(*[{"code": str(code)} for code in activity_codes])

    def program_activities(
        self: SQB,
        *activities: dict[str, str],
    ) -> SQB:
        """
        Filter by program activities using name or code.

        This filter allows searching by program activity name, code, or both.
        Each activity specification must include at least a name or code.

        Args:
            *activities: One or more activity specifications as dictionaries.
                Each dictionary can contain:
                - name: The program activity name (optional if code provided)
                - code: The program activity code (optional if name provided)

        Returns:
            T: A new instance with the program activities filter applied.

        Raises:
            ValidationError: If an activity has neither name nor code.

        Example:
            >>> # Filter by specific program activities
            >>> programs = (
            ...     client.awards.search()
            ...     .grants()
            ...     .program_activities({"name": "Research and Development"}, {"code": "0001"})
            ... )
        """
        if not activities:
            raise ValidationError("At least one program activity is required")

        # Validate each activity has at least name or code
        for activity in activities:
            if "name" not in activity and "code" not in activity:
                raise ValidationError(
                    "Each program activity must have at least a 'name' or 'code' field"
                )

        return self._with_filter(
            SimpleListFilter(key="program_activities", values=list(activities))
        )
