"""Recipient spending model for USASpending spending by recipient data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.formatter import round_to_millions
from .recipient import Recipient
from .spending import SpendingFields

if TYPE_CHECKING:
    from ..client import USASpendingClient


class RecipientSpending(SpendingFields, Recipient):
    """Model for spending by recipient data.

    Represents spending data grouped by recipient with recipient-specific
    fields like recipient_id and UEI.
    """

    def __init__(self, data: dict, client: USASpendingClient):
        """Initialize RecipientSpending model.

        Args:
            data: Raw recipient spending data from API.
            client: USASpendingClient client instance.
        """
        super().__init__(data, client)

    @property
    def duns(self) -> str | None:
        """DUNS number (alias for code).

        Returns:
            Optional[str]: The DUNS number, or None.
        """
        return self.code

    def __repr__(self) -> str:
        """String representation of RecipientSpending.

        Returns:
            str: String containing recipient name and formatted amount.
        """
        name = self.name or "Unknown Recipient"
        formatted_amount = round_to_millions(self.amount)
        return f"<RecipientSpending {name}: {formatted_amount}>"
