from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .base_model import BaseModel
from ..utils.formatter import to_date
from datetime import datetime


@dataclass()
class PeriodOfPerformance(BaseModel):
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @property
    def start_date(self) -> Optional[datetime]:
        return to_date(
            self.get_value(
                ["start_date", "Start Date", "Period of Performance Start Date"]
            )
        )

    @property
    def end_date(self) -> Optional[datetime]:
        return to_date(
            self.get_value(
                ["end_date", "End Date", "Period of Performance Current End Date"]
            )
        )

    @property
    def last_modified_date(self) -> Optional[datetime]:
        return to_date(self.get_value(["last_modified_date", "Last Modified Date"]))

    def __repr__(self) -> str:
        return f"<Period of Performance {self.start_date or '?'} -> {self.end_date or '?'}>"
