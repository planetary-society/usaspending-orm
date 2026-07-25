"""IDV (Indefinite Delivery Vehicle) award model for USASpending data."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from .award import Award
from .procurement_award import ProcurementAward

if TYPE_CHECKING:
    from ..queries.idv_child_awards import IDVChildAwardsSearch


class IDV(ProcurementAward):
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

    Note:
        ``place_of_performance`` is typically null or all-null for an IDV, since
        the vehicle itself is not performed anywhere; the orders placed against it
        are. ``None`` is the expected result rather than missing data.

        ``naics_description`` and ``psc_description`` here read only the flat
        classification dictionary, where the Contract equivalents also fall back
        to the classification hierarchy. See :class:`ProcurementAward`.

    Example:
        >>> # Find all IDVs for an agency
        >>> idvs = (
        ...     client.awards.search()
        ...     .idvs()
        ...     .agency("National Aeronautics and Space Administration")
        ...     .all()
        ... )
        >>> for idv in idvs:
        ...     print(f"{idv.award_identifier}: ${idv.total_obligation:,.2f}")
    """

    # Download type for bulk download API
    _download_type = "idv"

    TYPE_FIELDS: ClassVar[list[str]] = [
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

    SEARCH_FIELDS: ClassVar[list[str]] = [
        *Award.SEARCH_FIELDS,
        "Start Date",
        "Award Amount",
        "Total Outlays",
        "Contract Award Type",
        "Last Date to Order",
        "NAICS",
        "PSC",
    ]

    @property
    def contract_award_type(self) -> str | None:
        """Contract award type description.

        Returns:
            Optional[str]: The contract award type, or None.
        """
        return self._lazy_get("contract_award_type", "Contract Award Type", "type_description")

    @property
    def naics_code(self) -> str | None:
        """NAICS industry classification code.

        Returns:
            Optional[str]: The NAICS code, or None.
        """
        naics_data = self._lazy_get("naics", "NAICS")
        if isinstance(naics_data, dict):
            return naics_data.get("code")
        if self.naics_hierarchy and isinstance(self.naics_hierarchy.get("base_code"), dict):
            return self.naics_hierarchy["base_code"].get("code")
        return None

    @property
    def naics_description(self) -> str | None:
        """NAICS industry classification description.

        Returns:
            Optional[str]: The NAICS description, or None.
        """
        naics_data = self._lazy_get("naics", "NAICS")
        if isinstance(naics_data, dict):
            return naics_data.get("description")
        return None

    @property
    def psc_description(self) -> str | None:
        """Product/Service Code (PSC) description.

        Returns:
            Optional[str]: The PSC description, or None.
        """
        psc_data = self._lazy_get("psc", "PSC")
        if isinstance(psc_data, dict):
            return psc_data.get("description")
        return None

    @property
    def child_awards(self) -> IDVChildAwardsSearch:
        """Query builder for child awards (delivery/task orders) under this IDV.

        Returns an IDVChildAwardsSearch query builder that can be used to
        retrieve, filter, and paginate child awards placed against this IDV.

        Examples:
            >>> idv = client.awards.find_by_generated_id("CONT_IDV_...")
            >>> # Get all child awards
            >>> for child in idv.child_awards:
            ...     print(f"{child.piid}: ${child.obligated_amount:,.2f}")
            >>>
            >>> # Paginated access
            >>> idv.child_awards.limit(10).all()
            >>>
            >>> # Count child awards
            >>> idv.child_awards.count()
            >>>
            >>> # Sort by obligation amount
            >>> idv.child_awards.order_by("obligated_amount", "desc").all()

        Returns:
            IDVChildAwardsSearch: Query builder for child awards.
        """
        from ..queries.idv_child_awards import IDVChildAwardsSearch

        return IDVChildAwardsSearch(self._client, self.generated_unique_award_id)
