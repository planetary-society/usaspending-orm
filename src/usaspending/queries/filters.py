from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Literal, Optional, Union

from ..exceptions import ValidationError
from ..utils.validations import parse_enum_value

# ==============================================================================
# Constants
# ==============================================================================

# Earliest fiscal year supported by USASpending.gov
MIN_FISCAL_YEAR = 2008

# Earliest date supported by USASpending.gov API (start of MIN_FISCAL_YEAR)
# Fiscal years begin on October 1 of the prior calendar year
MIN_API_DATE = datetime.date(MIN_FISCAL_YEAR - 1, 10, 1)

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


@dataclass(frozen=True)
class AgencySpec:
    """Represents a standard agency specification for awarding/funding agency filters."""

    name: str
    type: str  # "awarding" or "funding"
    tier: str  # "toptier" or "subtier"
    toptier_name: Optional[str] = None  # For scoping subtiers to specific parent

    def to_dict(self) -> dict[str, str]:
        """Serializes the agency spec to the dictionary format required by the API."""
        data = {
            "name": self.name,
            "type": self.type,
            "tier": self.tier,
        }
        if self.toptier_name:
            data["toptier_name"] = self.toptier_name
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
    """Filter by one or more awarding or funding agencies."""

    key: ClassVar[str] = "agencies"
    agencies: list[AgencySpec]

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {self.key: [agency.to_dict() for agency in self.agencies]}


@dataclass(frozen=True)
class SimpleListFilter(BaseFilter):
    """A generic filter for API keys that accept a list of string values."""

    key: str
    values: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {self.key: self.values}


@dataclass(frozen=True)
class SimpleStringFilter(BaseFilter):
    """A generic filter for API keys that accept a single string value."""

    key: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {self.key: self.value}


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
class NAICSFilter(BaseFilter):
    """Filter by NAICS codes with require/exclude structure using flat arrays.

    Per API documentation, NAICS codes use flat string arrays (not nested arrays
    like TAS/PSC codes). The API will match codes that START WITH the provided
    prefixes, allowing for hierarchical filtering.
    """

    key: ClassVar[str] = "naics_codes"
    require: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, dict[str, list[str]]]:
        data: dict[str, list[str]] = {}
        if self.require:
            data["require"] = self.require
        if self.exclude:
            data["exclude"] = self.exclude
        return {self.key: data}


@dataclass(frozen=True)
class PSCFilter(BaseFilter):
    """Filter by Product and Service Codes (PSC).

    Supports two formats per API documentation:
    1. Simple list: ["1510", "1520"] - direct code matching
    2. Hierarchical require/exclude: {"require": [[...]], "exclude": [[...]]}
    """

    key: ClassVar[str] = "psc_codes"
    codes: list[str] = field(default_factory=list)  # Simple format
    require: list[list[str]] = field(default_factory=list)  # Hierarchical format
    exclude: list[list[str]] = field(default_factory=list)  # Hierarchical format

    def to_dict(self) -> dict[str, Any]:
        # If simple codes are provided, use simple list format
        if self.codes:
            return {self.key: self.codes}
        # Otherwise use hierarchical require/exclude format
        data: dict[str, list[list[str]]] = {}
        if self.require:
            data["require"] = self.require
        if self.exclude:
            data["exclude"] = self.exclude
        return {self.key: data}


@dataclass(frozen=True)
class TieredCodeFilter(BaseFilter):
    """Handles filters with hierarchical 'require' and 'exclude' structure for TAS codes."""

    key: Literal["tas_codes"]
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
    """Convert a string to a LocationScope enum value.

    Args:
        scope: Either "domestic" or "foreign" (case-insensitive).

    Returns:
        LocationScope: The corresponding enum value.

    Raises:
        ValidationError: If scope is not "domestic" or "foreign".
    """
    return parse_enum_value(scope, LocationScope, "scope", normalize=False)


def parse_agency_type(agency_type: str) -> AgencyType:
    """Convert a string to an AgencyType enum value.

    Args:
        agency_type: Either "awarding" or "funding" (case-insensitive).

    Returns:
        AgencyType: The corresponding enum value.

    Raises:
        ValidationError: If agency_type is not "awarding" or "funding".
    """
    return parse_enum_value(agency_type, AgencyType, "agency_type", normalize=False)


def parse_agency_tier(tier: str) -> AgencyTier:
    """Convert a string to an AgencyTier enum value.

    Args:
        tier: Either "toptier" or "subtier" (case-insensitive).

    Returns:
        AgencyTier: The corresponding enum value.

    Raises:
        ValidationError: If tier is not "toptier" or "subtier".
    """
    return parse_enum_value(tier, AgencyTier, "tier", normalize=False)


