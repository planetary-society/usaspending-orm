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
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
)


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
        date_string: Date string in any supported format, or a date object

    Returns:
        date object or None if parsing fails
    """
    if not date_string:
        return None

    if isinstance(date_string, datetime):
        return date_string.date()
    if isinstance(date_string, date):
        return date_string

    # Date-only is nearly everything the API sends, and `date.fromisoformat` reads it
    # about 11x faster than working down the format list. The shape check pins the
    # fast path to that one shape, which is what keeps it from widening what parses.
    # Both ways that can go wrong are named in the tests, which fail if either does.
    if len(date_string) == 10 and date_string[4] == date_string[7] == "-":
        try:
            return date.fromisoformat(date_string)
        except ValueError:
            # Well shaped but not a real date. Fall through, so an impossible date
            # warns by the same path as every other failure.
            pass

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue

    logger.warning(f"Could not parse date string: {date_string}")
    return None
