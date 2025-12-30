"""TASCodesQuery - Lazy query for Treasury Account Symbols."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING

from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.treasury_account_symbol import TreasuryAccountSymbol

logger = USASpendingLogger.get_logger(__name__)


class TASCodesQuery:
    """Lazy query for Treasury Account Symbols (TAS).

    Provides a query-like interface for fetching TAS codes under a
    federal account. Supports iteration, indexing, and count operations.

    The query is lazily evaluated - the API is only called when results
    are actually accessed (iteration, indexing, count, etc.).

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

    def __iter__(self) -> Iterator["TreasuryAccountSymbol"]:
        """Iterate over TAS codes.

        Yields:
            TreasuryAccountSymbol instances.
        """
        return iter(self._fetch())

    def __len__(self) -> int:
        """Return the number of TAS codes.

        Returns:
            Count of TAS codes.
        """
        return len(self._fetch())

    def __getitem__(self, index: int) -> "TreasuryAccountSymbol":
        """Get TAS code by index.

        Args:
            index: Zero-based index.

        Returns:
            TreasuryAccountSymbol at the given index.

        Raises:
            IndexError: If index is out of range.
        """
        return self._fetch()[index]

    def __bool__(self) -> bool:
        """Check if there are any TAS codes.

        Returns:
            True if there are TAS codes, False otherwise.
        """
        return len(self) > 0

    def count(self) -> int:
        """Return the number of TAS codes.

        Equivalent to len(query).

        Returns:
            Count of TAS codes.
        """
        return len(self)

    def all(self) -> List["TreasuryAccountSymbol"]:
        """Return all TAS codes as a list.

        Returns:
            List of TreasuryAccountSymbol instances.
        """
        return list(self._fetch())

    def first(self) -> Optional["TreasuryAccountSymbol"]:
        """Return the first TAS code, or None if empty.

        Returns:
            First TreasuryAccountSymbol, or None.
        """
        results = self._fetch()
        return results[0] if results else None

    def __repr__(self) -> str:
        """String representation of TASCodesQuery."""
        if self._results is not None:
            return f"<TASCodesQuery {self._toptier_code}/{self._federal_account} [{len(self._results)} results]>"
        return f"<TASCodesQuery {self._toptier_code}/{self._federal_account} [not fetched]>"
