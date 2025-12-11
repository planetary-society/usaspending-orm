"""Contract award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, TYPE_CHECKING
from functools import cached_property
from decimal import Decimal

from .award import Award
from ..utils.formatter import to_decimal

if TYPE_CHECKING:
    from ..queries.subawards_search import SubAwardsSearch


class Contract(Award):
    """Contract award type including definitive contracts and purchase orders."""

    TYPE_FIELDS = [
        "piid",
        "base_exercised_options",
        "base_and_all_options",
        "contract_award_type",
        "naics_code",
        "naics_description",
        "naics_hierarchy",
        "psc_code",
        "psc_description",
        "psc_hierarchy",
        "latest_transaction_contract_data",
    ]

    SEARCH_FIELDS = Award.SEARCH_FIELDS + [
        "Start Date",
        "End Date",
        "Award Amount",
        "Total Outlays",
        "Contract Award Type",
        "NAICS",
        "PSC",
    ]

    @property
    def piid(self) -> Optional[str]:
        """Procurement Instrument Identifier (PIID).

        A unique identifier assigned to a federal contract, purchase order, basic
        ordering agreement, basic agreement, and blanket purchase agreement. It is
        used to track the contract, and any modifications or transactions related
        to it. After October 2017, it is between 13 and 17 digits, both letters
        and numbers.

        Returns:
            Optional[str]: The PIID, or None.
        """
        return self._lazy_get("piid")

    @property
    def base_exercised_options(self) -> Optional[Decimal]:
        """Sum of base exercised options value from associated transactions.

        Returns:
            Optional[Decimal]: The total base exercised options amount, or None.
        """
        return to_decimal(self._lazy_get("base_exercised_options", default=None))

    @property
    def base_and_all_options(self) -> Optional[Decimal]:
        """Sum of base and all options value from associated transactions.

        Returns:
            Optional[Decimal]: The total base and all options amount, or None.
        """
        return to_decimal(self._lazy_get("base_and_all_options", default=None))

    @property
    def contract_award_type(self) -> Optional[str]:
        """Contract award type description.

        Returns:
            Optional[str]: The contract award type description, or None.
        """
        return self.type_description

    @property
    def naics_code(self) -> Optional[str]:
        """NAICS industry classification code.

        Returns:
            Optional[str]: The NAICS code, or None.
        """
        naics_data = self._lazy_get("naics", "NAICS")
        if isinstance(naics_data, dict):
            return naics_data.get("code")
        if self.naics_hierarchy and isinstance(
            self.naics_hierarchy.get("base_code"), dict
        ):
            return self.naics_hierarchy["base_code"].get("code")
        if self.latest_transaction_contract_data:
            return self.latest_transaction_contract_data.get("naics")
        return None

    @property
    def naics_description(self) -> Optional[str]:
        """NAICS industry classification description.

        Returns:
            Optional[str]: The NAICS description, or None.
        """
        naics_data = self._lazy_get("naics", "NAICS")
        if isinstance(naics_data, dict):
            return naics_data.get("description")
        if self.naics_hierarchy and isinstance(
            self.naics_hierarchy.get("base_code"), dict
        ):
            return self.naics_hierarchy["base_code"].get("description")
        if self.latest_transaction_contract_data:
            return self.latest_transaction_contract_data.get("naics_description")
        return None

    @property
    def psc_code(self) -> Optional[str]:
        """Product/Service Code (PSC) for contracts.

        Returns:
            Optional[str]: The PSC code, or None.
        """
        psc_data = self._lazy_get("psc", "PSC")
        if isinstance(psc_data, dict):
            return psc_data.get("code")
        if self.psc_hierarchy and isinstance(self.psc_hierarchy.get("base_code"), dict):
            return self.psc_hierarchy["base_code"].get("code")
        return None

    @property
    def psc_description(self) -> Optional[str]:
        """Product/Service Code (PSC) description.

        Returns:
            Optional[str]: The PSC description, or None.
        """
        psc_data = self._lazy_get("psc", "PSC")
        if isinstance(psc_data, dict):
            return psc_data.get("description")
        if self.psc_hierarchy and isinstance(self.psc_hierarchy.get("base_code"), dict):
            return self.psc_hierarchy["base_code"].get("description")
        return None

    @cached_property
    def psc_hierarchy(self) -> Optional[Dict[str, Any]]:
        """Product/Service Code (PSC) hierarchy information.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing PSC hierarchy data, or None.
        """
        return self._lazy_get("psc_hierarchy")

    @cached_property
    def naics_hierarchy(self) -> Optional[Dict[str, Any]]:
        """North American Industry Classification System (NAICS) hierarchy.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing NAICS hierarchy data, or None.
        """
        return self._lazy_get("naics_hierarchy")

    @cached_property
    def latest_transaction_contract_data(self) -> Optional[Dict[str, Any]]:
        """Latest contract transaction data with procurement-specific details.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing latest transaction data, or None.
        """
        return self._lazy_get("latest_transaction_contract_data")

    @property
    def subawards(self) -> "SubAwardsSearch":
        """Get subawards query builder for this contract award with appropriate award type filters.

        Automatically applies contract award type filters.

        Examples:
            >>> contract.subawards.count()  # Get count without loading all data
            >>> contract.subawards.limit(10).all()  # Get first 10 subawards
            >>> list(contract.subawards)  # Iterate through all subawards

        Returns:
            SubAwardsSearch: A query builder object for subawards.
        """
        from .award_types import CONTRACT_CODES

        return self._client.subawards.award_id(
            self.generated_unique_award_id
        ).award_type_codes(*CONTRACT_CODES)
