"""Funding model for USASpending data."""

from __future__ import annotations

from typing import Dict, Any, Optional

from .base_model import BaseModel
from ..utils.formatter import to_float


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
        return to_float(self.raw.get("transaction_obligated_amount"))

    @property
    def gross_outlay_amount(self) -> Optional[float]:
        """Gross outlay amount for this funding record."""
        return to_float(self.raw.get("gross_outlay_amount"))

    @property
    def disaster_emergency_fund_code(self) -> Optional[str]:
        """Code indicating whether funding is associated with a disaster."""
        return self.raw.get("disaster_emergency_fund_code")

    @property
    def federal_account(self) -> Optional[str]:
        """Identifier of the federal account."""
        return self.raw.get("federal_account")

    @property
    def account_title(self) -> Optional[str]:
        """Federal account title."""
        return self.raw.get("account_title")

    @property
    def funding_agency_name(self) -> Optional[str]:
        """Name of the funding agency."""
        return self.raw.get("funding_agency_name")

    @property
    def funding_agency_id(self) -> Optional[int]:
        """Internal surrogate identifier of the funding agency."""
        value = self.raw.get("funding_agency_id")
        return int(value) if value is not None else None

    @property
    def funding_toptier_agency_id(self) -> Optional[int]:
        """Top-tier funding agency identifier."""
        value = self.raw.get("funding_toptier_agency_id")
        return int(value) if value is not None else None

    @property
    def funding_agency_slug(self) -> Optional[str]:
        """URL-friendly funding agency identifier."""
        return self.raw.get("funding_agency_slug")

    @property
    def awarding_agency_name(self) -> Optional[str]:
        """Name of the awarding agency."""
        return self.raw.get("awarding_agency_name")

    @property
    def awarding_agency_id(self) -> Optional[int]:
        """Internal surrogate identifier of the awarding agency."""
        value = self.raw.get("awarding_agency_id")
        return int(value) if value is not None else None

    @property
    def awarding_toptier_agency_id(self) -> Optional[int]:
        """Top-tier awarding agency identifier."""
        value = self.raw.get("awarding_toptier_agency_id")
        return int(value) if value is not None else None

    @property
    def awarding_agency_slug(self) -> Optional[str]:
        """URL-friendly awarding agency identifier."""
        return self.raw.get("awarding_agency_slug")

    @property
    def object_class(self) -> Optional[str]:
        """Object class code."""
        return self.raw.get("object_class")

    @property
    def object_class_name(self) -> Optional[str]:
        """Object class name/description."""
        return self.raw.get("object_class_name")

    @property
    def program_activity_code(self) -> Optional[str]:
        """Program activity code."""
        return self.raw.get("program_activity_code")

    @property
    def program_activity_name(self) -> Optional[str]:
        """Program activity name."""
        return self.raw.get("program_activity_name")

    @property
    def reporting_fiscal_year(self) -> Optional[int]:
        """Fiscal year of the submission date."""
        value = self.raw.get("reporting_fiscal_year")
        return int(value) if value is not None else None

    @property
    def reporting_fiscal_quarter(self) -> Optional[int]:
        """Fiscal quarter of the submission date."""
        value = self.raw.get("reporting_fiscal_quarter")
        return int(value) if value is not None else None

    @property
    def reporting_fiscal_month(self) -> Optional[int]:
        """Fiscal month of the submission date."""
        value = self.raw.get("reporting_fiscal_month")
        return int(value) if value is not None else None

    @property
    def is_quarterly_submission(self) -> Optional[bool]:
        """True if submission is quarterly, False if monthly."""
        return self.raw.get("is_quarterly_submission")

    def __repr__(self) -> str:
        """String representation of Funding."""
        year = self.reporting_fiscal_year or "?"
        month = self.reporting_fiscal_month

        # Format month with zero padding if it's a number
        if month is not None:
            month_str = f"{month:02d}"
        else:
            month_str = "?"

        amount = self.transaction_obligated_amount
        amount_str = f"${amount:,.2f}" if amount is not None else "?"
        agency = self.funding_agency_name or "Unknown Agency"

        return f"<Funding {year}-{month_str} {agency} {amount_str}>"
