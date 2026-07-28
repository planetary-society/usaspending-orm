"""Contract award model for USASpending data."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from .award import Award
from .procurement_award import ProcurementAward

if TYPE_CHECKING:
    from ..queries.subawards_search import SubAwardsSearch


class Contract(ProcurementAward):
    """Contract award type including definitive contracts and purchase orders."""

    # Download type for bulk download API
    _download_type = "contract"

    TYPE_FIELDS: ClassVar[list[str]] = [
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

    SEARCH_FIELDS: ClassVar[list[str]] = [
        *Award.SEARCH_FIELDS,
        "Start Date",
        "End Date",
        "Award Amount",
        "Total Outlays",
        "Contract Award Type",
        "NAICS",
        "PSC",
    ]

    @property
    def contract_award_type(self) -> str | None:
        """Contract award type description.

        Returns:
            Optional[str]: The contract award type description, or None.
        """
        return self.type_description

    @property
    def naics_code(self) -> str | None:
        """NAICS industry classification code.

        Falls back to the classification hierarchy, and then to the latest
        contract transaction, where the IDV equivalent stops sooner.

        Returns:
            Optional[str]: The NAICS code, or None.
        """
        naics_data = self._lazy_get("naics", "NAICS")
        if isinstance(naics_data, dict):
            return naics_data.get("code")
        if self.naics_hierarchy and isinstance(self.naics_hierarchy.get("base_code"), dict):
            return self.naics_hierarchy["base_code"].get("code")
        if self.latest_transaction_contract_data:
            return self.latest_transaction_contract_data.get("naics")
        return None

    @property
    def naics_description(self) -> str | None:
        """NAICS industry classification description.

        Falls back to the classification hierarchy, and then to the latest
        contract transaction, where the IDV equivalent stops sooner.

        Returns:
            Optional[str]: The NAICS description, or None.
        """
        naics_data = self._lazy_get("naics", "NAICS")
        if isinstance(naics_data, dict):
            return naics_data.get("description")
        if self.naics_hierarchy and isinstance(self.naics_hierarchy.get("base_code"), dict):
            return self.naics_hierarchy["base_code"].get("description")
        if self.latest_transaction_contract_data:
            return self.latest_transaction_contract_data.get("naics_description")
        return None

    @property
    def psc_description(self) -> str | None:
        """Product/Service Code (PSC) description.

        Falls back to the classification hierarchy, where the IDV equivalent
        reads only the flat dictionary.

        Returns:
            Optional[str]: The PSC description, or None.
        """
        psc_data = self._lazy_get("psc", "PSC")
        if isinstance(psc_data, dict):
            return psc_data.get("description")
        if self.psc_hierarchy and isinstance(self.psc_hierarchy.get("base_code"), dict):
            return self.psc_hierarchy["base_code"].get("description")
        return None

    @property
    def subawards(self) -> SubAwardsSearch:
        """Get subawards query builder for this contract award with appropriate award type filters.

        Automatically applies contract award type filters.

        Examples:
            >>> contract.subawards.count()  # Get count without loading all data
            >>> contract.subawards.limit(10).all()  # Get first 10 subawards
            >>> contract.subawards.all()  # Every subaward, as a list

        Returns:
            SubAwardsSearch: A query builder object for subawards.
        """
        from .award_types import CONTRACT_CODES

        return self._client.subawards.award_id(self.generated_unique_award_id).award_type_codes(
            *CONTRACT_CODES
        )
