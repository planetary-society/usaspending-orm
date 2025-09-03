"""Loan award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List

from .grant import Grant
from .award import Award
from ..utils.formatter import to_float


class Loan(Grant):
    """Loan award type."""

    TYPE_FIELDS = [
        "fain",
        "uri",
        "total_subsidy_cost",
        "total_loan_value",
        "cfda_info",
        "cfda_number",
        "primary_cfda_info",
        "sai_number",
    ]

    SEARCH_FIELDS = Award.SEARCH_FIELDS + [
        "Issued Date",
        "Loan Value",
        "Subsidy Cost",
        "SAI Number",
        "CFDA Number",
        "Assistance Listings",
        "primary_assistance_listing",
    ]

    @property
    def fain(self) -> Optional[str]:
        """
        An identification code assigned to each financial assistance award tracking
        purposes. The FAIN is tied to that award (and all future modifications to that
        award) throughout the award's life. Each FAIN is assigned by an agency. Within
        an agency, FAIN are unique: each new award must be issued a new FAIN. FAIN
        stands for Federal Award Identification Number, though the digits are letters,
        not numbers.
        """
        return self._lazy_get("fain")

    @property
    def uri(self) -> Optional[str]:
        """The uri of the award"""
        return self._lazy_get("uri")

    @property
    def total_subsidy_cost(self) -> Optional[float]:
        """The total of the original_loan_subsidy_cost from associated transactions"""
        return to_float(
            self._lazy_get("Subsidy Cost", "total_subsidy_cost", default=None)
        )

    @property
    def total_loan_value(self) -> Optional[float]:
        """The total of the face_value_loan_guarantee from associated transactions"""
        return to_float(self._lazy_get("Loan Value", "total_loan_value", default=None))
    
    @property
    def cfda_info(self) -> List[Dict[str, Any]]:
        """Catalog of Federal Domestic Assistance information for loans."""
        return self._lazy_get("cfda_info", "Assistance Listings", default=[])

    @property
    def cfda_number(self) -> Optional[str]:
        """Primary CFDA number for loans."""
        return self._lazy_get("cfda_number", "CFDA Number")

    @property
    def primary_cfda_info(self) -> Optional[Dict[str, Any]]:
        """Primary CFDA program information."""
        return self._lazy_get("primary_cfda_info", "primary_assistance_listing")

    @property
    def sai_number(self) -> Optional[str]:
        """System for Award Identification (SAI) number for loans."""
        return self._lazy_get("sai_number", "SAI Number")
