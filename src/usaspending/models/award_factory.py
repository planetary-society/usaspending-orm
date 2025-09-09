"""Factory for creating appropriate Award subclass instances."""

from __future__ import annotations
from typing import Dict, Any, Optional, TYPE_CHECKING

from .award_types import get_category_for_code
from ..exceptions import ValidationError

if TYPE_CHECKING:
    from .award import Award
    from ..client import USASpendingClient


def create_award(
    data_or_id: Dict[str, Any] | str, client: Optional[USASpendingClient] = None
) -> Award:
    """
    Factory function to create the appropriate Award subclass based on the award data.

    Args:
        data_or_id: Award data dictionary or unique award ID string
        client: Optional USASpendingClient instance

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

    award_class_map = {
        "contract": Contract,
        "idv": IDV,
        "grant": Grant,
        "loan": Loan,
    }

    # Determine class from category first (most reliable)
    award_class = award_class_map.get(category)

    # Fallback to type codes if category doesn't match
    if not award_class and award_type:
        code_category = get_category_for_code(award_type)
        if code_category:
            # Map config category names to award class names
            category_map = {
                "contracts": "contract",
                "idvs": "idv",
                "grants": "grant",
                "loans": "loan",
            }
            mapped_category = category_map.get(code_category)
            if mapped_category:
                award_class = award_class_map.get(mapped_category)

    # Use the determined class or default to the base Award class
    cls = award_class or Award
    return cls(data_or_id, client)
