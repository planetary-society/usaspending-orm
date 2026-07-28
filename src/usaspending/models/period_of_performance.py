from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

from ..utils.dates import to_date
from .base_model import BaseModel


class PeriodOfPerformance(BaseModel):
    """Period of Performance model for USASpending data.

    Represents the time period during which the work of an award is expected
    to be performed or the funding is available for obligation.

    An award search result reports these dates as flat, title-cased keys rather
    than as the nested object a detail response sends. Both spellings are read
    here, so an award holding a search result can hand its payload over via
    :meth:`_from_search_result` rather than translating the keys itself.
    """

    #: The flat keys an award search result carries for its period of performance.
    #: Every one is read by a property below, and this is the projection
    #: :meth:`_from_search_result` copies.
    _SEARCH_KEYS: ClassVar[tuple[str, ...]] = (
        "Start Date",
        "Base Obligation Date",
        "End Date",
        "Period of Performance Current End Date",
        "Period of Performance Potential End Date",
        "Last Modified Date",
    )

    @classmethod
    def _from_search_result(cls, data: dict[str, Any]) -> PeriodOfPerformance:
        """Build from an award search result, taking only the keys this model owns.

        Copies rather than aliasing: an award replaces its payload in place when a
        detail fetch fires, and this model reads some of its dates lazily, so a
        shared reference would let that fetch change an object already built.

        Args:
            data: An award search result, whose other keys are ignored.

        Returns:
            PeriodOfPerformance: A model whose ``raw`` holds only period data.
        """
        return cls({key: data[key] for key in cls._SEARCH_KEYS if key in data})

    def __init__(self, data: dict[str, Any]):
        """Initialize PeriodOfPerformance.

        Args:
            data: Dictionary containing period of performance data.
        """
        super().__init__(data)
        self._start_date = to_date(
            self.get_value(
                [
                    "start_date",
                    "Start Date",
                    "Period of Performance Start Date",
                    "Base Obligation Date",
                ]
            )
        )
        self._end_date = to_date(
            self.get_value(["end_date", "End Date", "Period of Performance Current End Date"])
        )

    @property
    def start_date(self) -> date | None:
        """Start date of the period of performance.

        Returns:
            Optional[date]: The start date, or None.
        """
        return self._start_date

    @property
    def end_date(self) -> date | None:
        """Current end date of the period of performance.

        Returns:
            Optional[date]: The current end date, or None.
        """
        return self._end_date

    @property
    def last_modified_date(self) -> date | None:
        """Date when the period of performance was last modified.

        Returns:
            Optional[date]: The last modified date, or None.
        """
        return to_date(self.get_value(["last_modified_date", "Last Modified Date"]))

    @property
    def potential_end_date(self) -> date | None:
        """Potential end date if all options are exercised.

        Returns:
            Optional[date]: The potential end date, or None.
        """
        return to_date(
            self.get_value(["potential_end_date", "Period of Performance Potential End Date"])
        )

    def __repr__(self) -> str:
        """String representation of PeriodOfPerformance.

        Returns:
            str: String formatted as "<Period of Performance START -> END>".
        """
        return f"<Period of Performance {self._start_date or '?'} -> {self._end_date or '?'}>"
