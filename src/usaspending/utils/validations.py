"""Validation utilities for the USASpending API client.

Reusable checks shared across query builders, models and filters. Most are
generic and parameterized by field name; a few encode a specific USASpending
convention, such as the shape of an agency toptier code. Domain validators live
here rather than in ``queries/filters.py`` so that ``models/`` and ``resources/``
can import them without pulling in the query layer.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import Any, TypeVar

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
        >>> validate_non_empty_string("  ", "name")
        Traceback (most recent call last):
            ...
        usaspending.exceptions.ValidationError: name cannot be empty
    """
    if not value or not isinstance(value, str):
        raise ValidationError(f"{field_name} cannot be empty")
    result = value.strip() if strip else value
    if not result:
        raise ValidationError(f"{field_name} cannot be empty")
    return result


def parse_date_string(
    value: str | date,
    field_name: str = "date",
    format_str: str = "%Y-%m-%d",
) -> date:
    """Parse a date string or pass through a date object.

    Args:
        value: Date string, date or datetime. A datetime is narrowed to its
            date portion.
        field_name: Name of the field for error messages.
        format_str: Expected date format (default "YYYY-MM-DD").

    Returns:
        Parsed date object.

    Raises:
        ValidationError: If string format is invalid.

    Example:
        >>> parse_date_string("2024-01-15", "start_date")
        datetime.date(2024, 1, 15)
        >>> parse_date_string(date(2024, 1, 15), "start_date")
        datetime.date(2024, 1, 15)
        >>> parse_date_string(datetime(2024, 1, 15, 9, 30), "start_date")
        datetime.date(2024, 1, 15)
        >>> parse_date_string("15/01/2024", "start_date")
        Traceback (most recent call last):
            ...
        usaspending.exceptions.ValidationError: Invalid start_date format: '15/01/2024'. Expected '%Y-%m-%d'.
    """
    # datetime subclasses date, so narrow before the date check, not after. The
    # same pair guards `to_date` in utils/dates.py, which had this bug first.
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, format_str).date()
    except ValueError as e:
        raise ValidationError(
            f"Invalid {field_name} format: '{value}'. Expected '{format_str}'."
        ) from e


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
    raise ValidationError(f"Invalid {field_name}: '{value}'. Valid options: {valid_options}")


def validate_toptier_code(toptier_code: str | int | None) -> str:
    """Validate and normalize an agency toptier code.

    Args:
        toptier_code: The code to validate. Coerced to a stripped string.

    Returns:
        str: The normalized code.

    Raises:
        ValidationError: If the code is missing, or is not a 3-4 digit numeric
            string.

    Example:
        >>> validate_toptier_code("080")
        '080'
        >>> validate_toptier_code(" 012 ")
        '012'
    """
    if not toptier_code:
        raise ValidationError("toptier_code is required")

    normalized = str(toptier_code).strip()

    if not normalized.isdigit() or len(normalized) not in (3, 4):
        raise ValidationError(
            f"Invalid toptier_code: {normalized}. Must be a 3-4 digit numeric string"
        )

    return normalized


#: Matches the list-annotated recipient-ID form, ``<hash>-['C', 'R']``.
_RECIPIENT_LEVEL_LIST_RE = re.compile(
    r"""
    ^(?P<base>.+?)              # the recipient hash, non-greedy
    -\[\s*(?P<body>[^\]]+)\]    #  -[ 'C', 'R' ]
    $
    """,
    re.VERBOSE,
)


def normalize_recipient_id(recipient_id: Any) -> Any:
    """Normalize a recipient ID to a single ``<hash>-<level>`` form.

    USASpending sometimes reports a recipient ID carrying every level the
    recipient exists at, as ``"<hash>-['C', 'R']"``. The ``/recipient/{id}/``
    endpoint takes one level and returns a different record for each, so one
    has to be chosen.

    ``R`` is avoided whenever another level is available, and otherwise the
    first level listed wins. That is measured rather than assumed: against the
    live endpoint, for all six multi-level IDs in the captured fixtures, the
    ``R`` record reports *less* spending than its sibling and reports flat zero
    in four of the six, with ``parent_id``, ``parent_name`` and ``parents`` all
    null. ``26e104c4-1307-f677-c014-ac7fe7ab9e6d`` reports $24.6M over 109
    transactions at ``-C`` and $0 over 0 transactions at ``-R``. Since a lazy
    load merges whatever that record holds, choosing ``R`` would report a
    recipient as having no spending and no parent.

    The rule deliberately does not encode an order among the non-``R`` levels.
    Every observed level list is ``['C']`` or ``['C', 'R']``, which is also
    consistent with the API simply emitting them alphabetically, so there is no
    evidence about ``P`` versus ``C``. Skipping ``R`` is what the data supports,
    and doing it by membership rather than by position means a list arriving as
    ``['R', 'C']`` cannot reintroduce the zeroing.

    Args:
        recipient_id: The raw recipient ID. Non-string input is returned
            unchanged, defensively, since this runs during model construction.

    Returns:
        The normalized ID, or the input unchanged if it is not a string or
        carries no level list.

    Example:
        >>> normalize_recipient_id("abc123-['C', 'R']")
        'abc123-C'
        >>> normalize_recipient_id("abc123-['R', 'C']")
        'abc123-C'
        >>> normalize_recipient_id("abc123-['R']")
        'abc123-R'
        >>> normalize_recipient_id("abc123-C/")
        'abc123-C'
    """
    if not isinstance(recipient_id, str):
        return recipient_id

    normalized = recipient_id.strip().rstrip("/")

    match = _RECIPIENT_LEVEL_LIST_RE.match(normalized)
    if not match:
        return normalized

    levels = [
        token.strip().strip("'\"").upper()
        for token in match.group("body").split(",")
        if token.strip().strip("'\"")
    ]

    # Guard the chosen level rather than the list: a list of empty tokens would
    # otherwise produce a bare trailing dash.
    level = next((lvl for lvl in levels if lvl != "R"), levels[0] if levels else "")
    if not level:
        return match.group("base")

    return f"{match.group('base')}-{level}"


def validate_sort_field(
    field: str,
    valid_fields: set[str],
    context: str = "query",
) -> None:
    """Validate that a sort field is allowed for the query type.

    Args:
        field: The sort field to validate.
        valid_fields: Set of valid sort field names.
        context: Description of the query context for error messages.

    Raises:
        ValidationError: If field is not in valid_fields.

    Example:
        >>> validate_sort_field("Award Amount", {"Award Amount", "Award ID"}, "awards search")
        >>> validate_sort_field("Nope", {"Award ID"}, "awards search")
        Traceback (most recent call last):
            ...
        usaspending.exceptions.ValidationError: Invalid sort field 'Nope' for awards search. Valid fields: Award ID
    """
    if field not in valid_fields:
        sorted_fields = sorted(valid_fields)
        raise ValidationError(
            f"Invalid sort field '{field}' for {context}. Valid fields: {', '.join(sorted_fields)}"
        )
