"""Date parsing for the several shapes USASpending reports dates in.

Like the numeric coercers, :func:`to_date` answers a missing or unparseable value
with None rather than raising, so callers that require a date supply their own
fallback. Unlike them it also logs a warning, since a date the API sent that will
not parse is a shape surprise rather than the routine omission a missing number is.
"""

from __future__ import annotations

from datetime import date, datetime

from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)

#: Every shape the API is known to report a date in, tried in order of likelihood.
#: :func:`to_date` documents what each one is, and this tuple decides what parses.
#:
#: Six, which is one more than CPython's process-global strptime regex cache
#: holds: walking all of them evicts every entry, including those of unrelated
#: callers, who then recompile. `_starts_like_a_date` keeps values that cannot
#: match from reaching the walk, which is most of them, but a date-shaped value
#: that matches nothing still pays it. Getting under the cache would mean
#: normalizing the `T` separator to a space so the four datetime formats become
#: two, which would also start accepting `2025-08-29 14:30:45Z`. Not done: the
#: accept set is worth more than the cache. `%z` reads a `Z` as well as a
#: numeric offset, which is why no separate format spells it.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S%z",
)


def _starts_like_a_date(value: object) -> bool:
    """Report whether `value` could be one of the shapes in `_DATE_FORMATS`.

    Every format begins `%Y-%m-`, and `%Y` matches exactly four digits, so
    anything the list can read starts with four digits and a dash, and runs to at
    least the 8 of an unpadded `YYYY-M-D`.

    Args:
        value: Any value, including ones of the wrong type entirely.

    Returns:
        bool: True if the value is a string whose start could begin a date.
    """
    return isinstance(value, str) and len(value) >= 8 and value[:4].isdigit() and value[4] == "-"


def to_date(date_string: str | date | None) -> date | None:
    """Convert date string to date object.

    Supports multiple date formats:
    - YYYY-MM-DD (date only; the month and day need not be zero padded)
    - YYYY-MM-DD HH:MM:SS (space-separated datetime)
    - YYYY-MM-DD HH:MM:SS.ffffff (space-separated datetime with microseconds)
    - YYYY-MM-DDTHH:MM:SS (ISO datetime)
    - YYYY-MM-DDTHH:MM:SS.ffffff (ISO datetime with microseconds)
    - YYYY-MM-DDTHH:MM:SSZ (ISO datetime with UTC indicator)
    - YYYY-MM-DDTHH:MM:SS+/-HHMM or +/-HH:MM (ISO datetime with timezone offset)

    Note: For formats with time components, only the date portion is returned.
    If input is already a date object, returns it unchanged.

    Args:
        date_string: Date string in any supported format, or a date object. A
            value of any other type is unusable and answers None, since this
            reads API payloads rather than caller input.

    Returns:
        date object or None if parsing fails
    """
    if not date_string:
        return None

    # datetime subclasses date, so narrow before the date check, not after. The
    # same pair guards `parse_date_string` in utils/validations.py.
    if isinstance(date_string, datetime):
        return date_string.date()
    if isinstance(date_string, date):
        return date_string

    # Date-only is nearly everything the API sends, and `date.fromisoformat` reads it
    # about 11x faster than working down the format list. The width pins the fast
    # path to that one shape, which is what keeps it from widening what parses.
    # Both ways that can go wrong are named in the tests, which fail if either does.
    try:
        if len(date_string) == 10 and date_string[4] == date_string[7] == "-":
            return date.fromisoformat(date_string)
    except (TypeError, ValueError):
        # Well shaped but not a real date, or not a string at all. Both fall
        # through, so every unusable value answers by the one path below.
        pass

    # Only a value that could be one of the formats is walked against them. This
    # sits after the fast path rather than before it so the shape it tests, which
    # is nearly everything the API sends, is answered without paying for it.
    if _starts_like_a_date(date_string):
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(date_string, fmt).date()
            except ValueError:
                continue

    logger.warning(f"Could not parse date string: {date_string}")
    return None
