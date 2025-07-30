"""Recipient spending model for USASpending spending by recipient data."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .spending import Spending

if TYPE_CHECKING:
    from ..client import USASpending


class RecipientSpending(Spending):
    """Model for spending by recipient data.
    
    Represents spending data grouped by recipient with recipient-specific 
    fields like recipient_id and UEI.
    """
    
    def __init__(self, data: dict, client: Optional["USASpending"] = None):
        """Initialize RecipientSpending model.
        
        Args:
            data: Raw recipient spending data from API
            client: USASpending client instance
        """
        super().__init__(data, client)
    
    @property
    def recipient_id(self) -> Optional[str]:
        """Unique recipient identifier including hash and level."""
        return self.get_value(["recipient_id"])
    
    @property
    def uei(self) -> Optional[str]:
        """Unique Entity Identifier for the recipient."""
        return self.get_value(["uei"])
    
    @property
    def duns(self) -> Optional[str]:
        """DUNS number for the recipient (legacy identifier)."""
        # The API documentation shows 'code' field contains DUNS for recipients
        return self.code
    
    def __repr__(self) -> str:
        """String representation of RecipientSpending."""
        name = self.name or "Unknown Recipient"
        amount = self.amount or 0
        return f"<RecipientSpending {name}: ${amount:,.2f}>"