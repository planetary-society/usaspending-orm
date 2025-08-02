from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Literal, Optional

# ==============================================================================
# Award Type Code Constants
# ==============================================================================

# Contract award type codes
CONTRACT_CODES = frozenset({"A", "B", "C", "D"})

# IDV award type codes
IDV_CODES = frozenset(
    {"IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"}
)

# Loan award type codes
LOAN_CODES = frozenset({"07", "08"})

# Grant award type codes
GRANT_CODES = frozenset({"02", "03", "04", "05"})

# Direct payment award type codes
DIRECT_PAYMENT_CODES = frozenset({"06", "10"})

# Other award type codes that do not fit into the above categories
OTHER_CODES = frozenset({"09", "11", "-1"})

# All valid award type codes
ALL_AWARD_CODES = CONTRACT_CODES | IDV_CODES | LOAN_CODES | GRANT_CODES

# ==============================================================================
# Helper Enums and Dataclasses
# ==============================================================================


class AgencyType(Enum):
    """Enumeration for agency types."""

    AWARDING = "awarding"
    FUNDING = "funding"


class AgencyTier(Enum):
    """Enumeration for agency tiers."""

    TOPTIER = "toptier"
    SUBTIER = "subtier"


class LocationScope(Enum):
    """Enumeration for location scopes."""

    DOMESTIC = "domestic"
    FOREIGN = "foreign"


class AwardDateType(Enum):
    """Enumeration for award search date types."""

    ACTION_DATE = "action_date"
    DATE_SIGNED = "date_signed"
    LAST_MODIFIED = "last_modified_date"
    NEW_AWARDS_ONLY = "new_awards_only"


@dataclass(frozen=True)
class Location:
    """Represents a standard location for Place of Performance or Recipient filters."""

    country_code: str
    state_code: Optional[str] = None
    county_code: Optional[str] = None
    city_name: Optional[str] = None
    district_original: Optional[str] = None
    district_current: Optional[str] = None
    zip_code: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        """Serializes the location to the dictionary format required by the API."""
        data = {"country": self.country_code}
        if self.state_code:
            data["state"] = self.state_code
        if self.county_code:
            data["county"] = self.county_code
        if self.city_name:
            data["city"] = self.city_name
        if self.district_original:
            data["district_original"] = self.district_original
        if self.district_current:
            data["district_current"] = self.district_current
        if self.zip_code:
            data["zip"] = self.zip_code
        return data


# ==============================================================================
# Base Filter Abstraction
# ==============================================================================


class BaseFilter(ABC):
    """Abstract base class for all query filter types."""

    key: ClassVar[str]

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Converts the filter to its dictionary representation for the API."""
        pass


# ==============================================================================
# Individual Filter Implementations
# ==============================================================================


@dataclass(frozen=True)
class KeywordsFilter(BaseFilter):
    """Filter by a list of keywords."""

    key: ClassVar[str] = "keywords"
    values: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {self.key: self.values}


@dataclass(frozen=True)
class TimePeriodFilter(BaseFilter):
    """Filter by a date range."""

    key: ClassVar[str] = "time_period"
    start_date: datetime.date
    end_date: datetime.date
    date_type: Optional[AwardDateType] = None

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        period: dict[str, str] = {
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
        }
        if self.date_type:
            period["date_type"] = self.date_type.value
        return {self.key: [period]}


@dataclass(frozen=True)
class LocationScopeFilter(BaseFilter):
    """Filter by domestic or foreign scope for location."""

    key: Literal["place_of_performance_scope", "recipient_scope"]
    scope: LocationScope

    def to_dict(self) -> dict[str, str]:
        return {self.key: self.scope.value}


@dataclass(frozen=True)
class LocationFilter(BaseFilter):
    """Filter by one or more specific geographic locations."""

    key: Literal["place_of_performance_locations", "recipient_locations"]
    locations: list[Location]

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {self.key: [loc.to_dict() for loc in self.locations]}


@dataclass(frozen=True)
class AgencyFilter(BaseFilter):
    """Filter by an awarding or funding agency."""

    key: ClassVar[str] = "agencies"
    agency_type: AgencyType
    tier: AgencyTier
    name: str

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        agency_object = {
            "type": self.agency_type.value,
            "tier": self.tier.value,
            "name": self.name,
        }
        return {self.key: [agency_object]}


@dataclass(frozen=True)
class SimpleListFilter(BaseFilter):
    """A generic filter for API keys that accept a list of string values."""

    key: str
    values: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {self.key: self.values}


@dataclass(frozen=True)
class AwardAmount:
    """Represents a single award amount range for filtering."""

    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

    def to_dict(self) -> dict[str, float]:
        data = {}
        if self.lower_bound is not None:
            data["lower_bound"] = self.lower_bound
        if self.upper_bound is not None:
            data["upper_bound"] = self.upper_bound
        return data


@dataclass(frozen=True)
class AwardAmountFilter(BaseFilter):
    """Filter by one or more award amount ranges."""

    key: ClassVar[str] = "award_amounts"
    amounts: list[AwardAmount]

    def to_dict(self) -> dict[str, list[dict[str, float]]]:
        return {self.key: [amount.to_dict() for amount in self.amounts]}


@dataclass(frozen=True)
class TieredCodeFilter(BaseFilter):
    """Handles filters with a 'require' and 'exclude' structure like NAICS."""

    key: Literal["naics_codes", "psc_codes", "tas_codes"]
    require: list[list[str]] = field(default_factory=list)
    exclude: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, dict[str, list[list[str]]]]:
        data = {}
        if self.require:
            data["require"] = self.require
        if self.exclude:
            data["exclude"] = self.exclude
        return {self.key: data}


@dataclass(frozen=True)
class TreasuryAccountComponentsFilter(BaseFilter):
    """Filter by specific components of a Treasury Account."""

    key: ClassVar[str] = "treasury_account_components"
    components: list[dict[str, str]]

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {self.key: self.components}
