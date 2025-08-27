"""Agency model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property
from dataclasses import dataclass
from ..utils.formatter import to_float, to_int
from .lazy_record import LazyRecord

if TYPE_CHECKING:
    from ..client import USASpending

# Create data class for def_codes
@dataclass
class DefCode:
    code: str
    public_law: str
    title: Optional[str] = None
    urls: Optional[List[str]] = None
    disaster: Optional[str] = None


class Agency(LazyRecord):
    """Rich wrapper around a USAspending agency record."""

    def __init__(self, data: Dict[str, Any], client: Optional[USASpending] = None):
        """Initialize Agency instance.

        Args:
            data: Agency data dictionary
            client: Optional USASpending client instance
        """
        super().__init__(data, client)

    def _fetch_details(self) -> Optional[Dict[str, Any]]:
        """Agency records are typically complete, no additional fetching needed."""
        return None

    @property
    def id(self) -> Optional[int]:
        """Agency internal ID."""
        return self._lazy_get("id")

    @property
    def has_agency_page(self) -> bool:
        """Whether this agency has a dedicated page on USASpending.gov."""
        return bool(self._lazy_get("has_agency_page", default=False))

    @property
    def office_agency_name(self) -> Optional[str]:
        """Name of the specific office within the agency."""
        return self._lazy_get("office_agency_name")

    @cached_property
    def toptier_agency(self) -> Optional[AgencyTier]:
        """Top-tier agency information."""
        data = self._data.get("toptier_agency")
        return AgencyTier(data) if data else None

    @cached_property
    def subtier_agency(self) -> Optional[AgencyTier]:
        """Sub-tier agency information."""
        data = self._data.get("subtier_agency")
        return AgencyTier(data) if data else None

    @property
    def name(self) -> Optional[str]:
        """Primary agency name (from toptier or subtier)."""
        if self.toptier_agency:
            return self.toptier_agency.name
        elif self.subtier_agency:
            return self.subtier_agency.name
        return self.office_agency_name

    @property
    def code(self) -> Optional[str]:
        """Primary agency code (from toptier or subtier)."""
        if self.toptier_agency:
            return self.toptier_agency.code
        elif self.subtier_agency:
            return self.subtier_agency.code
        return None

    @property
    def abbreviation(self) -> Optional[str]:
        """Primary agency abbreviation (from toptier or subtier)."""
        if self.toptier_agency:
            return self.toptier_agency.abbreviation
        elif self.subtier_agency:
            return self.subtier_agency.abbreviation
        return None

    @property
    def total_obligations(self) -> Optional[float]:
        """Total obligations for this agency across all awards."""
        obligations = self.get_value("total_obligations","obligations")
        return to_float(obligations)
    
    def obligations(self) -> Optional[float]:
        if ("obligations" or "total_obligations") in self.raw:
            return self.get_value("total_obligations","obligations")
        else:
            pass
    
    def transaction_count(self) -> Optional[int]:
        """Total transaction count for this agency across all awards."""
        count = self._lazy_get("transaction_count")
        return to_int(count)
    
    def new_award_count(self) -> Optional[int]:
        """Total new award count for this agency across all awards."""
        count = self._lazy_get("new_award_count")
        return to_int(count)
    
    def __repr__(self) -> str:
        """String representation of Agency."""
        name = self.name or "?"
        code = self.code or "?"
        return f"<Agency {code}: {name}>"


class AgencyTier:
    """Represents toptier or subtier agency information."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize AgencyTier instance.

        Args:
            data: Agency tier data dictionary
        """
        self._data = data

    @property
    def name(self) -> Optional[str]:
        """Agency tier name."""
        return self._data.get("name")

    @property
    def code(self) -> Optional[str]:
        """Agency tier code."""
        return self._data.get("code")

    @property
    def abbreviation(self) -> Optional[str]:
        """Agency tier abbreviation."""
        return self._data.get("abbreviation")

    @property
    def slug(self) -> Optional[str]:
        """URL slug for this agency tier."""
        return self._data.get("slug")

    def __repr__(self) -> str:
        """String representation of AgencyTier."""
        name = self.name or "?"
        code = self.code or "?"
        return f"<AgencyTier {code}: {name}>"
