"""Contract award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, TYPE_CHECKING
from functools import cached_property

from .award import Award
from ..utils.formatter import to_float

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
        """
        Procurement Instrument Identifier - A unique identifier assigned to a federal
        contract, purchase order, basic ordering agreement, basic agreement, and
        blanket purchase agreement. It is used to track the contract, and any
        modifications or transactions related to it. After October 2017, it is
        between 13 and 17 digits, both letters and numbers.
        """
        return self._lazy_get("piid")

    @property
    def base_exercised_options(self) -> Optional[float]:
        """The sum of the base_exercised_options_val from associated transactions"""
        return to_float(self._lazy_get("base_exercised_options", default=None))

    @property
    def base_and_all_options(self) -> Optional[float]:
        """The sum of the base_and_all_options_value from associated transactions"""
        return to_float(self._lazy_get("base_and_all_options", default=None))

    @property
    def contract_award_type(self) -> Optional[str]:
        """Contract award type description."""
        return self.get_value(["contract_award_type", "Contract Award Type"])

    @property
    def naics_code(self) -> Optional[str]:
        """NAICS industry classification code."""
        naics_data = self.get_value(["naics", "NAICS"])
        if isinstance(naics_data, dict):
            return naics_data.get("code")
        return None

    @property
    def naics_description(self) -> Optional[str]:
        """NAICS industry classification description."""
        naics_data = self.get_value(["naics", "NAICS"])
        if isinstance(naics_data, dict):
            return naics_data.get("description")
        return None

    @property
    def psc_code(self) -> Optional[str]:
        """Product/Service Code (PSC) for contracts."""
        psc_data = self.get_value(["psc", "PSC"])
        if isinstance(psc_data, dict):
            return psc_data.get("code")
        return None

    @property
    def psc_description(self) -> Optional[str]:
        """Product/Service Code (PSC) description."""
        psc_data = self.get_value(["psc", "PSC"])
        if isinstance(psc_data, dict):
            return psc_data.get("description")
        return None

    @cached_property
    def psc_hierarchy(self) -> Optional[Dict[str, Any]]:
        """Product/Service Code (PSC) hierarchy information."""
        return self._lazy_get("psc_hierarchy")

    @cached_property
    def naics_hierarchy(self) -> Optional[Dict[str, Any]]:
        """North American Industry Classification System (NAICS) hierarchy."""
        return self._lazy_get("naics_hierarchy")

    @cached_property
    def latest_transaction_contract_data(self) -> Optional[Dict[str, Any]]:
        """Latest contract transaction data with procurement-specific details."""
        return self._lazy_get("latest_transaction_contract_data")

    @property
    def subawards(self) -> "SubAwardsSearch":
        """Get subawards query builder for this contract award with appropriate award type filters.

        Returns a SubAwardsSearch object that can be further filtered and chained.
        Automatically applies contract award type filters.

        Examples:
            >>> contract.subawards.count()  # Get count without loading all data
            >>> contract.subawards.limit(10).all()  # Get first 10 subawards
            >>> list(contract.subawards)  # Iterate through all subawards
        """
        from ..config import CONTRACT_CODES
        
        return (self._client.subawards
                .for_award(self.generated_unique_award_id)
                .with_award_types(*CONTRACT_CODES))