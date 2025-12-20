"""Grant award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property
from decimal import Decimal

from .award import Award
from ..utils.formatter import to_decimal

if TYPE_CHECKING:
    from ..queries.subawards_search import SubAwardsSearch


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
    def record_type(self) -> Optional[int]:
        """Grant record type identifier.

        Returns:
            Optional[int]: The record type ID, or None.
        """
        return self._lazy_get("record_type")

    @property
    def cfda_info(self) -> List[Dict[str, Any]]:
        """Catalog of Federal Domestic Assistance (CFDA) information for grants.

        Returns:
            List[Dict[str, Any]]: List of CFDA dictionaries, or empty list.
        """
        return self._lazy_get("cfda_info", "Assistance Listings", default=[])

    @property
    def cfda_number(self) -> Optional[str]:
        """Primary CFDA number for grants.

        Returns:
            Optional[str]: The primary CFDA number, or None.
        """
        primary_info = self._lazy_get("primary_cfda_info", "primary_assistance_listing")
        if primary_info:
            return primary_info.get("cfda_number")

        cfda_list = self._lazy_get("cfda_info", "Assistance Listings")
        if cfda_list:
            return cfda_list[0].get("cfda_number")

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
        """System for Award Identification (SAI) number for grants.

        Returns:
            Optional[str]: The SAI number, or None.
        """
        return self._lazy_get("sai_number", "SAI Number")

    @cached_property
    def funding_opportunity(self) -> Optional[Dict[str, Any]]:
        """Funding opportunity details for grants.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing funding opportunity details, or None.
        """
        return self._lazy_get("funding_opportunity")

    @property
    def non_federal_funding(self) -> Optional[Decimal]:
        """Summation of this award's transactions' non-federal funding amount.

        Returns:
            Optional[Decimal]: The non-federal funding amount, or None.
        """
        return to_decimal(self._lazy_get("non_federal_funding", default=None))

    @property
    def total_funding(self) -> Optional[Decimal]:
        """Sum of the federal action obligations and the Non-Federal funding amount.

        Returns:
            Optional[Decimal]: The total funding amount, or None.
        """
        return to_decimal(self._lazy_get("total_funding", default=None))

    @property
    def transaction_obligated_amount(self) -> Optional[Decimal]:
        """Transaction-level obligated amount.

        Returns:
            Optional[Decimal]: The transaction obligated amount, or None.
        """
        return to_decimal(self._lazy_get("transaction_obligated_amount", default=None))

    @property
    def total_subsidy_cost(self) -> Optional[Decimal]:
        """Total subsidy cost for this award.

        Returns:
            Optional[Decimal]: The total subsidy cost, or None.
        """
        return to_decimal(self._lazy_get("total_subsidy_cost", default=None))

    @property
    def base_exercised_options(self) -> Optional[Decimal]:
        """Total amount obligated for the base and exercised options of this award.

        Returns:
            Optional[Decimal]: The base exercised options amount, or None.
        """
        return to_decimal(self._lazy_get("base_exercised_options", default=None))

    @property
    def base_and_all_options(self) -> Optional[Decimal]:
        """Total amount obligated for the base and all options of this award.

        Returns:
            Optional[Decimal]: The base and all options amount, or None.
        """
        return to_decimal(self._lazy_get("base_and_all_options", default=None))

    @property
    def subawards(self) -> "SubAwardsSearch":
        """Get subawards query builder for this grant award with appropriate award type filters.

        Automatically applies grant award type filters.

        Examples:
            >>> grant.subawards.count()  # Get count without loading all data
            >>> grant.subawards.limit(10).all()  # Get first 10 subawards
            >>> list(grant.subawards)  # Iterate through all subawards

        Returns:
            SubAwardsSearch: A query builder object for subawards.
        """
        from .award_types import GRANT_CODES

        # Grant subawards use grant award types only
        # Note: Due to validation in AwardsSearch, we cannot mix grant/direct_payment/other categories
        return self._client.subawards.award_id(
            self.generated_unique_award_id
        ).award_type_codes(*GRANT_CODES)
