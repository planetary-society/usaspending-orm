"""AwardAccount model for award-specific federal account data."""

from __future__ import annotations

from decimal import Decimal
from functools import cached_property
from typing import Any, Dict, Optional, TYPE_CHECKING

from .federal_account import FederalAccount
from ..utils.formatter import to_decimal, to_int

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from .agency import Agency


class AwardAccount(FederalAccount):
    """Federal account with award-specific funding data.

    This model extends FederalAccount to represent accounts returned by the
    /api/v2/awards/accounts/ endpoint, which provides federal accounts
    associated with a specific award along with funding agency information.

    The API returns different field names than the TAS hierarchy endpoints:
    - `federal_account` -> id/code
    - `account_title` -> description/name/title
    - `total_transaction_obligated_amount` -> obligated amount for this award

    Additionally provides funding agency information:
    - funding_agency_name
    - funding_agency_abbreviation
    - funding_agency_id
    - funding_toptier_agency_id
    - funding_agency_slug

    Example:
        >>> for account in award.accounts:
        ...     print(f"{account.code}: ${account.total_transaction_obligated_amount:,.2f}")
        ...     print(f"  Funded by: {account.funding_agency.name}")
    """

    def __init__(self, data: Dict[str, Any], client: "USASpendingClient"):
        """Initialize AwardAccount.

        Maps the award/accounts endpoint field names to the standard
        FederalAccount field names.

        Args:
            data: Raw API response data for this account.
            client: USASpendingClient instance.
        """
        # Map award/accounts endpoint field names to FederalAccount field names
        normalized_data = data.copy()

        # Map federal_account -> id (used by FederalAccount)
        if "federal_account" in normalized_data and "id" not in normalized_data:
            normalized_data["id"] = normalized_data["federal_account"]

        # Map account_title -> description (used by FederalAccount)
        if "account_title" in normalized_data and "description" not in normalized_data:
            normalized_data["description"] = normalized_data["account_title"]

        # Extract toptier_code from federal_account (e.g., "080-0131" -> "080")
        toptier_code = self._extract_toptier_code(normalized_data.get("id"))

        super().__init__(normalized_data, client, toptier_code=toptier_code)

    @staticmethod
    def _extract_toptier_code(federal_account: Optional[str]) -> Optional[str]:
        """Extract toptier code from federal account code.

        Args:
            federal_account: Federal account code (e.g., "080-0131").

        Returns:
            The toptier code (e.g., "080"), or None if not parseable.
        """
        if not federal_account or not isinstance(federal_account, str):
            return None

        parts = federal_account.split("-")
        if len(parts) >= 1 and parts[0]:
            return parts[0]

        return None

    @property
    def account_title(self) -> Optional[str]:
        """Title of the federal account.

        Returns:
            Optional[str]: The account title, or None.
        """
        return self.description

    @property
    def federal_account(self) -> Optional[str]:
        """The federal account code (YYY-XXXX)

        Returns:
            Optional[str]: The federal account code, or None.
        """
        return self.id

    @property
    def total_transaction_obligated_amount(self) -> Decimal:
        """Total obligated amount for this account on this award.

        Returns:
            Decimal: The obligated amount, or 0.00 if not available.
        """
        value = self.get_value("total_transaction_obligated_amount")
        return to_decimal(value) or Decimal("0.00")

    @property
    def obligated_amount(self) -> Decimal:
        """Alias for total_transaction_obligated_amount.

        Returns:
            Decimal: The obligated amount, or 0.00 if not available.
        """
        return self.total_transaction_obligated_amount

    @property
    def funding_agency_name(self) -> Optional[str]:
        """Name of the funding agency.

        Returns:
            Optional[str]: The funding agency name, or None.
        """
        return self.get_value("funding_agency_name")

    @property
    def funding_agency_abbreviation(self) -> Optional[str]:
        """Abbreviation of the funding agency.

        Returns:
            Optional[str]: The funding agency abbreviation, or None.
        """
        return self.get_value("funding_agency_abbreviation")

    @property
    def funding_agency_id(self) -> Optional[int]:
        """Internal ID of the funding agency.

        Returns:
            Optional[int]: The funding agency ID, or None.
        """
        return to_int(self.get_value("funding_agency_id"))

    @property
    def funding_toptier_agency_id(self) -> Optional[int]:
        """Toptier agency ID for the funding agency.

        Returns:
            Optional[int]: The funding toptier agency ID, or None.
        """
        return to_int(self.get_value("funding_toptier_agency_id"))

    @property
    def funding_agency_slug(self) -> Optional[str]:
        """URL slug for the funding agency.

        Returns:
            Optional[str]: The funding agency slug for USASpending URLs, or None.
        """
        return self.get_value("funding_agency_slug")

    @cached_property
    def funding_agency(self) -> Optional["Agency"]:
        """Funding agency as an Agency object.

        Creates an Agency instance from the funding agency fields.

        Returns:
            Optional[Agency]: Agency object for the funding agency, or None
            if funding agency information is not available.
        """
        # Check if we have any funding agency data
        agency_name = self.funding_agency_name
        if not agency_name:
            return None

        from .agency import Agency

        agency_data = {
            "name": agency_name,
            "abbreviation": self.funding_agency_abbreviation,
            "agency_id": self.funding_agency_id,
            "id": self.funding_toptier_agency_id,
            "slug": self.funding_agency_slug,
            "toptier_code": self.toptier_code,
        }

        return Agency(agency_data, self._client)

    def __repr__(self) -> str:
        """String representation of AwardAccount."""
        code = self.federal_account_code or "?"
        amount = self.total_transaction_obligated_amount
        agency = self.funding_agency_abbreviation or "?"
        return f"<AwardAccount {code}: ${amount:,.2f} ({agency})>"
