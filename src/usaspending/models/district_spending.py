"""District spending model for USASpending spending by district data."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .spending import Spending

if TYPE_CHECKING:
    from ..client import USASpending


class DistrictSpending(Spending):
    """Model for spending by congressional district data.
    
    Represents spending data grouped by congressional district with 
    district-specific parsing and display logic.
    """
    
    def __init__(self, data: dict, client: Optional["USASpending"] = None):
        """Initialize DistrictSpending model.
        
        Args:
            data: Raw district spending data from API
            client: USASpending client instance
        """
        super().__init__(data, client)
    
    @property
    def district_code(self) -> Optional[str]:
        """Congressional district code."""
        return self.code
    
    @property
    def state_code(self) -> Optional[str]:
        """Extract state code from district name if available.
        
        District names typically follow format like 'TX-12' or 'MS-MULTIPLE DISTRICTS'.
        """
        if self.name:
            # Names like "TX-12" or "MS-MULTIPLE DISTRICTS"
            parts = self.name.split("-", 1)
            if len(parts) >= 2:
                return parts[0]
        return None
    
    @property
    def district_number(self) -> Optional[str]:
        """Extract district number from district name if available.
        
        Returns the numeric part or special designation like 'MULTIPLE DISTRICTS'.
        """
        if self.name:
            # Names like "TX-12" or "MS-MULTIPLE DISTRICTS"  
            parts = self.name.split("-", 1)
            if len(parts) >= 2:
                return parts[1]
        return None
    
    @property
    def is_multiple_districts(self) -> bool:
        """Check if this represents multiple districts in a state."""
        district_num = self.district_number
        return district_num is not None and "MULTIPLE" in district_num.upper()
    
    def __repr__(self) -> str:
        """String representation of DistrictSpending."""
        name = self.name or "Unknown District"
        amount = self.amount or 0
        return f"<DistrictSpending {name}: ${amount:,.2f}>"