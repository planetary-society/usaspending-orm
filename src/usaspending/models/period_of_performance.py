from __future__ import annotations
from typing import Dict, Any, Optional
from .base_model import BaseModel
from ..utils.formatter import to_date
from datetime import date


class PeriodOfPerformance(BaseModel):
    def __init__(self, data: Dict[str, Any]):
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
        return self._start_date

    @property
    def end_date(self) -> Optional[date]:
        return self._end_date

    @property
    def last_modified_date(self) -> Optional[date]:
        return to_date(self.get_value(["last_modified_date", "Last Modified Date"]))

    @property
    def potential_end_date(self) -> Optional[date]:
        return to_date(
            self.get_value(
                ["potential_end_date", "Period of Performance Potential End Date"]
            )
        )

    def __repr__(self) -> str:
        return f"<Period of Performance {self._start_date or '?'} -> {self._end_date or '?'}>"
