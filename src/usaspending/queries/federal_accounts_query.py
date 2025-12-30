"""FederalAccountsQuery - Lazy query for Federal Accounts."""

from __future__ import annotations

from typing import Iterator, List, Optional, TYPE_CHECKING

from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.federal_account import FederalAccount

logger = USASpendingLogger.get_logger(__name__)


class FederalAccountsQuery:
    """Lazy query for Federal Accounts with TAS codes.

    Provides a query-like interface for fetching federal accounts under
    an agency. Supports iteration, indexing, and count operations.

    The query is lazily evaluated - the API is only called when results
    are actually accessed (iteration, indexing, count, etc.).

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
        client: "USASpendingClient",
        toptier_code: str,
    ):
        """Initialize FederalAccountsQuery.

        Args:
            client: USASpendingClient instance.
            toptier_code: Agency toptier code (e.g., "080").
        """
        self._client = client
        self._toptier_code = toptier_code
        self._results: Optional[List["FederalAccount"]] = None

    def _fetch(self) -> List["FederalAccount"]:
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

    def __iter__(self) -> Iterator["FederalAccount"]:
        """Iterate over federal accounts.

        Yields:
            FederalAccount instances.
        """
        return iter(self._fetch())

    def __len__(self) -> int:
        """Return the number of federal accounts.

        Returns:
            Count of federal accounts.
        """
        return len(self._fetch())

    def __getitem__(self, index: int) -> "FederalAccount":
        """Get federal account by index.

        Args:
            index: Zero-based index.

        Returns:
            FederalAccount at the given index.

        Raises:
            IndexError: If index is out of range.
        """
        return self._fetch()[index]

    def __bool__(self) -> bool:
        """Check if there are any federal accounts.

        Returns:
            True if there are federal accounts, False otherwise.
        """
        return len(self) > 0

    def count(self) -> int:
        """Return the number of federal accounts.

        Equivalent to len(query).

        Returns:
            Count of federal accounts.
        """
        return len(self)

    def all(self) -> List["FederalAccount"]:
        """Return all federal accounts as a list.

        Returns:
            List of FederalAccount instances.
        """
        return list(self._fetch())

    def first(self) -> Optional["FederalAccount"]:
        """Return the first federal account, or None if empty.

        Returns:
            First FederalAccount, or None.
        """
        results = self._fetch()
        return results[0] if results else None

    def fiscal_year(
        self, year: int, include_noyear_accounts: bool = False
    ) -> List["FederalAccount"]:
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
            List of FederalAccount instances with active TAS codes for the year.

        Example:
            >>> # Only explicit year ranges (excludes no-year accounts)
            >>> active_accounts = agency.federal_accounts.fiscal_year(2024)
            >>>
            >>> # Include no-year accounts
            >>> all_active = agency.federal_accounts.fiscal_year(2024, include_noyear_accounts=True)
        """
        accounts = self._fetch()

        def tas_matches(tas) -> bool:
            if not include_noyear_accounts and tas.availability_type_code == "X":
                return False
            return tas.fiscal_year(year)

        return [
            account
            for account in accounts
            if any(tas_matches(tas) for tas in account.tas_codes)
        ]

    def __repr__(self) -> str:
        """String representation of FederalAccountsQuery."""
        if self._results is not None:
            return f"<FederalAccountsQuery {self._toptier_code} [{len(self._results)} results]>"
        return f"<FederalAccountsQuery {self._toptier_code} [not fetched]>"
