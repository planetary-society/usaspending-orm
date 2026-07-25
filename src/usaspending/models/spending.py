"""Shared fields and base model for USASpending spending by category data."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from ..utils.formatter import to_decimal
from .base_model import BaseModel

if TYPE_CHECKING:
    from ..client import USASpendingClient


class SpendingMixin:
    """Fields shared by every spending-by-category result.

    ``RecipientSpending`` must subclass :class:`Recipient` rather than
    :class:`Spending`, so these four accessors would otherwise be duplicated
    verbatim across the two hierarchies. Compose this ahead of the model base.

    Deliberately excludes ``name``, ``id`` and ``category``: ``Recipient.name``
    applies title casing, and a mixin ahead of it in the MRO would shadow that.
    """

    @property
    def code(self) -> str | None:
        """Code associated with the spending record (DUNS, district code, etc.).

        Returns:
            Optional[str]: The code, or None.
        """
        return self.get_value("code")

    @property
    def amount(self) -> Decimal | None:
        """Total spending amount for this record.

        Returns:
            Optional[Decimal]: The total amount, or None.
        """
        return to_decimal(self.get_value("amount"))

    @property
    def total_outlays(self) -> Decimal | None:
        """Total outlays for this spending record.

        Returns:
            Optional[Decimal]: The total outlays, or None.
        """
        return to_decimal(self.get_value("total_outlays"))

    @property
    def spending_level(self) -> str | None:
        """The spending level used for this data (transactions, awards, subawards).

        Returns:
            Optional[str]: The spending level, or None.
        """
        return self.get_value("spending_level")


class Spending(SpendingMixin, BaseModel):
    """Base model for spending by category data.

    Represents common fields across spending by recipient and district categories.
    This model provides access to spending data with amounts, names, codes, and outlays.

    Note:
        The client is held as a plain attribute rather than through
        ``ClientAwareModel``. No property on this model or its subclasses issues
        a request, so the weakref indirection would add a
        ``DetachedInstanceError`` path with nothing to protect.
    """

    #: Name shown by ``__repr__`` when the record carries none.
    _UNKNOWN_NAME: ClassVar[str] = "Unknown"

    def __init__(self, data: dict, client: USASpendingClient | None = None):
        """Initialize Spending model.

        Args:
            data: Raw spending data from API.
            client: USASpendingClient client instance.
        """
        super().__init__(data)
        self._client = client

    @property
    def id(self) -> int | None:
        """Database ID for the spending record.

        Returns:
            Optional[int]: The database ID, or None.
        """
        return self.get_value("id")

    @property
    def name(self) -> str | None:
        """Display name for the spending category (recipient name or district name).

        Returns:
            Optional[str]: The name, or None.
        """
        return self.get_value("name")

    @property
    def category(self) -> str | None:
        """The category type (recipient or district).

        Returns:
            Optional[str]: The category type, or None.
        """
        return self.get_value("category")

    def __repr__(self) -> str:
        """String representation of the spending record.

        Subclasses override :attr:`_UNKNOWN_NAME` rather than this method, since
        the class name is read from the instance.

        Returns:
            str: String containing name and amount.
        """
        return (
            f"<{type(self).__name__} {self.name or self._UNKNOWN_NAME}: ${self.amount or 0:,.2f}>"
        )
