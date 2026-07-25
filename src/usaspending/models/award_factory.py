"""Factory for creating appropriate Award subclass instances."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from ..exceptions import ValidationError
from .award_types import category_for_singular, get_award_group

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ..client import USASpendingClient
    from .award import Award


@lru_cache(maxsize=1)
def _model_classes() -> Mapping[str, type[Award]]:
    """Bind ``AwardCategory.model_name`` values to their model classes.

    The registry stores the class *name* because the models import the registry,
    so it cannot import them back. This is the one place those names are
    resolved. Imports are deferred to break the cycle, and the result is cached
    so the resolution is paid once per process rather than per award.

    Returns:
        Mapping[str, type[Award]]: Model class by registry ``model_name``.
    """
    from types import MappingProxyType

    from .contract import Contract
    from .grant import Grant
    from .idv import IDV
    from .loan import Loan

    return MappingProxyType({"Contract": Contract, "IDV": IDV, "Grant": Grant, "Loan": Loan})


def model_for_name(model_name: str | None) -> type[Award]:
    """Resolve a registry ``model_name`` to its model class.

    Args:
        model_name: Name from :attr:`AwardCategory.model_name` or
            :attr:`AwardCategory.search_fields_model`, or None.

    Returns:
        type[Award]: The named model class, or the base ``Award`` when the name
        is None or unrecognized.
    """
    from .award import Award

    if model_name is None:
        return Award
    return _model_classes().get(model_name, Award)


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

    # If it's just an ID, create base Award and let lazy loading determine type
    if isinstance(data_or_id, str):
        return Award(data_or_id, client)

    if not isinstance(data_or_id, dict):
        raise ValidationError("Award factory expects a dict or an award_id string")

    # Try category field first, then type code
    group = get_award_group(data_or_id.get("category", ""))
    if not group:
        group = get_award_group(data_or_id.get("type") or data_or_id.get("award_type") or "")

    category = category_for_singular(group)
    cls = model_for_name(category.model_name) if category else Award
    return cls(data_or_id, client)
