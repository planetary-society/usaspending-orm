# tests/utils/test_validations.py
"""Tests for the generic validation utilities."""

from __future__ import annotations

import datetime
from enum import Enum

import pytest

from usaspending.exceptions import ValidationError
from usaspending.utils.validations import (
    parse_date_string,
    parse_enum_value,
    validate_non_empty_string,
)


# ==============================================================================
# Test Enums for parse_enum_value tests
# ==============================================================================


class SampleScope(Enum):
    """Sample enum for testing."""

    DOMESTIC = "domestic"
    FOREIGN = "foreign"


class SampleDateType(Enum):
    """Sample enum with underscores for testing normalization."""

    ACTION_DATE = "action_date"
    DATE_SIGNED = "date_signed"
    LAST_MODIFIED = "last_modified_date"


# ==============================================================================
# validate_non_empty_string Tests
# ==============================================================================


class TestValidateNonEmptyString:
    """Tests for validate_non_empty_string validator."""

    def test_valid_string(self):
        """Test that a valid string is returned."""
        result = validate_non_empty_string("hello", "field_name")
        assert result == "hello"

    def test_strips_whitespace_by_default(self):
        """Test that whitespace is stripped by default."""
        result = validate_non_empty_string("  hello  ", "field_name")
        assert result == "hello"

    def test_preserves_whitespace_when_strip_false(self):
        """Test that whitespace is preserved when strip=False."""
        result = validate_non_empty_string("  hello  ", "field_name", strip=False)
        assert result == "  hello  "

    def test_empty_string_raises_error(self):
        """Test that empty string raises ValidationError."""
        with pytest.raises(ValidationError, match="test_field cannot be empty"):
            validate_non_empty_string("", "test_field")

    def test_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises ValidationError."""
        with pytest.raises(ValidationError, match="test_field cannot be empty"):
            validate_non_empty_string("   ", "test_field")

    def test_none_raises_error(self):
        """Test that None raises ValidationError."""
        with pytest.raises(ValidationError, match="test_field cannot be empty"):
            validate_non_empty_string(None, "test_field")

    def test_non_string_raises_error(self):
        """Test that non-string types raise ValidationError."""
        with pytest.raises(ValidationError, match="test_field cannot be empty"):
            validate_non_empty_string(123, "test_field")

        with pytest.raises(ValidationError, match="test_field cannot be empty"):
            validate_non_empty_string(["list"], "test_field")


# ==============================================================================
# parse_date_string Tests
# ==============================================================================


class TestParseDateString:
    """Tests for parse_date_string validator."""

    def test_parses_valid_date_string(self):
        """Test that a valid date string is parsed."""
        result = parse_date_string("2024-01-15", "start_date")
        assert result == datetime.date(2024, 1, 15)

    def test_passes_through_date_object(self):
        """Test that a date object is returned unchanged."""
        input_date = datetime.date(2024, 3, 20)
        result = parse_date_string(input_date, "end_date")
        assert result is input_date

    def test_invalid_format_raises_error(self):
        """Test that invalid date format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid start_date format"):
            parse_date_string("01-15-2024", "start_date")

    def test_invalid_date_raises_error(self):
        """Test that invalid date values raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            parse_date_string("2024-13-45", "date")

    def test_non_date_string_raises_error(self):
        """Test that non-date strings raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid my_date format"):
            parse_date_string("not-a-date", "my_date")

    def test_default_field_name(self):
        """Test that default field_name is 'date'."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            parse_date_string("invalid", "date")

    def test_default_format(self):
        """Test that default format is YYYY-MM-DD."""
        result = parse_date_string("2024-12-25", "xmas")
        assert result == datetime.date(2024, 12, 25)


# ==============================================================================
# parse_enum_value Tests
# ==============================================================================


class TestParseEnumValue:
    """Tests for parse_enum_value validator."""

    def test_exact_match(self):
        """Test that exact string match works."""
        result = parse_enum_value("domestic", SampleScope, "scope")
        assert result == SampleScope.DOMESTIC

    def test_case_insensitive(self):
        """Test that matching is case-insensitive."""
        result = parse_enum_value("DOMESTIC", SampleScope, "scope")
        assert result == SampleScope.DOMESTIC

        result = parse_enum_value("Domestic", SampleScope, "scope")
        assert result == SampleScope.DOMESTIC

    def test_normalize_removes_underscores(self):
        """Test that normalize=True removes underscores."""
        result = parse_enum_value("action_date", SampleDateType, "date_type")
        assert result == SampleDateType.ACTION_DATE

        # Also works without underscores
        result = parse_enum_value("actiondate", SampleDateType, "date_type")
        assert result == SampleDateType.ACTION_DATE

    def test_normalize_false_requires_exact_format(self):
        """Test that normalize=False requires exact format match."""
        # With normalize=False, "domestic" still matches because it's exact
        result = parse_enum_value("domestic", SampleScope, "scope", normalize=False)
        assert result == SampleScope.DOMESTIC

    def test_invalid_value_raises_error(self):
        """Test that invalid value raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid scope: 'invalid'"):
            parse_enum_value("invalid", SampleScope, "scope")

    def test_error_includes_valid_options(self):
        """Test that error message includes valid options."""
        with pytest.raises(ValidationError) as exc_info:
            parse_enum_value("bad", SampleScope, "scope")

        error_msg = str(exc_info.value)
        assert "'domestic'" in error_msg
        assert "'foreign'" in error_msg

    def test_all_enum_members_matchable(self):
        """Test that all enum members can be matched."""
        assert (
            parse_enum_value("domestic", SampleScope, "scope") == SampleScope.DOMESTIC
        )
        assert parse_enum_value("foreign", SampleScope, "scope") == SampleScope.FOREIGN


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestValidatorsIntegration:
    """Integration tests to verify validators work with actual filter enums."""

    def test_with_location_scope_enum(self):
        """Test parse_enum_value with LocationScope enum."""
        from usaspending.queries.filters import LocationScope

        result = parse_enum_value("domestic", LocationScope, "scope", normalize=False)
        assert result == LocationScope.DOMESTIC

        result = parse_enum_value("foreign", LocationScope, "scope", normalize=False)
        assert result == LocationScope.FOREIGN

    def test_with_agency_type_enum(self):
        """Test parse_enum_value with AgencyType enum."""
        from usaspending.queries.filters import AgencyType

        result = parse_enum_value(
            "awarding", AgencyType, "agency_type", normalize=False
        )
        assert result == AgencyType.AWARDING

        result = parse_enum_value("FUNDING", AgencyType, "agency_type", normalize=False)
        assert result == AgencyType.FUNDING

    def test_with_award_date_type_enum(self):
        """Test parse_enum_value with AwardDateType enum."""
        from usaspending.queries.filters import AwardDateType

        # Test with normalize=True (removes underscores)
        result = parse_enum_value(
            "action_date", AwardDateType, "date_type", normalize=True
        )
        assert result == AwardDateType.ACTION_DATE

        result = parse_enum_value(
            "actiondate", AwardDateType, "date_type", normalize=True
        )
        assert result == AwardDateType.ACTION_DATE

        result = parse_enum_value(
            "NEW_AWARDS_ONLY", AwardDateType, "date_type", normalize=True
        )
        assert result == AwardDateType.NEW_AWARDS_ONLY
