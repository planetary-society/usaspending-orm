"""FederalAccount model for TAS hierarchy data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base_model import ClientAwareModel

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..queries.tas_codes_query import TASCodesQuery


class FederalAccount(ClientAwareModel):
    """Federal account node in the TAS hierarchy.

    Represents a federal account (budget account) which contains one or more
    Treasury Account Symbols (TAS). Federal accounts are the intermediate
    level between agencies and individual TAS codes.

    Federal Account ID Format: AID-MAIN
    Example: 080-0120 (NASA Science account)

    Attributes:
        id: The federal account code (e.g., "080-0120")
        description: Human-readable account title
        ancestors: List containing parent toptier_code
        count: Number of TAS codes under this account
    """

    def __init__(
        self,
        data: Dict[str, Any],
        client: "USASpendingClient",
        toptier_code: Optional[str] = None,
    ):
        """Initialize FederalAccount.

        Args:
            data: Raw API response data for this federal account.
            client: USASpendingClient instance.
            toptier_code: Parent agency toptier code for navigation.
        """
        raw = self.validate_init_data(data, "FederalAccount", allow_string_id=False)
        super().__init__(raw, client)
        self._toptier_code = toptier_code or (
            self.ancestors[0] if self.ancestors else None
        )

    @property
    def id(self) -> Optional[str]:
        """The federal account code (e.g., '080-0120')."""
        return self.get_value("id")

    @property
    def code(self) -> Optional[str]:
        """Alias for id property."""
        return self.id

    @property
    def federal_account_code(self) -> Optional[str]:
        """Alias for id property."""
        return self.id

    @property
    def description(self) -> Optional[str]:
        """Human-readable account title/description."""
        return self.get_value("description")

    @property
    def name(self) -> Optional[str]:
        """Alias for description property."""
        return self.description

    @property
    def title(self) -> Optional[str]:
        """Alias for description property."""
        return self.description

    @property
    def count(self) -> int:
        """Number of TAS codes under this federal account."""
        return self.get_value("count", default=self.tas_codes.count())

    @property
    def ancestors(self) -> List[str]:
        """List of ancestor node IDs (contains toptier_code)."""
        ancestors = self.get_value("ancestors", default=[])
        return ancestors if isinstance(ancestors, list) else []

    @property
    def toptier_code(self) -> Optional[str]:
        """Parent agency toptier code."""
        return self._toptier_code

    @property
    def tas_codes(self) -> "TASCodesQuery":
        """Get TAS codes under this federal account.

        Returns a query-like object that supports iteration, filtering,
        ordering, and .count().

        Returns:
            TASCodesQuery: Lazy query for TAS codes.

        Example:
            >>> account = agency.federal_accounts[0]
            >>> for tas in account.tas_codes:
            ...     print(tas.id, tas.bpoa, tas.epoa)
            >>>
            >>> # Get count
            >>> print(len(account.tas_codes))
            >>> print(account.tas_codes.count())
            >>>
            >>> # Filter by availability or fiscal year
            >>> no_year = account.tas_codes.availability_type_code("X").all()
            >>> fy2024 = account.tas_codes.fiscal_year(2024).all()
        """
        from ..queries.tas_codes_query import TASCodesQuery

        if not self._toptier_code or not self.federal_account_code:
            # Return empty query if we don't have required codes
            return TASCodesQuery(self._client, "", "")

        return TASCodesQuery(
            self._client,
            self._toptier_code,
            self.federal_account_code,
        )

    def __repr__(self) -> str:
        """String representation of FederalAccount."""
        code = self.federal_account_code or "?"
        title = self.title or "?"
        # Truncate long titles
        if len(title) > 50:
            title = title[:47] + "..."
        return f"<FederalAccount {code}: {title}>"
