"""Tests for formatter utility functions."""

import pytest
from datetime import datetime
from unittest.mock import patch, mock_open
import yaml

from usaspending.utils.formatter import (
    contracts_titlecase,
    TextFormatter,
    to_date,
)



class TestContractsTitlecase:
    """Test the contracts_titlecase function."""

    @pytest.fixture(autouse=True)
    def setup_yaml(self):
        """Mock the YAML file for consistent tests."""
        import usaspending.utils.formatter

        usaspending.utils.formatter._special_cases_cache = None
        TextFormatter._special_cases_cache = None

        mock_special_cases = [
            "NASA",
            "ESA",
            "USA",
            "SBIR",
            "LLC",
            "Inc.",
            "Ltd.",
            "NE",
            "SW",
            "St.",
            "Ave.",
            "OSIRIS-REx",
            "SCaN",
            "EPSCoR",
        ]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            yield

        usaspending.utils.formatter._special_cases_cache = None
        TextFormatter._special_cases_cache = None

    def test_none_input(self):
        """Test handling of None input."""
        assert contracts_titlecase(None) is None

    def test_basic_titlecase(self):
        """Test basic title casing."""
        assert contracts_titlecase("hello world") == "Hello World"
        assert contracts_titlecase("HELLO WORLD") == "Hello World"

    def test_acronyms_preserved(self):
        """Test that acronyms are preserved."""
        assert contracts_titlecase("nasa research") == "NASA Research"
        assert contracts_titlecase("working with nasa") == "Working With NASA"
        assert contracts_titlecase("sbir program") == "SBIR Program"

    def test_business_suffixes(self):
        """Test business suffixes."""
        assert contracts_titlecase("acme inc.") == "Acme Inc."
        assert contracts_titlecase("technology llc") == "Technology LLC"
        assert contracts_titlecase("services ltd.") == "Services Ltd."

    def test_small_words(self):
        """Test that small words are lowercase in middle."""
        assert contracts_titlecase("bread and butter") == "Bread and Butter"
        assert contracts_titlecase("the quick fox") == "The Quick Fox"
        assert contracts_titlecase("of the people") == "Of the People"

    def test_directional_abbreviations(self):
        """Test directional abbreviations."""
        assert contracts_titlecase("123 main st. ne") == "123 Main St. NE"
        assert contracts_titlecase("456 oak ave. sw") == "456 Oak Ave. SW"

    def test_directional_with_punctuation(self):
        """Test directional abbreviations with punctuation."""

        assert (
            contracts_titlecase("123 main st. ne, suite 100")
            == "123 Main St. NE, Suite 100"
        )

    def test_special_casing(self):
        """Test special casing rules."""
        assert contracts_titlecase("osiris-rex mission") == "OSIRIS-REx Mission"
        assert contracts_titlecase("scan network") == "SCaN Network"
        assert contracts_titlecase("epscor funding") == "EPSCoR Funding"

    def test_complex_examples(self):
        """Test complex real-world examples."""
        assert (
            contracts_titlecase("nasa sbir program for small business llc")
            == "NASA SBIR Program for Small Business LLC"
        )

        assert (
            contracts_titlecase("123 main st. ne, suite 100")
            == "123 Main St. NE, Suite 100"
        )

        assert (
            contracts_titlecase("the university of maryland and nasa")
            == "The University of Maryland and NASA"
        )


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
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_iso_datetime_format(self):
        """Test ISO datetime format without timezone."""
        result = to_date("2025-08-29T00:00:00")
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_iso_datetime_with_time(self):
        """Test ISO datetime format with specific time."""
        result = to_date("2025-08-29T14:30:45")
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

    def test_iso_datetime_with_microseconds(self):
        """Test ISO datetime format with microseconds."""
        result = to_date("2025-08-29T14:30:45.123456")
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45
        assert result.microsecond == 123456

    def test_iso_datetime_with_utc_indicator(self):
        """Test ISO datetime format with Z (UTC) indicator."""
        result = to_date("2025-08-29T14:30:45Z")
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

    def test_iso_datetime_with_timezone_offset(self):
        """Test ISO datetime format with timezone offset."""
        result = to_date("2025-08-29T14:30:45+00:00")
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 29
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

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

        # End of year
        result = to_date("2025-12-31T23:59:59")
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 31
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_real_usaspending_formats(self):
        """Test formats actually returned by USAspending API."""
        # Common format from API responses
        result = to_date("2025-08-25T00:00:00")
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 25

    @patch("usaspending.utils.formatter.logger")
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
        date2 = datetime(2025, 6, 15)
        assert date1 == date2


