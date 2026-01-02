"""Factory for creating appropriate Award subclass instances."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..exceptions import ValidationError
from .award_types import get_award_group

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from .award import Award


def create_award(data_or_id: dict[str, Any] | str, client: USASpendingClient) -> Award:
    """Create the appropriate Award subclass based on the award data.

    Args:
        data_or_id: Award data dictionary or unique award ID string.
        client: USASpendingClient instance.

    Returns:
        Award: Appropriate Award subclass instance (Contract, Grant, IDV, Loan, or base Award).

    Raises:
        ValidationError: If input is neither a dictionary nor a string.
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

    award_class_map = {
        "contract": Contract,
        "idv": IDV,
        "grant": Grant,
        "loan": Loan,
    }

    # Try category field first, then type code
    group = get_award_group(data_or_id.get("category", ""))
    if not group:
        group = get_award_group(data_or_id.get("type") or data_or_id.get("award_type") or "")

    cls = award_class_map.get(group, Award)
    return cls(data_or_id, client)
