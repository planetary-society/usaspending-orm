"""Funding model for USASpending data."""

from __future__ import annotations

from typing import Dict, Any, Optional, TYPE_CHECKING

from .base_model import BaseModel
from ..utils.formatter import to_float, round_to_millions

if TYPE_CHECKING:
    from .agency import Agency

class Funding(BaseModel):
    """Represents federal account funding data for an award."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize Funding instance.

        Args:
            data: Raw funding data from API response
        """
        super().__init__(data)

    @property
    def transaction_obligated_amount(self) -> Optional[float]:
        """Amount obligated for this funding record."""
        return to_float(self.get_value("transaction_obligated_amount", default=0.0))

    @property
    def gross_outlay_amount(self) -> Optional[float]:
        """Gross outlay amount for this funding record."""
        return to_float(self.get_value("gross_outlay_amount", default=0.0))

    @property
    def disaster_emergency_fund_code(self) -> Optional[str]:
        """Code indicating whether funding is associated with a disaster."""
        return self.get_value("disaster_emergency_fund_code")

    @property
    def federal_account(self) -> Optional[str]:
        """Identifier of the federal account."""
        return self.get_value("federal_account")

    @property
    def account_title(self) -> Optional[str]:
        """Federal account title."""
        return self.get_value("account_title")

    @property
    def funding_agency_name(self) -> Optional[str]:
        """Name of the funding agency."""
        return self.get_value("funding_agency_name")

    @property
    def funding_agency_id(self) -> Optional[int]:
        """Internal surrogate identifier of the funding agency."""
        value = self.get_value("funding_agency_id")
        return int(value) if value is not None else None

    @property
    def funding_toptier_agency_id(self) -> Optional[int]:
        """Top-tier funding agency identifier."""
        value = self.get_value("funding_toptier_agency_id")
        return int(value) if value is not None else None

    @property
    def funding_agency_slug(self) -> Optional[str]:
        """URL-friendly funding agency identifier."""
        return self.get_value("funding_agency_slug")

    @property
    def funding_agency(self) -> Optional["Agency"]:
        """Retrieve the full Agency object for the funding agency."""
        name = self.funding_agency_name
        if name:
            return self._client.agencies.find_all_funding_agencies_by_name(name).toptier()[0]
        else:
            return None

    @property
    def awarding_agency_name(self) -> Optional[str]:
        """Name of the awarding agency."""
        return self.get_value("awarding_agency_name")

    @property
    def awarding_agency_id(self) -> Optional[int]:
        """Internal surrogate identifier of the awarding agency."""
        value = self.get_value("awarding_agency_id")
        return int(value) if value is not None else None

    @property
    def awarding_toptier_agency_id(self) -> Optional[int]:
        """Top-tier awarding agency identifier."""
        value = self.get_value("awarding_toptier_agency_id")
        return int(value) if value is not None else None

    @property
    def awarding_agency_slug(self) -> Optional[str]:
        """URL-friendly awarding agency identifier."""
        return self.get_value("awarding_agency_slug")

    @property
    def object_class(self) -> Optional[str]:
        """Object class code."""
        return self.get_value("object_class")

    @property
    def object_class_name(self) -> Optional[str]:
        """Object class name/description."""
        return self.get_value("object_class_name")

    @property
    def program_activity_code(self) -> Optional[str]:
        """Program activity code."""
        return self.get_value("program_activity_code")

    @property
    def program_activity_name(self) -> Optional[str]:
        """Program activity name."""
        return self.get_value("program_activity_name")

    @property
    def reporting_fiscal_year(self) -> Optional[int]:
        """Fiscal year of the submission date."""
        value = self.get_value("reporting_fiscal_year")
        return int(value) if value is not None else None

    @property
    def reporting_fiscal_quarter(self) -> Optional[int]:
        """Fiscal quarter of the submission date."""
        value = self.get_value("reporting_fiscal_quarter")
        return int(value) if value is not None else None

    @property
    def reporting_fiscal_month(self) -> Optional[int]:
        """Fiscal month of the submission date."""
        value = self.get_value("reporting_fiscal_month")
        return int(value) if value is not None else None

    @property
    def is_quarterly_submission(self) -> Optional[bool]:
        """True if submission is quarterly, False if monthly."""
        return self.get_value("is_quarterly_submission")

    def __repr__(self) -> str:
        """String representation of Funding."""
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
