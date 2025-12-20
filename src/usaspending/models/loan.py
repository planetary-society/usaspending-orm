"""Loan award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from decimal import Decimal

from .grant import Grant
from .award import Award
from ..utils.formatter import to_decimal


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
        """Federal Award Identification Number (FAIN).

        An identification code assigned to each financial assistance award tracking
        purposes. The FAIN is tied to that award (and all future modifications to that
        award) throughout the award's life. Each FAIN is assigned by an agency. Within
        an agency, FAIN are unique: each new award must be issued a new FAIN. FAIN
        stands for Federal Award Identification Number, though the digits are letters,
        not numbers.

        Returns:
            Optional[str]: The FAIN, or None.
        """
        return self._lazy_get("fain")

    @property
    def uri(self) -> Optional[str]:
        """The Unique Record Identifier (URI) of the award.

        Returns:
            Optional[str]: The URI, or None.
        """
        return self._lazy_get("uri")

    @property
    def total_subsidy_cost(self) -> Optional[Decimal]:
        """Total of the original loan subsidy cost from associated transactions.

        Returns:
            Optional[Decimal]: The total subsidy cost, or None.
        """
        return to_decimal(
            self._lazy_get("Subsidy Cost", "total_subsidy_cost", default=None)
        )

    @property
    def total_loan_value(self) -> Optional[Decimal]:
        """Total of the face value loan guarantee from associated transactions.

        Returns:
            Optional[Decimal]: The total loan value, or None.
        """
        return to_decimal(
            self._lazy_get("Loan Value", "total_loan_value", default=None)
        )

    @property
    def cfda_info(self) -> List[Dict[str, Any]]:
        """Catalog of Federal Domestic Assistance (CFDA) information for loans.

        Returns:
            List[Dict[str, Any]]: List of CFDA dictionaries, or empty list.
        """
        return self._lazy_get("cfda_info", "Assistance Listings", default=[])

    @property
    def cfda_number(self) -> Optional[str]:
        """Primary CFDA number for loans.

        Returns:
            Optional[str]: The primary CFDA number, or None.
        """
        return self._lazy_get("cfda_number", "CFDA Number")

    @property
    def primary_cfda_info(self) -> Optional[Dict[str, Any]]:
        """Primary CFDA program information.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing primary CFDA details, or None.
        """
        return self._lazy_get("primary_cfda_info", "primary_assistance_listing")

    @property
    def sai_number(self) -> Optional[str]:
        """System for Award Identification (SAI) number for loans.

        Returns:
            Optional[str]: The SAI number, or None.
        """
        return self._lazy_get("sai_number", "SAI Number")
