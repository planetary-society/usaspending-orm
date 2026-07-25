"""State spending model for USASpending spending by state/territory data."""

from __future__ import annotations

from typing import ClassVar

from .spending import Spending


class StateSpending(Spending):
    """Model for spending by state/territory data.

    Represents spending data grouped by state/territory with
    state-specific properties.
    """

    _UNKNOWN_NAME: ClassVar[str] = "Unknown State"

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
