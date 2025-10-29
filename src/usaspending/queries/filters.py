from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Literal, Optional, Union

from ..exceptions import ValidationError

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
class LocationSpec:
    """Represents a standard location specification for Place of Performance or Recipient filters."""

    country_code: str
    state_code: Optional[str] = None
    county_code: Optional[str] = None
    city_name: Optional[str] = None
    district_original: Optional[str] = (
        None  # Current congressional district (e.g. "IA-03")
    )
    district_current: Optional[str] = (
        None  # Congressional district when awarded (e.g. "WA-01")
    )
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
    locations: list[LocationSpec]

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


# ==============================================================================
# Conversion Utility Functions
# ==============================================================================


def parse_location_scope(scope: str) -> LocationScope:
    """
    Convert a string to a LocationScope enum value.

    Args:
        scope: Either "domestic" or "foreign" (case-insensitive).

    Returns:
        LocationScope: The corresponding enum value.

    Raises:
        ValidationError: If scope is not "domestic" or "foreign".
    """
    scope_lower = scope.lower()
    if scope_lower == "domestic":
        return LocationScope.DOMESTIC
    elif scope_lower == "foreign":
        return LocationScope.FOREIGN
    else:
        raise ValidationError("scope must be 'domestic' or 'foreign'")


def parse_agency_type(agency_type: str) -> AgencyType:
    """
    Convert a string to an AgencyType enum value.

    Args:
        agency_type: Either "awarding" or "funding" (case-insensitive).

    Returns:
        AgencyType: The corresponding enum value.

    Raises:
        ValidationError: If agency_type is not "awarding" or "funding".
    """
    agency_type_lower = agency_type.lower()
    if agency_type_lower == "awarding":
        return AgencyType.AWARDING
    elif agency_type_lower == "funding":
        return AgencyType.FUNDING
    else:
        raise ValidationError("agency_type must be 'awarding' or 'funding'")


def parse_agency_tier(tier: str) -> AgencyTier:
    """
    Convert a string to an AgencyTier enum value.

    Args:
        tier: Either "toptier" or "subtier" (case-insensitive).

    Returns:
        AgencyTier: The corresponding enum value.

    Raises:
        ValidationError: If tier is not "toptier" or "subtier".
    """
    tier_lower = tier.lower()
    if tier_lower == "toptier":
        return AgencyTier.TOPTIER
    elif tier_lower == "subtier":
        return AgencyTier.SUBTIER
    else:
        raise ValidationError("tier must be 'toptier' or 'subtier'")


def parse_award_date_type(date_type: str) -> AwardDateType:
    """
    Convert a string to an AwardDateType enum value.

    Handles flexible input formats including underscores and variations.

    Args:
        date_type: One of "action_date", "date_signed", "last_modified_date",
            or "new_awards_only" (case-insensitive, underscores optional).

    Returns:
        AwardDateType: The corresponding enum value.

    Raises:
        ValidationError: If date_type is not a valid option.
    """
    date_type_lower = date_type.lower().replace("_", "")
    if date_type_lower == "actiondate":
        return AwardDateType.ACTION_DATE
    elif date_type_lower == "datesigned":
        return AwardDateType.DATE_SIGNED
    elif date_type_lower in ["lastmodified", "lastmodifieddate"]:
        return AwardDateType.LAST_MODIFIED
    elif date_type_lower == "newardsonly":
        return AwardDateType.NEW_AWARDS_ONLY
    else:
        raise ValidationError(
            f"Invalid date_type: '{date_type}'. Must be one of: "
            "'action_date', 'date_signed', 'last_modified_date', 'new_awards_only'"
        )


def parse_award_amount(
    amount: Union[dict[str, float], tuple[Optional[float], Optional[float]]],
) -> AwardAmount:
    """
    Convert a dictionary or tuple to an AwardAmount dataclass.

    Args:
        amount: Either:
            - A dictionary with 'lower_bound' and/or 'upper_bound' keys
            - A tuple of (lower_bound, upper_bound) where None means unbounded

    Returns:
        AwardAmount: The corresponding dataclass instance.

    Raises:
        ValidationError: If amount is not a valid dict or tuple format.
    """
    if isinstance(amount, dict):
        return AwardAmount(**amount)
    elif isinstance(amount, tuple):
        if len(amount) != 2:
            raise ValidationError(
                "Award amount tuple must have exactly 2 elements (lower_bound, upper_bound)"
            )
        lower, upper = amount
        return AwardAmount(lower_bound=lower, upper_bound=upper)
    else:
        raise ValidationError(
            "Award amounts must be specified as a dictionary or tuple"
        )


def parse_location_spec(location: dict[str, str]) -> LocationSpec:
    """
    Convert a dictionary to a LocationSpec dataclass.

    Args:
        location: A dictionary with location fields like country_code,
            state_code, city_name, etc.

    Returns:
        LocationSpec: The corresponding dataclass instance.
    """
    return LocationSpec(**location)
