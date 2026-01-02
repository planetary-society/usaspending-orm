"""SubTier Agency model for USASpending sub-agency data."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from ..utils.formatter import contracts_titlecase, to_decimal, to_int
from .base_model import BaseModel

if TYPE_CHECKING:
    from ..client import USASpendingClient


class SubTierAgency(BaseModel):
    """Rich wrapper around a USAspending subtier agency record.

    This model represents a subtier agency with its essential properties,
    including nested office information.
    """

    def __init__(
        self, data: dict[str, Any], client: USASpendingClient | None = None
    ):
        """Initialize SubTierAgency model.

        Args:
            data: Raw sub-agency data from API.
            client: USASpendingClient client instance.
        """
        # Check if this data includes office_agency_name (from award context)
        office_agency_name = data.get("office_agency_name")
        if office_agency_name and "children" not in data:
            # Create a synthetic child office from office_agency_name
            office_child = {"name": contracts_titlecase(office_agency_name)}
            # Create a copy of data with the office child
            data = data.copy()
            data["children"] = [office_child]

        super().__init__(data)
        self._client = client

    @property
    def name(self) -> str | None:
        """Name of the subtier agency.

        Returns:
            Optional[str]: The name of the subtier agency, or None.
        """
        return contracts_titlecase(self.get_value("name"))

    @property
    def code(self) -> str | None:
        """Code of the subtier agency.

        Returns:
            Optional[str]: The subtier agency code, or None.
        """
        return self.get_value("code")

    @property
    def abbreviation(self) -> str | None:
        """Abbreviation of the subtier agency.

        Returns:
            Optional[str]: The subtier agency abbreviation, or None.
        """
        return self.get_value("abbreviation")

    @property
    def total_obligations(self) -> Decimal | None:
        """Total obligations for this subtier agency.

        Returns:
            Optional[Decimal]: The total obligations, or None.
        """
        obligations = self.get_value("total_obligations")
        return to_decimal(obligations)

    @property
    def transaction_count(self) -> int | None:
        """Number of transactions for this subtier agency.

        Returns:
            Optional[int]: The transaction count, or None.
        """
        count = self.get_value("transaction_count")
        return to_int(count)

    @property
    def new_award_count(self) -> int | None:
        """Number of new awards for this subtier agency.

        Returns:
            Optional[int]: The new award count, or None.
        """
        count = self.get_value("new_award_count")
        return to_int(count)

    @property
    def offices(self) -> list[SubTierAgency]:
        """List of offices under this subtier agency.

        Returns:
            List[SubTierAgency]: A list of SubTierAgency instances representing offices.
        """
        children_data = self.get_value("children", default=[])
        if not isinstance(children_data, list):
            return []

        offices = []
        for office_data in children_data:
            if isinstance(office_data, dict):
                office = SubTierAgency(office_data, self._client)
                offices.append(office)

        return offices

    def __repr__(self) -> str:
        """String representation of SubTierAgency.

        Returns:
            str: String containing the agency code and name.
        """
        name = self.name or "?"
        code = self.code or "?"
        return f"<SubTierAgency {code}: {name}>"
