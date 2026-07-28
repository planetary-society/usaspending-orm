"""Tests for date parsing."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch

import pytest

from usaspending.utils.dates import to_date


class TestToDate:
    """Test the to_date function with various date formats."""

    def test_none_and_empty_input(self):
        """Test handling of None and empty string inputs."""
        assert to_date(None) is None
        assert to_date("") is None
        assert to_date("   ") is None

    def test_basic_date_format(self):
        """Test the original YYYY-MM-DD format."""
        result = to_date("2025-08-29")
        assert result is not None
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29

    def test_iso_datetime_format(self):
        """Test ISO datetime format without timezone - returns date only."""
        result = to_date("2025-08-29T00:00:00")
        assert result is not None
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29

    def test_iso_datetime_with_time(self):
        """Test ISO datetime format with specific time - returns date only."""
        result = to_date("2025-08-29T14:30:45")
        assert result is not None
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29

    def test_iso_datetime_with_microseconds(self):
        """Test ISO datetime format with microseconds - returns date only."""
        result = to_date("2025-08-29T14:30:45.123456")
        assert result is not None
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29

    def test_iso_datetime_with_utc_indicator(self):
        """Test ISO datetime format with Z (UTC) indicator - returns date only."""
        result = to_date("2025-08-29T14:30:45Z")
        assert result is not None
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29

    def test_iso_datetime_with_timezone_offset(self):
        """Test ISO datetime format with timezone offset - returns date only."""
        result = to_date("2025-08-29T14:30:45+00:00")
        assert result is not None
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29

    def test_invalid_date_formats(self):
        """Test that invalid date formats return None."""
        assert to_date("not-a-date") is None
        assert to_date("2025/08/29") is None  # Wrong separator
        assert to_date("08-29-2025") is None  # Wrong order
        assert to_date("abc-def-ghi") is None
        assert to_date("2025") is None  # Incomplete date

    def test_edge_cases(self):
        """Test edge cases for date parsing."""
        # Leap year date
        result = to_date("2024-02-29")
        assert result is not None
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29

        # End of year - returns date only
        result = to_date("2025-12-31T23:59:59")
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 31

    def test_real_usaspending_formats(self):
        """Test formats actually returned by USAspending API."""
        # Common format from API responses
        result = to_date("2025-08-25T00:00:00")
        assert result is not None
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 25

    def test_space_separated_datetime_format(self):
        """Test datetime format with a space separator - returns date only."""
        result = to_date("2026-03-31 10:11:00")
        assert result is not None
        assert isinstance(result, date)
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 31

    def test_space_separated_datetime_with_microseconds(self):
        """Test a space separator combined with microseconds - returns date only."""
        result = to_date("2026-03-31 10:11:00.123456")
        assert result == date(2026, 3, 31)

    @patch("usaspending.utils.dates._DATE_FORMATS", ())
    def test_a_date_only_value_parses_without_the_format_list(self):
        """The fast path, not the format list, is what reads a plain YYYY-MM-DD.

        With every strptime format removed the value still parses, which is only
        possible through ``date.fromisoformat``. Nothing else catches the fast
        path being disabled, since the format list accepts this shape too.

        This and the test below are the only two places in the suite that patch a
        private name, so the reason is worth stating rather than copying: the two
        paths return equal dates for every value either accepts, so which one ran
        is observable through no assertion on the result. Spying on the parser is
        not available either, since ``date`` is an immutable C type and patching
        the module's ``date`` name would break the isinstance checks above it.
        """
        assert to_date("2025-08-29") == date(2025, 8, 29)

    @patch("usaspending.utils.dates._DATE_FORMATS", ())
    def test_a_datetime_value_does_not_reach_the_fast_path(self):
        """A value carrying a time is left to the format list.

        Catches the fast path being switched to ``datetime.fromisoformat``, which
        reads more shapes and so looks like a simplification, with the width
        check loosened to let those shapes through. Either change alone is
        harmless; together they take a time where none should be accepted.
        """
        assert to_date("2025-08-29T14:30:45") is None
        assert to_date("2025-08-29 14:30:45") is None

    def test_compact_timezone_offset(self):
        """An offset written without a colon is accepted.

        Only ``%z`` matches this shape, so it is the one supported format that
        neither ``date.fromisoformat`` nor ``datetime.fromisoformat`` can parse on
        every supported Python.
        """
        result = to_date("2025-08-29T14:30:45+0500")
        assert result == date(2025, 8, 29)

    def test_unpadded_month_and_day(self):
        """A date written without zero padding is accepted.

        ``%Y-%m-%d`` takes ``2025-8-9`` where ``date.fromisoformat`` requires the
        padding, so this is why the fast path cannot replace that format outright.
        """
        result = to_date("2025-8-9")
        assert result == date(2025, 8, 9)

    @pytest.mark.parametrize(
        "value",
        [
            "2025-08-29GARBAGE",  # A valid date does not license trailing junk
            "2025-08-29 99:99:99",  # An impossible time rejects the whole value
            "2025-08-29 ",  # Trailing space
            "2025-08-29T14:30",  # Time with no seconds
            "2025-08-29Z",  # Zone designator with no time
        ],
    )
    def test_a_leading_date_alone_is_not_enough(self, value):
        """Reject a string whose first ten characters are a date but whose rest is not.

        The whole string has to be a date the API could have sent. Reading only the
        leading ten characters would take every one of these.
        """
        assert to_date(value) is None

    @pytest.mark.parametrize("value", ["20250829", "2025-W35-5"])
    def test_iso_forms_the_api_does_not_send_are_rejected(self, value):
        """Reject the basic and week-date ISO forms on every supported Python.

        Python 3.11 widened ``date.fromisoformat`` to accept both, so these fail
        on 3.11 and later if the fast path stops excluding them.
        """
        assert to_date(value) is None

    def test_earliest_representable_date(self):
        """The minimum date parses, as a boundary on the year field."""
        assert to_date("0001-01-01") == date(1, 1, 1)

    @pytest.mark.parametrize(
        "value",
        [
            "2025-13-01",  # Invalid month
            "2025-08-32",  # Invalid day
            "2023-02-29",  # Not a leap year
        ],
    )
    @patch("usaspending.utils.dates.logger")
    def test_an_impossible_date_still_warns(self, mock_logger, value):
        """A well-shaped but impossible date warns like any other failure.

        These take the date-only path, so they would be the ones to lose the
        warning if that path returned early instead of falling through.
        """
        assert to_date(value) is None
        mock_logger.warning.assert_called_once()

    @patch("usaspending.utils.dates.logger")
    def test_logging_on_invalid_format(self, mock_logger):
        """Test that invalid formats trigger a warning log."""
        result = to_date("invalid-date-format")
        assert result is None
        mock_logger.warning.assert_called_once()
        assert "Could not parse date string: invalid-date-format" in str(
            mock_logger.warning.call_args
        )

    def test_backwards_compatibility(self):
        """Ensure the function maintains backwards compatibility."""
        # Test that the original format still works
        old_format_date = "2025-01-15"
        result = to_date(old_format_date)
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

        # Test that we get the same results as before for standard dates

        date1 = to_date("2025-06-15")
        date2 = date(2025, 6, 15)
        assert date1 == date2

    def test_date_object_passthrough(self):
        """Test that date objects are returned unchanged (idempotent behavior)."""
        input_date = date(2024, 8, 12)
        result = to_date(input_date)

        assert result is input_date  # Same object
        assert result == date(2024, 8, 12)

    def test_date_object_prevents_double_conversion_error(self):
        """Test that passing a date object doesn't raise TypeError.

        This was a bug where Award.start_date called to_date() on a value
        that was already converted to a date by PeriodOfPerformance.
        """
        # Simulate double conversion scenario
        first_conversion = to_date("2024-08-12")
        assert first_conversion == date(2024, 8, 12)

        # Second conversion should not raise TypeError
        second_conversion = to_date(first_conversion)
        assert second_conversion == date(2024, 8, 12)

    def test_datetime_object_returns_date_portion(self):
        """datetime input is narrowed to its date() portion.

        Regression: datetime is a subclass of date, so the prior
        ``isinstance(x, date)`` check let datetimes through unchanged,
        leaking a datetime out of a function typed ``date | None``.
        """
        dt = datetime(2025, 8, 29, 14, 30, 45)
        result = to_date(dt)

        assert type(result) is date
        assert result == date(2025, 8, 29)
