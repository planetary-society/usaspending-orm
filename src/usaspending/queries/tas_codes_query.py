"""TASCodesQuery - Lazy query for Treasury Account Symbols."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..utils.validations import validate_non_empty_string
from .filter_tree_query import FilterTreeQuery
from .filters import SimpleStringFilter

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.treasury_account_symbol import TreasuryAccountSymbol


class TASCodesQuery(FilterTreeQuery["TreasuryAccountSymbol"]):
    """Lazy query for Treasury Account Symbols (TAS).

    Provides a query-like interface for fetching TAS codes under a
    federal account. Supports iteration, indexing, count operations, and
    client-side filtering.

    Filters:
        - code(): Filter by TAS code.
        - codes(): Filter by multiple TAS codes.
        - availability_type_code(): Filter by availability type (e.g., "X").
        - description(): Filter by description text (substring, case-insensitive).
        - name(): Alias for description().
        - fiscal_year(): Filter to TAS codes covering a fiscal year.

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
        client: USASpendingClient,
        toptier_code: str,
        federal_account: str,
    ):
        """Initialize TASCodesQuery.

        Args:
            client: USASpendingClient instance.
            toptier_code: Agency toptier code (e.g., "080").
            federal_account: Federal account code (e.g., "080-0120").
        """
        self._toptier_code = toptier_code
        self._federal_account = federal_account
        super().__init__(client)

    def _scope(self) -> dict[str, str]:
        """Return the agency and federal account this query is scoped to."""
        return {
            "toptier_code": self._toptier_code,
            "federal_account": self._federal_account,
        }

    def _build_model(self, data: dict[str, Any]) -> TreasuryAccountSymbol:
        """Build a TreasuryAccountSymbol, carrying its scope down to it."""
        from ..models.treasury_account_symbol import TreasuryAccountSymbol

        return TreasuryAccountSymbol(
            data,
            self._client,
            toptier_code=self._toptier_code,
            federal_account=self._federal_account,
        )

    def _new_instance(self) -> TASCodesQuery:
        """Reconstruct with the required toptier code and federal account."""
        return self.__class__(self._client, self._toptier_code, self._federal_account)

    def availability_type_code(self, code: str) -> TASCodesQuery:
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

    def name(self, text: str) -> TASCodesQuery:
        """Alias for description().

        Args:
            text: Description text to search for.

        Returns:
            TASCodesQuery: Filtered query.
        """
        return self.description(text)

    def fiscal_year(self, year: int) -> TASCodesQuery:
        """Filter to TAS codes covering a fiscal year.

        Args:
            year: Fiscal year to match.

        Returns:
            TASCodesQuery: Filtered query.
        """

        def predicate(tas: TreasuryAccountSymbol) -> bool:
            return tas.fiscal_year(year)

        return self._add_filter(predicate)
