"""Generic validation utilities for USASpending API client.

This module provides reusable validation functions that are used across
query builders and filters to reduce code duplication.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, TypeVar, Union

from ..exceptions import ValidationError

E = TypeVar("E", bound=Enum)


def validate_non_empty_string(
    value: Any,
    field_name: str,
    strip: bool = True,
) -> str:
    """Validate that a value is a non-empty string.

    Args:
        value: The value to validate.
        field_name: Name of the field for error messages.
        strip: Whether to strip whitespace (default True).

    Returns:
        The validated string (stripped if strip=True).

    Raises:
        ValidationError: If value is empty or not a string.

    Example:
        >>> validate_non_empty_string("hello", "name")
        'hello'
        >>> validate_non_empty_string("  ", "name")  # Raises ValidationError
    """
    if not value or not isinstance(value, str):
        raise ValidationError(f"{field_name} cannot be empty")
    result = value.strip() if strip else value
    if not result:
        raise ValidationError(f"{field_name} cannot be empty")
    return result


def parse_date_string(
    value: Union[str, date],
    field_name: str = "date",
    format_str: str = "%Y-%m-%d",
) -> date:
    """Parse a date string or pass through a date object.

    Args:
        value: Date string or date object.
        field_name: Name of the field for error messages.
        format_str: Expected date format (default "YYYY-MM-DD").

    Returns:
        Parsed date object.

    Raises:
        ValidationError: If string format is invalid.

    Example:
        >>> parse_date_string("2024-01-15", "start_date")
        datetime.date(2024, 1, 15)
        >>> parse_date_string(datetime.date(2024, 1, 15), "start_date")
        datetime.date(2024, 1, 15)
    """
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, format_str).date()
    except ValueError:
        raise ValidationError(
            f"Invalid {field_name} format: '{value}'. Expected '{format_str}'."
        )


def parse_enum_value(
    value: str,
    enum_class: type[E],
    field_name: str,
    normalize: bool = True,
) -> E:
    """Parse a string to an enum value with case-insensitive matching.

    Args:
        value: String value to parse.
        enum_class: The enum class to match against.
        field_name: Name of the field for error messages.
        normalize: Whether to normalize by removing underscores (default True).

    Returns:
        Matching enum member.

    Raises:
        ValidationError: If no matching enum value found.

    Example:
        >>> from usaspending.queries.filters import LocationScope
        >>> parse_enum_value("domestic", LocationScope, "scope")
        <LocationScope.DOMESTIC: 'domestic'>
        >>> parse_enum_value("DOMESTIC", LocationScope, "scope")
        <LocationScope.DOMESTIC: 'domestic'>
    """

    def normalize_str(s: str) -> str:
        result = s.lower()
        return result.replace("_", "") if normalize else result

    value_normalized = normalize_str(value)
    for member in enum_class:
        if normalize_str(member.value) == value_normalized:
            return member

    valid_options = ", ".join(f"'{m.value}'" for m in enum_class)
    raise ValidationError(
        f"Invalid {field_name}: '{value}'. Valid options: {valid_options}"
    )
