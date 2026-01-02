"""Recipient spending model for USASpending spending by recipient data."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from ..utils.formatter import round_to_millions, to_decimal
from .recipient import Recipient

if TYPE_CHECKING:
    from ..client import USASpendingClient


class RecipientSpending(Recipient):
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

    @property
    def code(self) -> str | None:
        """DUNS number from spending data (stored in 'code' field).

        Returns:
            Optional[str]: The DUNS number, or None.
        """
        return self.get_value(["code"], default=None)

    @property
    def amount(self) -> Decimal | None:
        """Total spending amount for this record.

        Returns:
            Optional[Decimal]: The total amount, or None.
        """
        return to_decimal(self.get_value(["amount"]))

    @property
    def total_outlays(self) -> Decimal | None:
        """Total outlays for this spending record.

        Returns:
            Optional[Decimal]: The total outlays, or None.
        """
        return to_decimal(self.get_value(["total_outlays"]))

    @property
    def spending_level(self) -> str | None:
        """The spending level used for this data (transactions, awards, subawards).

        Returns:
            Optional[str]: The spending level, or None.
        """
        return self.get_value(["spending_level"])

    def __repr__(self) -> str:
        """String representation of RecipientSpending.

        Returns:
            str: String containing recipient name and formatted amount.
        """
        name = self.name or "Unknown Recipient"
        formatted_amount = round_to_millions(self.amount) or 0
        return f"<RecipientSpending {name}: {formatted_amount}>"
