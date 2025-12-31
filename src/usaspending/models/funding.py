"""Funding model for USASpending data."""

from __future__ import annotations

from typing import Dict, Any, Optional, TYPE_CHECKING
from decimal import Decimal

from .base_model import ClientAwareModel
from ..utils.formatter import to_decimal, round_to_millions

if TYPE_CHECKING:
    from .agency import Agency
    from .federal_account import FederalAccount
    from ..client import USASpendingClient


class Funding(ClientAwareModel):
    """Represents federal account funding data for an award."""

    def __init__(self, data: Dict[str, Any], client: "USASpendingClient"):
        """Initialize Funding instance.

        Args:
            data: Raw funding data from API response.
            client: The USASpendingClient instance.
        """
        super().__init__(data, client)

    @property
    def transaction_obligated_amount(self) -> Optional[Decimal]:
        """Amount obligated for this funding record.

        Returns:
            Optional[Decimal]: The transaction obligated amount, or 0.0.
        """
        return to_decimal(self.get_value("transaction_obligated_amount", default=0.0))

    @property
    def gross_outlay_amount(self) -> Optional[Decimal]:
        """Gross outlay amount for this funding record.

        Returns:
            Optional[Decimal]: The gross outlay amount, or 0.0.
        """
        return to_decimal(self.get_value("gross_outlay_amount", default=0.0))

    @property
    def disaster_emergency_fund_code(self) -> Optional[str]:
        """Code indicating whether funding is associated with a disaster.

        Returns:
            Optional[str]: The disaster emergency fund code, or None.
        """
        return self.get_value("disaster_emergency_fund_code")

    @property
    def federal_account_code(self) -> Optional[str]:
        """Identifier of the federal account.

        Returns:
            Optional[str]: The federal account identifier, or None.
        """
        return self.get_value("federal_account")

    @property
    def federal_account(self) -> Optional["FederalAccount"]:
        """Retrieve the FederalAccount object for this funding record.

        Returns:
            Optional[FederalAccount]: The FederalAccount object, or None.
        """
        code = self.get_value("federal_account")
        if not code:
            return None

        from .federal_account import FederalAccount

        data = {
            "id": code,
            "description": self.get_value("account_title"),
            "ancestors": [str(self.funding_toptier_agency_id)]
            if self.funding_toptier_agency_id
            else [],
        }

        return FederalAccount(
            data=data,
            client=self._client,
            toptier_code=str(self.funding_toptier_agency_id)
            if self.funding_toptier_agency_id
            else None,
        )

    @property
    def account_title(self) -> Optional[str]:
        """Federal account title.

        Returns:
            Optional[str]: The federal account title, or None.
        """
        return self.get_value("account_title")

    @property
    def funding_agency_name(self) -> Optional[str]:
        """Name of the funding agency.

        Returns:
            Optional[str]: The funding agency name, or None.
        """
        return self.get_value("funding_agency_name")

    @property
    def funding_agency_id(self) -> Optional[int]:
        """Internal surrogate identifier of the funding agency.

        Returns:
            Optional[int]: The funding agency ID, or None.
        """
        value = self.get_value("funding_agency_id")
        return int(value) if value is not None else None

    @property
    def funding_toptier_agency_id(self) -> Optional[str]:
        """Top-tier funding agency identifier.

        Returns:
            Optional[str]: The funding toptier agency ID, or None.
        """
        value = self.get_value("funding_toptier_agency_id")
        return str(value) if value is not None else None

    @property
    def funding_agency_slug(self) -> Optional[str]:
        """URL-friendly funding agency identifier.

        Returns:
            Optional[str]: The funding agency slug, or None.
        """
        return self.get_value("funding_agency_slug")

    @property
    def funding_agency(self) -> Optional["Agency"]:
        """Retrieve the Agency object for the funding agency.

        Constructs an Agency from the existing Funding data without making
        an API call. The Agency will lazy-load additional details if accessed.

        Returns:
            Optional[Agency]: The Agency object for the funding agency, or None.
        """
        toptier_code = self.funding_toptier_agency_id
        if not toptier_code:
            return None

        from .agency import Agency

        data = {
            "toptier_code": toptier_code,
            "name": self.get_value("funding_agency_name"),
            "agency_id": self.get_value("funding_agency_id"),
            "slug": self.get_value("funding_agency_slug"),
        }

        return Agency(data=data, client=self._client)

    @property
    def awarding_agency_name(self) -> Optional[str]:
        """Name of the awarding agency.

        Returns:
            Optional[str]: The awarding agency name, or None.
        """
        return self.get_value("awarding_agency_name")

    @property
    def awarding_agency_id(self) -> Optional[int]:
        """Internal surrogate identifier of the awarding agency.

        Returns:
            Optional[int]: The awarding agency ID, or None.
        """
        value = self.get_value("awarding_agency_id")
        return int(value) if value is not None else None

    @property
    def awarding_toptier_agency_id(self) -> Optional[str]:
        """Top-tier awarding agency identifier.

        Returns:
            Optional[str]: The awarding toptier agency ID, or None.
        """
        value = self.get_value("awarding_toptier_agency_id")
        return str(value) if value is not None else None

    @property
    def awarding_agency_slug(self) -> Optional[str]:
        """URL-friendly awarding agency identifier.

        Returns:
            Optional[str]: The awarding agency slug, or None.
        """
        return self.get_value("awarding_agency_slug")

    @property
    def awarding_agency(self) -> Optional["Agency"]:
        """Retrieve the Agency object for the awarding agency.

        Constructs an Agency from the existing Funding data without making
        an API call. The Agency will lazy-load additional details if accessed.

        Returns:
            Optional[Agency]: The Agency object for the awarding agency, or None.
        """
        toptier_code = self.awarding_toptier_agency_id
        if not toptier_code:
            return None

        from .agency import Agency

        data = {
            "toptier_code": toptier_code,
            "name": self.get_value("awarding_agency_name"),
            "agency_id": self.get_value("awarding_agency_id"),
            "slug": self.get_value("awarding_agency_slug"),
        }

        return Agency(data=data, client=self._client)

    @property
    def object_class(self) -> Optional[str]:
        """Object class code.

        Returns:
            Optional[str]: The object class code, or None.
        """
        return self.get_value("object_class")

    @property
    def object_class_name(self) -> Optional[str]:
        """Object class name/description.

        Returns:
            Optional[str]: The object class name, or None.
        """
        return self.get_value("object_class_name")

    @property
    def program_activity_code(self) -> Optional[str]:
        """Program activity code.

        Returns:
            Optional[str]: The program activity code, or None.
        """
        return self.get_value("program_activity_code")

    @property
    def program_activity_name(self) -> Optional[str]:
        """Program activity name.

        Returns:
            Optional[str]: The program activity name, or None.
        """
        return self.get_value("program_activity_name")

    @property
    def reporting_fiscal_year(self) -> Optional[int]:
        """Fiscal year of the submission date.

        Returns:
            Optional[int]: The reporting fiscal year, or None.
        """
        value = self.get_value("reporting_fiscal_year")
        return int(value) if value is not None else None

    @property
    def reporting_fiscal_quarter(self) -> Optional[int]:
        """Fiscal quarter of the submission date.

        Returns:
            Optional[int]: The reporting fiscal quarter, or None.
        """
        value = self.get_value("reporting_fiscal_quarter")
        return int(value) if value is not None else None

    @property
    def reporting_fiscal_month(self) -> Optional[int]:
        """Fiscal month of the submission date.

        Returns:
            Optional[int]: The reporting fiscal month, or None.
        """
        value = self.get_value("reporting_fiscal_month")
        return int(value) if value is not None else None

    @property
    def is_quarterly_submission(self) -> Optional[bool]:
        """Indicates if submission is quarterly.

        Returns:
            Optional[bool]: True if submission is quarterly, False if monthly, or None.
        """
        return self.get_value("is_quarterly_submission")

    def __repr__(self) -> str:
        """String representation of Funding.

        Returns:
            str: String containing year, month, agency, and amount.
        """
        year = self.reporting_fiscal_year or "?"
        month = self.reporting_fiscal_month

        # Format month with zero padding if it's a number
        if month is not None:
            month_str = f"{month:02d}"
        else:
            month_str = "?"

        if self.transaction_obligated_amount:
            amount = self.transaction_obligated_amount
            amount_str = f"OBL: {round_to_millions(amount)}"
        elif self.gross_outlay_amount:
            amount = self.gross_outlay_amount
            amount_str = f"OUTLAY: {round_to_millions(amount)}"
        else:
            amount_str = "?"

        agency = self.funding_agency_name or "Unknown Agency"

        return f"<Funding {year}-{month_str} {agency} {amount_str}>"
