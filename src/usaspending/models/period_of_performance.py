from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from ..utils.formatter import to_float
from datetime import datetime

@dataclass(slots=True)
class PeriodOfPerformance:
    _raw: Dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def start_date(self) -> Optional[str]:
        return self._raw.get(self._raw, "start_date", "Start Date", "Period of Performance Start Date")

    @property
    def end_date(self) -> Optional[str]:
        return self._raw.get(self._raw, "end_date", "End Date", "Period of Performance Current End Date")

    @property
    def last_modified_date(self) -> Optional[str]:
        return self._raw.get(self._raw, "last_modified_date", "Last Modified Date")

    @property
    def raw(self) -> Dict[str, Any]:  return self._raw

    def to_dict(self) -> dict:
        return self._raw

    def __repr__(self) -> str:
        return f"<Period {self.start_date or '?'} → {self.end_date or '?'}>"