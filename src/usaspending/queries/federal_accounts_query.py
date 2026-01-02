"""FederalAccountsQuery - Lazy query for Federal Accounts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..logging_config import USASpendingLogger
from ..utils.validations import validate_non_empty_string
from .client_side_query_builder import ClientSideQueryBuilder
from .filters import KeywordsFilter, SimpleListFilter, SimpleStringFilter

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.federal_account import FederalAccount

logger = USASpendingLogger.get_logger(__name__)


class FederalAccountsQuery(ClientSideQueryBuilder["FederalAccount"]):
    """Lazy query for Federal Accounts with TAS codes.

    Provides a query-like interface for fetching federal accounts under
    an agency. Supports iteration, indexing, count operations, and
    client-side filtering.

    The query is lazily evaluated - the API is only called when results
    are actually accessed (iteration, indexing, count, etc.).

    Filters:
        - code(): Filter by federal account code.
        - codes(): Filter by multiple federal account codes.
        - description(): Filter by description text (case-insensitive substring).
        - account_name(): Alias for description().
        - fiscal_year(): Filter by fiscal year coverage.

    Example:
        >>> accounts = agency.federal_accounts
        >>> len(accounts)  # Fetches and returns count
        16
        >>> accounts.count()  # Same as len()
        16
        >>> for account in accounts:
        ...     print(account.id, account.title)
        >>> first_account = accounts.first()
        >>> all_accounts = accounts.all()
    """

    ENDPOINT = "/references/filter_tree/tas/{toptier_code}/"

    def __init__(
        self,
        client: USASpendingClient,
        toptier_code: str,
    ):
        """Initialize FederalAccountsQuery.

        Args:
            client: USASpendingClient instance.
            toptier_code: Agency toptier code (e.g., "080").
        """
        self._client = client
        self._toptier_code = toptier_code
        self._results: list[FederalAccount] | None = None
        super().__init__(
            items=[],
            keyword_fields=["description", "name", "title"],
        )

    def _fetch(self) -> list[FederalAccount]:
        """Fetch federal accounts from the API.

        Returns:
            List of FederalAccount model instances.
        """
        if self._results is not None:
            return self._results

        # Handle empty toptier_code
        if not self._toptier_code:
            self._results = []
            return self._results

        endpoint = self.ENDPOINT.format(toptier_code=self._toptier_code)

        logger.debug("Fetching federal accounts for agency %s", self._toptier_code)

        response = self._client._make_request("GET", endpoint)
        results = response.get("results", [])

        from ..models.federal_account import FederalAccount

        self._results = [
            FederalAccount(data, self._client, toptier_code=self._toptier_code)
            for data in results
            if isinstance(data, dict)
        ]

        logger.debug("Fetched %d federal accounts", len(self._results))

        return self._results

    def _materialize(self) -> list[FederalAccount]:
        """Return fetched federal accounts for client-side filtering."""
        return list(self._fetch())

    def code(self, code: str) -> FederalAccountsQuery:
        """Filter by federal account code.

        Args:
            code: Federal account code (e.g., "080-0120").

        Returns:
            FederalAccountsQuery: Filtered query.
        """
        validated = validate_non_empty_string(code, "code")
        return self._add_filter_object(SimpleStringFilter(key="id", value=validated))

    def codes(self, *codes: str) -> FederalAccountsQuery:
        """Filter by multiple federal account codes.

        Args:
            *codes: One or more federal account codes.

        Returns:
            FederalAccountsQuery: Filtered query.
        """
        return self._add_filter_object(
            SimpleListFilter(key="id", values=list(codes))
        )

    def description(self, text: str) -> FederalAccountsQuery:
        """Filter by description text (case-insensitive substring).

        Args:
            text: Description text to search for.

        Returns:
            FederalAccountsQuery: Filtered query.
        """
        validated = validate_non_empty_string(text, "description")
        return self._add_filter_object(KeywordsFilter(values=[validated]))

    def account_name(self, text: str) -> FederalAccountsQuery:
        """Alias for description().

        Args:
            text: Description text to search for.

        Returns:
            FederalAccountsQuery: Filtered query.
        """
        return self.description(text)

    def fiscal_year(
        self, year: int, include_noyear_accounts: bool = False
    ) -> FederalAccountsQuery:
        """Filter to federal accounts with active TAS codes for a fiscal year.

        Returns only federal accounts that have at least one Treasury Account
        Symbol active for the given fiscal year.

        Args:
            year: The fiscal year to filter by (e.g., 2024).
            include_noyear_accounts: If False (default), only include accounts
                with TAS codes that have explicit BPOA/EPOA year ranges covering
                the given year. No-year (X) accounts are excluded. If True,
                also include accounts with no-year TAS codes.

        Returns:
            FederalAccountsQuery: Filtered query for matching accounts.

        Example:
            >>> # Only explicit year ranges (excludes no-year accounts)
            >>> active_accounts = agency.federal_accounts.fiscal_year(2024).all()
            >>>
            >>> # Include no-year accounts
            >>> all_active = (
            ...     agency.federal_accounts
            ...     .fiscal_year(2024, include_noyear_accounts=True)
            ...     .all()
            ... )
        """
        def tas_matches(tas: Any) -> bool:
            if not include_noyear_accounts and tas.availability_type_code == "X":
                return False
            return tas.fiscal_year(year)

        def predicate(account: FederalAccount) -> bool:
            return any(tas_matches(tas) for tas in account.tas_codes)

        return self._add_filter(predicate)

    def _clone(self) -> FederalAccountsQuery:
        """Create a copy for method chaining."""
        clone = self.__class__(self._client, self._toptier_code)
        clone._results = self._results
        clone._filter_objects = self._filter_objects.copy()
        clone._predicate_filters = self._predicate_filters.copy()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        return clone

    def __repr__(self) -> str:
        """String representation of FederalAccountsQuery."""
        if self._results is not None:
            return f"<FederalAccountsQuery {self._toptier_code} [{len(self._results)} results]>"
        return f"<FederalAccountsQuery {self._toptier_code} [not fetched]>"