def parse_award_date_type(date_type: str) -> AwardDateType:
    """Convert a string to an AwardDateType enum value.

    Handles flexible input formats including underscores and variations.

    Args:
        date_type: One of "action_date", "date_signed", "last_modified_date",
            or "new_awards_only" (case-insensitive, underscores optional).

    Returns:
        AwardDateType: The corresponding enum value.

    Raises:
        ValidationError: If date_type is not a valid option.
    """
    return parse_enum_value(date_type, AwardDateType, "date_type", normalize=True)


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
    Convert a dictionary to a LocationSpec dataclass with validation.

    Per USASpending API documentation, location objects have the following rules:
    - country is required
    - county requires state to be specified
    - county and district_original are mutually exclusive
    - county and district_current are mutually exclusive
    - district_original and district_current are mutually exclusive
    - district_original/district_current require state to be specified
    - district_original/district_current require country to be "USA"

    Args:
        location: A dictionary with location fields like country_code,
            state_code, city_name, etc.

    Returns:
        LocationSpec: The corresponding dataclass instance.

    Raises:
        ValidationError: If location specification violates API rules.
    """
    # Map user-friendly keys to dataclass field names
    key_mapping = {
        "country": "country_code",
        "state": "state_code",
        "county": "county_code",
        "city": "city_name",
        "zip": "zip_code",
    }
    normalized = {key_mapping.get(k, k): v for k, v in location.items()}

    # Check for required country field
    country = normalized.get("country_code", "")
    if not country:
        raise ValidationError("Location must include 'country' or 'country_code'")

    # Determine what fields are present
    has_state = bool(normalized.get("state_code"))
    has_county = bool(normalized.get("county_code"))
    has_district_original = bool(normalized.get("district_original"))
    has_district_current = bool(normalized.get("district_current"))

    # Validation: county requires state
    if has_county and not has_state:
        raise ValidationError(
            "county requires state to be specified in location filter"
        )

    # Validation: county and district are mutually exclusive
    if has_county and (has_district_original or has_district_current):
        raise ValidationError(
            "county and district are mutually exclusive in location filter"
        )

    # Validation: district_original and district_current are mutually exclusive
    if has_district_original and has_district_current:
        raise ValidationError(
            "district_original and district_current are mutually exclusive"
        )

    # Validation: district requires state and USA country
    if has_district_original or has_district_current:
        if not has_state:
            raise ValidationError(
                "district requires state to be specified in location filter"
            )
        if country.upper() != "USA":
            raise ValidationError(
                "district is only valid for USA locations (country must be 'USA')"
            )

    return LocationSpec(**normalized)


def parse_agency_spec(agency: dict[str, str]) -> AgencySpec:
    """
    Convert a dictionary to an AgencySpec dataclass.

    Args:
        agency: A dictionary with agency fields: name, type, tier,
            and optionally toptier_name.

    Returns:
        AgencySpec: The corresponding dataclass instance.

    Raises:
        ValidationError: If required fields are missing or invalid.
    """
    from ..exceptions import ValidationError

    # Validate required fields
    if "name" not in agency:
        raise ValidationError("Agency specification must include 'name' field")
    if "type" not in agency:
        raise ValidationError("Agency specification must include 'type' field")
    if "tier" not in agency:
        raise ValidationError("Agency specification must include 'tier' field")

    # Validate type and tier values
    valid_types = {"awarding", "funding"}
    valid_tiers = {"toptier", "subtier"}

    if agency["type"] not in valid_types:
        raise ValidationError(
            f"Agency type must be 'awarding' or 'funding', got: {agency['type']}"
        )
    if agency["tier"] not in valid_tiers:
        raise ValidationError(
            f"Agency tier must be 'toptier' or 'subtier', got: {agency['tier']}"
        )

    return AgencySpec(**agency)


def parse_fiscal_year(year: Union[int, str]) -> int:
    """
    Validate and parse a fiscal year value.

    USASpending.gov data begins in fiscal year 2008, so any year before that
    is invalid.

    Args:
        year: Fiscal year as integer or string (e.g., 2024 or "2024").

    Returns:
        int: Validated fiscal year.

    Raises:
        ValidationError: If year is not a valid fiscal year (must be >= 2008).

    Example:
        >>> parse_fiscal_year(2024)
        2024
        >>> parse_fiscal_year("2024")
        2024
        >>> parse_fiscal_year(2007)  # Raises ValidationError
    """
    if isinstance(year, str):
        try:
            year = int(year)
        except ValueError:
            raise ValidationError(
                f"Invalid fiscal year: '{year}'. Must be an integer >= {MIN_FISCAL_YEAR}."
            )

    if not isinstance(year, int) or year < MIN_FISCAL_YEAR:
        raise ValidationError(
            f"Invalid fiscal year: {year}. Must be >= {MIN_FISCAL_YEAR} "
            "(earliest year supported by USASpending.gov)."
        )

    return year
