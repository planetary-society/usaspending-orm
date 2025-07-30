"""Factory for creating appropriate Award subclass instances."""

from __future__ import annotations
from typing import Dict, Any, Optional, TYPE_CHECKING

from ..config import (
    CONTRACT_CODES, IDV_CODES, GRANT_CODES, 
    LOAN_CODES, DIRECT_PAYMENT_CODES, OTHER_CODES
)
from ..exceptions import ValidationError

if TYPE_CHECKING:
    from ..client import USASpending
    from .award import Award


def create_award(data_or_id: Dict[str, Any] | str, client: Optional[USASpending] = None) -> Award:
    """
    Factory function to create the appropriate Award subclass based on the award data.
    
    Args:
        data_or_id: Award data dictionary or unique award ID string
        client: Optional USASpending client instance
        
    Returns:
        Appropriate Award subclass instance (Contract, Grant, IDV, Loan, or base Award)
    """
    # Import here to avoid circular imports
    from .award import Award
    from .contract import Contract
    from .grant import Grant
    from .idv import IDV
    from .loan import Loan
    
    # If it's just an ID, create base Award and let lazy loading determine type
    if isinstance(data_or_id, str):
        return Award(data_or_id, client)
    
    if not isinstance(data_or_id, dict):
        raise ValidationError("Award factory expects a dict or an award_id string")
    
    # Determine award type from data
    category = data_or_id.get("category", "").lower()
    award_type = data_or_id.get("type", "")
    
    # Use category first (most reliable)
    if category == "contract":
        return Contract(data_or_id, client)
    elif category == "idv":
        return IDV(data_or_id, client)
    elif category == "grant":
        return Grant(data_or_id, client)
    elif category == "loan":
        return Loan(data_or_id, client)
    
    # Fallback to type codes
    if award_type in CONTRACT_CODES:
        return Contract(data_or_id, client)
    elif award_type in IDV_CODES:
        return IDV(data_or_id, client)
    elif award_type in GRANT_CODES or award_type in DIRECT_PAYMENT_CODES or award_type in OTHER_CODES:
        return Grant(data_or_id, client)  # Grants handle all assistance types
    elif award_type in LOAN_CODES:
        return Loan(data_or_id, client)
    
    # Default to base Award if type cannot be determined
    return Award(data_or_id, client)