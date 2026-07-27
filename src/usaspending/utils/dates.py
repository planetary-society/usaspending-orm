"""Date parsing for the several shapes USASpending reports dates in."""

from __future__ import annotations

from datetime import date, datetime

from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)


def to_date(date_string: str | date | None) -> date | None:
    """Convert date string to date object.

    Supports multiple date formats:
    - YYYY-MM-DD (date only)
    - YYYY-MM-DD HH:MM:SS (space-separated datetime)
    - YYYY-MM-DD HH:MM:SS.ffffff (space-separated datetime with microseconds)
    - YYYY-MM-DDTHH:MM:SS (ISO datetime)
    - YYYY-MM-DDTHH:MM:SS.ffffff (ISO datetime with microseconds)
    - YYYY-MM-DDTHH:MM:SSZ (ISO datetime with UTC indicator)
    - YYYY-MM-DDTHH:MM:SS+/-HH:MM (ISO datetime with timezone offset)

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

    # Define formats to try, in order of likelihood
    formats = [
        "%Y-%m-%d",  # Date only (original format)
        "%Y-%m-%d %H:%M:%S",  # Datetime with space separator
        "%Y-%m-%d %H:%M:%S.%f",  # Datetime with space separator and microseconds
        "%Y-%m-%dT%H:%M:%S",  # ISO datetime without timezone
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO datetime with microseconds
        "%Y-%m-%dT%H:%M:%SZ",  # ISO datetime with UTC indicator
        "%Y-%m-%dT%H:%M:%S%z",  # ISO datetime with timezone offset
    ]

    for fmt in formats:
        try:
            parsed_datetime = datetime.strptime(date_string, fmt)
            # Return only the date portion
            return parsed_datetime.date()
        except ValueError:
            continue

    # If no format matched, log warning and return None
    logger.warning(f"Could not parse date string: {date_string}")
    return None
