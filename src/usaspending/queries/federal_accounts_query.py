"""FederalAccountsQuery - Lazy query for Federal Accounts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .filter_tree_query import FilterTreeQuery

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.federal_account import FederalAccount


class FederalAccountsQuery(FilterTreeQuery["FederalAccount"]):
    """Lazy query for Federal Accounts with TAS codes.

    Provides a query-like interface for fetching federal accounts under
    an agency. Supports iteration, indexing, count operations, and
    client-side filtering.

    Filters:
        - code(): Filter by federal account code.
        - codes(): Filter by multiple federal account codes.
        - description(): Filter by description text (substring, case-insensitive).
        - account_name(): Alias for description().
        - fiscal_year(): Filter to accounts with TAS codes active in a year.

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
    KEYWORD_FIELDS = ("description", "name", "title")

    def __init__(self, client: USASpendingClient, toptier_code: str):
        """Initialize FederalAccountsQuery.

        Args:
            client: USASpendingClient instance.
            toptier_code: Agency toptier code (e.g., "080").
        """
        self._toptier_code = toptier_code
        super().__init__(client)

    def _scope(self) -> dict[str, str]:
        """Return the agency this query is scoped to."""
        return {"toptier_code": self._toptier_code}

    def _build_model(self, data: dict[str, Any]) -> FederalAccount:
        """Build a FederalAccount, carrying the agency down to it."""
        from ..models.federal_account import FederalAccount

        return FederalAccount(data, self._client, toptier_code=self._toptier_code)

    def _new_instance(self) -> FederalAccountsQuery:
        """Reconstruct with the required toptier code."""
        return self.__class__(self._client, self._toptier_code)

    def account_name(self, text: str) -> FederalAccountsQuery:
        """Alias for description().

        Args:
            text: Description text to search for.

        Returns:
            FederalAccountsQuery: Filtered query.
        """
        return self.description(text)

    def fiscal_year(self, year: int, include_noyear_accounts: bool = False) -> FederalAccountsQuery:
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
            >>> all_active = agency.federal_accounts.fiscal_year(
            ...     2024, include_noyear_accounts=True
            ... ).all()
        """

        def tas_matches(tas: Any) -> bool:
            if not include_noyear_accounts and tas.availability_type_code == "X":
                return False
            return tas.fiscal_year(year)

        def predicate(account: FederalAccount) -> bool:
            return any(tas_matches(tas) for tas in account.tas_codes)

        return self._add_filter(predicate)
