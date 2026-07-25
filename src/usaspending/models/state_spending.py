"""State spending model for USASpending spending by state/territory data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .spending import Spending

if TYPE_CHECKING:
    pass


class StateSpending(Spending):
    """Model for spending by state/territory data.

    Represents spending data grouped by state/territory with
    state-specific properties.
    """

    @property
    def state_code(self) -> str | None:
        """State/territory code (e.g., 'WA', 'CA').

        Returns:
            Optional[str]: The state code, or None.
        """
        return self.code

    @property
    def state_name(self) -> str | None:
        """Full state/territory name (e.g., 'Washington').

        Returns:
            Optional[str]: The state name, or None.
        """
        return self.name

    def __repr__(self) -> str:
        """String representation of StateSpending.

        Returns:
            str: String containing state name and amount.
        """
        name = self.state_name or "Unknown State"
        amount = self.amount or 0
        return f"<StateSpending {name}: ${amount:,.2f}>"
