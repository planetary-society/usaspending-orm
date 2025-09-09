"""Recipient spending model for USASpending spending by recipient data."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from ..utils.formatter import to_decimal, round_to_millions
from .recipient import Recipient

if TYPE_CHECKING:
    from ..client import USASpending


class RecipientSpending(Recipient):
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
    def duns(self) -> Optional[str]:
        """DUNS number from spending data (stored in 'code' field)."""
        return self.get_value(["code"], default=None)

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

    def __repr__(self) -> str:
        """String representation of RecipientSpending."""
        name = self.name or "Unknown Recipient"
        formatted_amount = round_to_millions(self.amount) or 0
        return f"<RecipientSpending {name}: {formatted_amount}>"
