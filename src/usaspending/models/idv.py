"""IDV (Indefinite Delivery Vehicle) award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional
from functools import cached_property
from decimal import Decimal

from .award import Award
from .location import Location
from ..utils.formatter import to_decimal


class IDV(Award):
    """Indefinite Delivery Vehicle (IDV) award type.

    IDVs are contract vehicles that provide for an indefinite quantity of supplies
    or services during a fixed period of time. They establish broad parameters and
    terms for ordering supplies/services, with specific orders placed against them
    via delivery orders or task orders.

    Common IDV types include:
    - GWAC (Government-Wide Acquisition Contract)
    - IDC (Indefinite Delivery Contract)
    - FSS (Federal Supply Schedule)
    - BOA (Basic Ordering Agreement)
    - BPA (Blanket Purchase Agreement)

    IDVs serve as parent contracts that streamline procurement by pre-negotiating
    terms, conditions, and pricing for future orders. They reduce administrative
    costs and enable faster acquisition of recurring needs.

    Example:
        >>> # Find all IDVs for an agency
        >>> idvs = client.awards.search().idvs().agency("NASA").all()
        >>> for idv in idvs:
        ...     print(f"{idv.piid}: {idv.recipient_name} - ${idv.total_obligation:,.2f}")
    """

    TYPE_FIELDS = [
        "piid",
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
        "Award Amount",
        "Total Outlays",
        "Contract Award Type",
        "Last Date to Order",
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
    def base_and_all_options(self) -> Optional[Decimal]:
        """Total contract value including options and potential orders.

        For IDVs, this is the mutually agreed upon total contract value including
        all options (if any) AND the estimated value of all potential orders. For
        modifications, this reflects the change, positive or negative, of these values.

        Returns:
            Optional[Decimal]: The total contract value including options, or None.
        """
        return to_decimal(self._lazy_get("base_and_all_options", default=None))

    @property
    def base_exercised_options(self) -> Optional[Decimal]:
        """Value for the base contract and any exercised options.

        Returns:
            Optional[Decimal]: The base and exercised options value, or None.
        """
        return to_decimal(self._lazy_get("base_exercised_options", default=None))

    @property
    def contract_award_type(self) -> Optional[str]:
        """Contract award type description.

        Returns:
            Optional[str]: The contract award type, or None.
        """
        return self._lazy_get(
            "contract_award_type", "Contract Award Type", "type_description"
        )

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

    @cached_property
    def place_of_performance(self) -> Optional[Location]:
        """Award place of performance location.

        Note: IDVs typically have null or empty place_of_performance data.

        Returns:
            Optional[Location]: The location object, or None if data is missing/empty.
        """
        data = self._lazy_get(
            "place_of_performance", "Primary Place of Performance", default=None
        )
        if not isinstance(data, dict) or not data:
            return None

        # Check if all values in the dict are None/null (common for IDV awards)
        if all(v is None for v in data.values()):
            return None

        return Location(data, self._client)
