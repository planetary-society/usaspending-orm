"""Tests for numeric coercion helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from usaspending.utils.numbers import to_float, to_int


class TestToInt:
    """Tests for to_int, which backs every optional integer getter."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("2020", 2020),
            (2020, 2020),
            ("0", 0),
            (0, 0),
            ("-5", -5),
            (7.9, 7),  # int() truncates toward zero
            (Decimal("42.7"), 42),
            (True, 1),
        ],
    )
    def test_parseable_values(self, value, expected):
        """Values that int() accepts convert, including truncating floats."""
        assert to_int(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            "   ",
            "not-a-number",
            "FY2020",
            "12.5",  # int() rejects a decimal string, unlike a float
            [],
            {},
            object(),
        ],
    )
    def test_unparseable_values_return_none(self, value):
        """Absent or malformed values yield None instead of raising.

        API-supplied field values coerce leniently; only user-provided
        parameters raise, via the validators in utils/validations.py.
        """
        assert to_int(value) is None

    def test_none_short_circuits_before_int(self):
        """None returns early rather than raising TypeError inside int()."""
        assert to_int(None) is None


class TestToFloat:
    """Tests for to_float, which shares to_int's lenient contract."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("12.5", 12.5), (12.5, 12.5), ("0", 0.0), (0, 0.0), ("-3.25", -3.25), (7, 7.0)],
    )
    def test_parseable_values(self, value, expected):
        """Values that float() accepts convert, including integer strings."""
        assert to_float(value) == expected

    @pytest.mark.parametrize("value", [None, "", "not-a-number", "1.2.3", [], {}])
    def test_unparseable_values_return_none(self, value):
        """Absent or malformed values yield None instead of raising."""
        assert to_float(value) is None
