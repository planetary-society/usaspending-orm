"""Tests for date parsing and fiscal-year helpers."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch

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
        assert to_date("2025-13-01") is None  # Invalid month
        assert to_date("2025-08-32") is None  # Invalid day
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

        # Non-leap year (should fail)
        assert to_date("2023-02-29") is None

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
