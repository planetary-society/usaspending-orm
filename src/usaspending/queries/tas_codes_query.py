"""TASCodesQuery - Lazy query for Treasury Account Symbols."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from ..logging_config import USASpendingLogger
from ..utils.validations import validate_non_empty_string
from .client_side_query_builder import ClientSideQueryBuilder
from .filters import KeywordsFilter, SimpleListFilter, SimpleStringFilter

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.treasury_account_symbol import TreasuryAccountSymbol

logger = USASpendingLogger.get_logger(__name__)


class TASCodesQuery(ClientSideQueryBuilder["TreasuryAccountSymbol"]):
    """Lazy query for Treasury Account Symbols (TAS).

    Provides a query-like interface for fetching TAS codes under a
    federal account. Supports iteration, indexing, count operations, and
    client-side filtering.

    The query is lazily evaluated - the API is only called when results
    are actually accessed (iteration, indexing, count, etc.).

    Filters:
        - code(): Filter by TAS code.
        - codes(): Filter by multiple TAS codes.
        - availability_type_code(): Filter by availability type (e.g., "X").
        - description(): Filter by description text (case-insensitive substring).
        - fiscal_year(): Filter by fiscal year coverage.

    Example:
        >>> tas_codes = account.tas_codes
        >>> len(tas_codes)  # Fetches and returns count
        16
        >>> tas_codes.count()  # Same as len()
        16
        >>> for tas in tas_codes:
        ...     print(tas.id)
        >>> first_tas = tas_codes.first()
        >>> all_tas = tas_codes.all()
    """

    ENDPOINT = "/references/filter_tree/tas/{toptier_code}/{federal_account}/"

    def __init__(
        self,
        client: "USASpendingClient",
        toptier_code: str,
        federal_account: str,
    ):
        """Initialize TASCodesQuery.

        Args:
            client: USASpendingClient instance.
            toptier_code: Agency toptier code (e.g., "080").
            federal_account: Federal account code (e.g., "080-0120").
        """
        self._client = client
        self._toptier_code = toptier_code
        self._federal_account = federal_account
        self._results: Optional[List["TreasuryAccountSymbol"]] = None
        super().__init__(
            items=[],
            keyword_fields=["description", "name"],
        )

    def _fetch(self) -> List["TreasuryAccountSymbol"]:
        """Fetch TAS codes from the API.

        Returns:
            List of TreasuryAccountSymbol model instances.
        """
        if self._results is not None:
            return self._results

        # Handle empty parameters
        if not self._toptier_code or not self._federal_account:
            self._results = []
            return self._results

        endpoint = self.ENDPOINT.format(
            toptier_code=self._toptier_code,
            federal_account=self._federal_account,
        )

        logger.debug(
            "Fetching TAS codes for %s/%s",
            self._toptier_code,
            self._federal_account,
        )

        response = self._client._make_request("GET", endpoint)
        results = response.get("results", [])

        from ..models.treasury_account_symbol import TreasuryAccountSymbol

        self._results = [
            TreasuryAccountSymbol(
                data,
                self._client,
                toptier_code=self._toptier_code,
                federal_account=self._federal_account,
            )
            for data in results
            if isinstance(data, dict)
        ]

        logger.debug("Fetched %d TAS codes", len(self._results))

        return self._results

    def _materialize(self) -> list["TreasuryAccountSymbol"]:
        """Return fetched TAS codes for client-side filtering."""
        return list(self._fetch())

    def code(self, code: str) -> "TASCodesQuery":
        """Filter by TAS code.

        Args:
            code: TAS code (e.g., "080-2011/2012-0120-000").

        Returns:
            TASCodesQuery: Filtered query.
        """
        validated = validate_non_empty_string(code, "code")
        return self._add_filter_object(SimpleStringFilter(key="id", value=validated))

    def codes(self, *codes: str) -> "TASCodesQuery":
        """Filter by multiple TAS codes.

        Args:
            *codes: One or more TAS codes.

        Returns:
            TASCodesQuery: Filtered query.
        """
        return self._add_filter_object(SimpleListFilter(key="id", values=list(codes)))

    def availability_type_code(self, code: str) -> "TASCodesQuery":
        """Filter by availability type code.

        Args:
            code: Availability type code (e.g., "X").

        Returns:
            TASCodesQuery: Filtered query.
        """
        validated = validate_non_empty_string(code, "availability_type_code")
        return self._add_filter_object(
            SimpleStringFilter(key="availability_type_code", value=validated)
        )

    def description(self, text: str) -> "TASCodesQuery":
        """Filter by description text (case-insensitive substring).

        Args:
            text: Description text to search for.

        Returns:
            TASCodesQuery: Filtered query.
        """
        validated = validate_non_empty_string(text, "description")
        return self._add_filter_object(KeywordsFilter(values=[validated]))

    def name(self, text: str) -> "TASCodesQuery":
        """Alias for description().

        Args:
            text: Description text to search for.

        Returns:
            TASCodesQuery: Filtered query.
        """
        return self.description(text)

    def fiscal_year(self, year: int) -> "TASCodesQuery":
        """Filter to TAS codes covering a fiscal year.

        Args:
            year: Fiscal year to match.

        Returns:
            TASCodesQuery: Filtered query.
        """
        def predicate(tas: "TreasuryAccountSymbol") -> bool:
            return tas.fiscal_year(year)

        return self._add_filter(predicate)

    def _clone(self) -> "TASCodesQuery":
        """Create a copy for method chaining."""
        clone = self.__class__(self._client, self._toptier_code, self._federal_account)
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
        """String representation of TASCodesQuery."""
        if self._results is not None:
            return f"<TASCodesQuery {self._toptier_code}/{self._federal_account} [{len(self._results)} results]>"
        return f"<TASCodesQuery {self._toptier_code}/{self._federal_account} [not fetched]>"
