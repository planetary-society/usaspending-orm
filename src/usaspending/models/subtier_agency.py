"""Base spending model for USASpending spending by category data."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from ..utils.formatter import to_float
from .base_model import BaseModel

if TYPE_CHECKING:
    from ..client import USASpending


class SubTierAgency(BaseModel):
    def __init__(self, data: dict, client: Optional["USASpending"] = None):
        """Initialize SubAgency model.

        Args:
            data: Raw sub-agency data from API
            client: USASpending client instance
        """
        super().__init__(data)
        self._client = client
    
    @property
    def name(self) -> Optional[str]:
        """Name of the subtier agency."""
        return self.get_value(["name"])
    
    @property
    def code(self) -> Optional[str]:
        """Code of the subtier agency."""
        return self.get_value(["code"])
    
    @property
    def abbreviation(self) -> Optional[str]:
        """Abbreviation of the subtier agency."""
        return self.get_value(["abbreviation"])

