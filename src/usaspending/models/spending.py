"""Base spending model for USASpending spending by category data."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from ..utils.formatter import to_decimal
from .base_model import BaseModel

if TYPE_CHECKING:
    from ..client import USASpending


class Spending(BaseModel):
    """Base model for spending by category data.

    Represents common fields across spending by recipient and district categories.
    This model provides access to spending data with amounts, names, codes, and outlays.
    """

    def __init__(self, data: dict, client: Optional["USASpending"] = None):
        """Initialize Spending model.

        Args:
            data: Raw spending data from API
            client: USASpending client instance
        """
        super().__init__(data)
        self._client = client

    @property
    def id(self) -> Optional[int]:
        """Database ID for the spending record."""
        return self.get_value(["id"])

    @property
    def name(self) -> Optional[str]:
        """Display name for the spending category (recipient name or district name)."""
        return self.get_value(["name"])

    @property
    def code(self) -> Optional[str]:
        """Code associated with the spending record (DUNS, district code, etc.)."""
        return self.get_value(["code"])

    @property
    def amount(self) -> Optional[Decimal]:
        """Total spending amount for this record."""
        return to_decimal(self.get_value(["amount"]))

    @property
    def total_outlays(self) -> Optional[Decimal]:
        """Total outlays for this spending record."""
        return to_decimal(self.get_value(["total_outlays"]))

    @property
    def spending_level(self) -> Optional[str]:
        """The spending level used for this data (transactions, awards, subawards)."""
        return self.get_value(["spending_level"])

    @property
    def category(self) -> Optional[str]:
        """The category type (recipient or district)."""
        return self.get_value(["category"])

    def __repr__(self) -> str:
        """String representation of Spending."""
        name = self.name or "Unknown"
        amount = self.amount or 0
        return f"<Spending {name}: ${amount:,.2f}>"
