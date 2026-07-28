"""Recipient spending model for USASpending spending by recipient data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.numbers import round_to_millions
from .recipient import Recipient
from .spending import SpendingFields

if TYPE_CHECKING:
    from ..client import USASpendingClient


class RecipientSpending(SpendingFields, Recipient):
    """Model for spending by recipient data.

    Represents spending data grouped by recipient with recipient-specific
    fields like recipient_id and UEI.

    Warning:
        Half of the inherited accessors cost one API request each, per row, and
        the cost is not visible at the call site. ``/search/spending_by_category/
        recipient/`` returns six fields per row, so anything beyond them is
        lazy-loaded from ``/recipient/{id}/``:

        Served by the row, free
            ``amount``, ``code``, ``duns``, ``name``, ``recipient_id``,
            ``spending_level``, ``total_outlays``, ``uei``, ``raw``

        One request each, per row
            ``alternate_names``, ``business_categories``, ``business_types``,
            ``location``, ``parent``, ``parents``, ``recipient_level``,
            ``total_face_value_loan_amount``,
            ``total_face_value_loan_transactions``,
            ``total_transaction_amount``, ``total_transactions``

        So ``[row.location for row in page]`` is one request per row. That is the
        API's shape rather than this class's: the recipient *list* endpoint carries
        the same six-ish fields, so no bulk call supplies the rest, and reaching
        them through an explicit association instead was measured to save exactly
        zero requests. Read the free fields freely; treat the others as a
        deliberate per-recipient fetch.
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
