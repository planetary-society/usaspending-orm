"""State spending model for USASpending spending by state/territory data."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .spending import Spending

if TYPE_CHECKING:
    from ..client import USASpendingClient


class StateSpending(Spending):
    """Model for spending by state/territory data.

    Represents spending data grouped by state/territory with
    state-specific properties.
    """

    def __init__(self, data: dict, client: Optional["USASpendingClient"] = None):
        """Initialize StateSpending model.

        Args:
            data: Raw state spending data from API
            client: USASpendingClient client instance
        """
        super().__init__(data, client)

    @property
    def state_code(self) -> Optional[str]:
        """State/territory code (e.g., 'WA', 'CA')."""
        return self.code

    @property
    def state_name(self) -> Optional[str]:
        """Full state/territory name (e.g., 'Washington')."""
        return self.name

    def __repr__(self) -> str:
        """String representation of StateSpending."""
        name = self.state_name or "Unknown State"
        amount = self.amount or 0
        return f"<StateSpending {name}: ${amount:,.2f}>"
