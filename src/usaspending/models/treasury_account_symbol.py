"""TreasuryAccountSymbol model for TAS hierarchy data."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base_model import ClientAwareModel

if TYPE_CHECKING:
    from ..client import USASpendingClient


class TreasuryAccountSymbol(ClientAwareModel):
    """Treasury Account Symbol (TAS) - leaf node in TAS hierarchy.

    Represents an individual Treasury Account Symbol, the lowest level of
    the budget account hierarchy. TAS codes identify specific accounts
    used for recording financial transactions.

    TAS ID Format: AID-BPOA/EPOA-MAIN-SUB
    Example: 080-2011/2012-0120-000

    Components:
        - AID: Agency Identifier (3-4 digits)
        - BPOA/EPOA: Beginning/Ending Period of Availability (fiscal years)
        - MAIN: Main Account Code (4 digits)
        - SUB: Sub-Account Code (3 digits)

    The availability period may be:
        - Year range: "2011/2012" (two-year appropriation)
        - Single year: "2024/2025" (annual appropriation)
        - No-year: "X" (funds available until expended)

    Attributes:
        id: The full TAS code (e.g., "080-2011/2012-0120-000")
        description: Human-readable TAS title
        ancestors: List of parent node IDs [toptier_code, federal_account]
        count: Always 0 for leaf nodes
    """

    # Regex pattern to parse TAS ID: AID-BPOA/EPOA-MAIN-SUB or AID-X-MAIN-SUB
    _TAS_PATTERN = re.compile(
        r"^(?P<aid>\d{2,4})-"  # Agency ID (2-4 digits)
        r"(?P<period>(?P<bpoa>\d{4})/(?P<epoa>\d{4})|X)-"  # Period or X
        r"(?P<main>\d{4})-"  # Main account (4 digits)
        r"(?P<sub>\d{3})$"  # Sub account (3 digits)
    )

    def __init__(
        self,
        data: Dict[str, Any],
        client: "USASpendingClient",
        toptier_code: Optional[str] = None,
        federal_account: Optional[str] = None,
    ):
        """Initialize TreasuryAccountSymbol.

        Args:
            data: Raw API response data for this TAS.
            client: USASpendingClient instance.
            toptier_code: Parent agency toptier code.
            federal_account: Parent federal account code.
        """
        raw = self.validate_init_data(data, "TreasuryAccountSymbol", allow_string_id=False)
        super().__init__(raw, client)
        self._toptier_code = toptier_code
        self._federal_account = federal_account

        # Extract from ancestors if not provided
        ancestors = self.ancestors
        if not self._toptier_code and len(ancestors) > 0:
            self._toptier_code = ancestors[0]
        if not self._federal_account and len(ancestors) > 1:
            self._federal_account = ancestors[1]

        # Parse TAS ID components
        self._parsed: Optional[Dict[str, Optional[str]]] = None

    def _parse_tas_id(self) -> Dict[str, Optional[str]]:
        """Parse TAS ID into components.

        Returns:
            Dictionary with keys: aid, bpoa, epoa, main, sub, availability_type
        """
        if self._parsed is not None:
            return self._parsed

        tas_id = self.id or ""
        match = self._TAS_PATTERN.match(tas_id)

        if match:
            period = match.group("period")
            self._parsed = {
                "aid": match.group("aid"),
                "bpoa": match.group("bpoa"),  # None if X
                "epoa": match.group("epoa"),  # None if X
                "main": match.group("main"),
                "sub": match.group("sub"),
                "availability_type": "X" if period == "X" else None,
            }
        else:
            # Fallback for unexpected formats
            self._parsed = {
                "aid": None,
                "bpoa": None,
                "epoa": None,
                "main": None,
                "sub": None,
                "availability_type": None,
            }

        return self._parsed

    @property
    def id(self) -> Optional[str]:
        """The full TAS code (e.g., '080-2011/2012-0120-000')."""
        return self.get_value("id")

    @property
    def tas_code(self) -> Optional[str]:
        """Alias for id property."""
        return self.id

    @property
    def description(self) -> Optional[str]:
        """Human-readable TAS title/description."""
        return self.get_value("description")

    @property
    def name(self) -> Optional[str]:
        """Alias for description property."""
        return self.description

    @property
    def count(self) -> int:
        """Number of child items (always 0 for TAS leaf nodes)."""
        return self.get_value("count", default=0)

    @property
    def ancestors(self) -> List[str]:
        """List of ancestor node IDs [toptier_code, federal_account]."""
        ancestors = self.get_value("ancestors", default=[])
        return ancestors if isinstance(ancestors, list) else []

    @property
    def toptier_code(self) -> Optional[str]:
        """Parent agency toptier code."""
        return self._toptier_code

    @property
    def federal_account_code(self) -> Optional[str]:
        """Parent federal account code."""
        return self._federal_account

    @property
    def aid(self) -> Optional[str]:
        """Agency Identifier (e.g., '080').

        The AID is a 2-4 digit code identifying the agency responsible
        for the account.
        """
        return self._parse_tas_id()["aid"]

    @property
    def main(self) -> Optional[str]:
        """Main Account Code (e.g., '0120').

        The main account code is a 4-digit code identifying the type
        of fund or account group within an agency.
        """
        return self._parse_tas_id()["main"]

    @property
    def sub(self) -> Optional[str]:
        """Sub-Account Code (e.g., '000').

        The sub-account code provides additional detail about the
        specific account within a main account.
        """
        return self._parse_tas_id()["sub"]

    @property
    def bpoa(self) -> Optional[int]:
        """Beginning Period of Availability (fiscal year).

        Returns:
            The beginning fiscal year (e.g., 2011), or None if this is
            a no-year account (availability_type_code == 'X').
        """
        bpoa_str = self._parse_tas_id()["bpoa"]
        return int(bpoa_str) if bpoa_str else None

    @property
    def epoa(self) -> Optional[int]:
        """Ending Period of Availability (fiscal year).

        Returns:
            The ending fiscal year (e.g., 2012), or None if this is
            a no-year account (availability_type_code == 'X').
        """
        epoa_str = self._parse_tas_id()["epoa"]
        return int(epoa_str) if epoa_str else None

    @property
    def availability_type_code(self) -> Optional[str]:
        """Availability Type Code.

        Returns:
            'X' if this is a no-year account (funds available until expended),
            None otherwise (time-limited appropriation).
        """
        return self._parse_tas_id()["availability_type"]

    def fiscal_year(self, year: int) -> bool:
        """Check if this TAS covers the given fiscal year.

        A TAS covers a fiscal year if:
        - It is a no-year account (availability_type_code == 'X'), or
        - The year falls within the BPOA-EPOA range (inclusive)

        Args:
            year: The fiscal year to check (e.g., 2024).

        Returns:
            True if this TAS is available for the given fiscal year,
            False otherwise.

        Example:
            >>> tas = TreasuryAccountSymbol({"id": "080-2011/2012-0120-000"}, client)
            >>> tas.fiscal_year(2011)  # True
            >>> tas.fiscal_year(2012)  # True
            >>> tas.fiscal_year(2013)  # False
            >>>
            >>> no_year_tas = TreasuryAccountSymbol({"id": "080-X-0120-000"}, client)
            >>> no_year_tas.fiscal_year(2024)  # True (no-year is always available)
        """
        # No-year accounts are always available
        if self.availability_type_code == "X":
            return True

        bpoa = self.bpoa
        epoa = self.epoa

        # If we can't parse the period, return False
        if bpoa is None or epoa is None:
            return False

        return bpoa <= year <= epoa

    def __repr__(self) -> str:
        """String representation of TreasuryAccountSymbol."""
        code = self.tas_code or "?"
        title = self.description or "?"
        # Truncate long titles
        if len(title) > 40:
            title = title[:37] + "..."
        return f"<TreasuryAccountSymbol {code}: {title}>"
