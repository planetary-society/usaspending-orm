"""Grant award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from functools import cached_property

from .award import Award
from ..utils.formatter import to_float


class Grant(Award):
    """Grant and assistance award types."""

    TYPE_FIELDS = [
        "fain",
        "uri",
        "record_type",
        "cfda_info",
        "cfda_number",
        "primary_cfda_info",
        "sai_number",
        "funding_opportunity",
        "non_federal_funding",
        "total_funding",
        "transaction_obligated_amount",
    ]

    SEARCH_FIELDS = Award.SEARCH_FIELDS + [
        "Start Date",
        "End Date",
        "Award Amount",
        "Total Outlays",
        "Award Type",
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
    def record_type(self) -> Optional[int]:
        """Grant record type identifier."""
        return self._lazy_get("record_type")

    @property
    def cfda_info(self) -> List[Dict[str, Any]]:
        """Catalog of Federal Domestic Assistance information for grants."""
        return self.get_value(["cfda_info", "Assistance Listings"], default=[])

    @property
    def cfda_number(self) -> Optional[str]:
        """Primary CFDA number for grants."""
        return self.get_value(["cfda_number", "CFDA Number"])

    @property
    def primary_cfda_info(self) -> Optional[Dict[str, Any]]:
        """Primary CFDA program information."""
        return self.get_value(["primary_cfda_info", "primary_assistance_listing"])

    @property
    def sai_number(self) -> Optional[str]:
        """System for Award Identification (SAI) number for grants."""
        return self.get_value(["sai_number", "SAI Number"])

    @cached_property
    def funding_opportunity(self) -> Optional[Dict[str, Any]]:
        """Funding opportunity details for grants."""
        return self._lazy_get("funding_opportunity")

    @property
    def non_federal_funding(self) -> Optional[float]:
        """A summation of this award's transactions' non-federal funding amount"""
        return to_float(self._lazy_get("non_federal_funding", default=None))

    @property
    def total_funding(self) -> Optional[float]:
        """A summation of this award's transactions' funding amount"""
        return to_float(self._lazy_get("total_funding", default=None))

    @property
    def transaction_obligated_amount(self) -> Optional[float]:
        """Transaction-level obligated amount."""
        return to_float(self._lazy_get("transaction_obligated_amount", default=None))
