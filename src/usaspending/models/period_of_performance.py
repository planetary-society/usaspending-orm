from __future__ import annotations
from typing import Dict, Any, Optional
from .base_model import BaseModel
from ..utils.formatter import to_date
from datetime import date


class PeriodOfPerformance(BaseModel):
    """Period of Performance model for USASpending data.

    Represents the time period during which the work of an award is expected
    to be performed or the funding is available for obligation.
    """

    def __init__(self, data: Dict[str, Any]):
        """Initialize PeriodOfPerformance.

        Args:
            data: Dictionary containing period of performance data.
        """
        super().__init__(data)
        self._start_date = to_date(
            self.get_value(
                ["start_date", "Start Date", "Period of Performance Start Date"]
            )
        )
        self._end_date = to_date(
            self.get_value(
                ["end_date", "End Date", "Period of Performance Current End Date"]
            )
        )

    @property
    def start_date(self) -> Optional[date]:
        """Start date of the period of performance.

        Returns:
            Optional[date]: The start date, or None.
        """
        return self._start_date

    @property
    def end_date(self) -> Optional[date]:
        """Current end date of the period of performance.

        Returns:
            Optional[date]: The current end date, or None.
        """
        return self._end_date

    @property
    def last_modified_date(self) -> Optional[date]:
        """Date when the period of performance was last modified.

        Returns:
            Optional[date]: The last modified date, or None.
        """
        return to_date(self.get_value(["last_modified_date", "Last Modified Date"]))

    @property
    def potential_end_date(self) -> Optional[date]:
        """Potential end date if all options are exercised.

        Returns:
            Optional[date]: The potential end date, or None.
        """
        return to_date(
            self.get_value(
                ["potential_end_date", "Period of Performance Potential End Date"]
            )
        )

    def __repr__(self) -> str:
        """String representation of PeriodOfPerformance.

        Returns:
            str: String formatted as "<Period of Performance START -> END>".
        """
        return f"<Period of Performance {self._start_date or '?'} -> {self._end_date or '?'}>"
