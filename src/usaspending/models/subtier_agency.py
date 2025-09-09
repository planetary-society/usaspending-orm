"""SubTier Agency model for USASpending sub-agency data."""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING, Dict, Any
from decimal import Decimal
from ..utils.formatter import to_decimal, to_int, contracts_titlecase
from .base_model import BaseModel

if TYPE_CHECKING:
    from ..client import USASpending


class SubTierAgency(BaseModel):
    """Rich wrapper around a USAspending subtier agency record.
    
    This model represents a subtier agency with its essential properties,
    including nested office information.
    """

    def __init__(self, data: Dict[str, Any], client: Optional["USASpending"] = None):
        """Initialize SubTierAgency model.

        Args:
            data: Raw sub-agency data from API
            client: USASpending client instance
        """
        # Check if this data includes office_agency_name (from award context)
        office_agency_name = data.get("office_agency_name")
        if office_agency_name and "children" not in data:
            # Create a synthetic child office from office_agency_name
            office_child = {
                "name": contracts_titlecase(office_agency_name)
            }
            # Create a copy of data with the office child
            data = data.copy()
            data["children"] = [office_child]
        
        super().__init__(data)
        self._client = client
    
    @property
    def name(self) -> Optional[str]:
        """Name of the subtier agency."""
        return contracts_titlecase(self.get_value("name"))
    
    @property
    def code(self) -> Optional[str]:
        """Code of the subtier agency."""
        return self.get_value("code")
    
    @property
    def abbreviation(self) -> Optional[str]:
        """Abbreviation of the subtier agency."""
        return self.get_value("abbreviation")
    
    @property
    def total_obligations(self) -> Optional[Decimal]:
        """Total obligations for this subtier agency."""
        obligations = self.get_value("total_obligations")
        return to_decimal(obligations)
    
    @property
    def transaction_count(self) -> Optional[int]:
        """Number of transactions for this subtier agency."""
        count = self.get_value("transaction_count")
        return to_int(count)
    
    @property
    def new_award_count(self) -> Optional[int]:
        """Number of new awards for this subtier agency."""
        count = self.get_value("new_award_count")
        return to_int(count)
    
    @property
    def offices(self) -> List["SubTierAgency"]:
        """List of offices under this subtier agency.
        
        Returns:
            List of SubTierAgency instances representing offices
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
        """String representation of SubTierAgency."""
        name = self.name or "?"
        code = self.code or "?"
        return f"<SubTierAgency {code}: {name}>"

