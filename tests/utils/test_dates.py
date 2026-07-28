"""Tests for date parsing."""

from __future__ import annotations

import _strptime
from datetime import date, datetime
from unittest.mock import patch

import pytest

from usaspending.utils.dates import current_fiscal_year, to_date


class TestToDate:
    """Test the to_date function with various date formats."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # Date only, which is nearly everything the API sends.
            ("2025-08-29", date(2025, 8, 29)),
            ("2025-8-9", date(2025, 8, 9)),  # %Y-%m-%d takes it unpadded, fromisoformat does not
            ("0001-01-01", date(1, 1, 1)),  # Earliest representable, a boundary on the year
            ("2024-02-29", date(2024, 2, 29)),  # Leap day
            # A time component is parsed and discarded, whatever separates it.
            ("2025-08-29T00:00:00", date(2025, 8, 29)),
            ("2025-08-29T14:30:45", date(2025, 8, 29)),
            ("2026-03-31 10:11:00", date(2026, 3, 31)),
            ("2025-08-29T14:30:45.123456", date(2025, 8, 29)),
            ("2026-03-31 10:11:00.123456", date(2026, 3, 31)),
            ("2025-12-31T23:59:59", date(2025, 12, 31)),  # Last second of the year
            # Zone designators. %z reads all three, which is why no format spells Z.
            ("2025-08-29T14:30:45Z", date(2025, 8, 29)),
            ("2025-08-29T14:30:45+00:00", date(2025, 8, 29)),
            ("2025-08-29T14:30:45+0500", date(2025, 8, 29)),  # No colon; only %z takes it
        ],
    )
    def test_parseable_values(self, value, expected):
        """Every shape the docstring lists converts to its date portion."""
        assert to_date(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            "   ",
            "not-a-date",
            "abc-def-ghi",
            "2025/08/29",  # Wrong separator
            "08-29-2025",  # Wrong order
            "2025",  # Incomplete
        ],
    )
    def test_unparseable_values_return_none(self, value):
        """Absent and malformed values yield None instead of raising.

        API-supplied values coerce leniently, matching the numeric coercers; only
        user-supplied parameters raise, via the validators in utils/validations.py.
        Values of a wrong type entirely are covered below, where the warning they
        must also emit is asserted.
        """
        assert to_date(value) is None

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
        not available either, since ``date`` is an immutable C type, and replacing
        the module's ``date`` name with a plain stub would break the isinstance
        checks above it. ``_freeze_today`` below does replace that name, which is
        safe only because it substitutes a ``date`` subclass, leaving every
        isinstance check satisfied.
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

    @pytest.mark.parametrize("value", [123, 1.5, b"2025-08-29", [1], object()])
    @patch("usaspending.utils.dates.logger")
    def test_a_value_that_is_not_a_date_at_all_returns_none(self, mock_logger, value):
        """An unusable type answers None, like every other coercer in the package.

        ``utils/numbers.py`` states the convention for the family: a missing or
        unparseable value answers None rather than raising. This one used to let a
        TypeError out of ``strptime``, or out of the length check ahead of it, so
        it was the only coercer that could raise on a caller's bad input.

        Every value here is truthy, so each reaches the parsing below rather than
        the missing-value guard. A falsy one of any type, ``[]`` as much as ``""``,
        is the missing case and answers None without a warning.
        """
        assert to_date(value) is None
        mock_logger.warning.assert_called_once()

    def test_a_value_with_no_date_shape_leaves_the_shared_strptime_cache_alone(self):
        """Rejecting a non-date must not evict regexes other callers rely on.

        CPython caches compiled strptime patterns in one process-global dict and
        clears the whole thing when it exceeds five entries. Walking the format
        list to exhaustion therefore flushes every entry in the process, making
        the next `strptime` call anywhere in the application recompile, so one bad
        API field charges its cost to unrelated code. The shape check is what
        keeps such a value out of the walk.
        """
        datetime.strptime("15/01/2024", "%d/%m/%Y")
        assert "%d/%m/%Y" in _strptime._regex_cache

        assert to_date("this is not a date at all") is None

        assert "%d/%m/%Y" in _strptime._regex_cache

    def test_a_date_shaped_value_that_matches_nothing_still_evicts(self):
        """The shape check narrows what reaches the walk; it does not shorten it.

        Six formats is one more than the cache holds, so a value that passes the
        shape check and then matches none of them still costs an unrelated caller
        its compiled pattern. Pinned rather than fixed: closing it means folding
        the four datetime formats into two by normalizing the `T` separator, which
        would widen what parses. This documents the residual so the shape check is
        not mistaken for a complete answer.
        """
        datetime.strptime("15/01/2024", "%d/%m/%Y")
        assert "%d/%m/%Y" in _strptime._regex_cache

        assert to_date("2025-08-29GARBAGE") is None

        assert "%d/%m/%Y" not in _strptime._regex_cache

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


def _freeze_today(monkeypatch: pytest.MonkeyPatch, frozen: date) -> None:
    """Pin what ``date.today()`` answers inside ``usaspending.utils.dates``.

    The module's ``date`` name is replaced rather than ``date.today`` itself,
    which is unpatchable on an immutable C type. A subclass keeps every other use
    of the name working, and the substitution lasts only for the test that asks
    for it, so the isinstance checks in ``to_date`` never see it.

    Args:
        monkeypatch: The fixture that undoes the substitution afterwards.
        frozen: The date ``today()`` should report.
    """

    class FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return frozen

    monkeypatch.setattr("usaspending.utils.dates.date", FrozenDate)


class TestCurrentFiscalYear:
    """The federal fiscal year rule: October 1 opens the year named for its end."""

    @pytest.mark.parametrize(
        ("today", "expected"),
        [
            # The boundary, from both sides. The two calendar-year edges below it
            # are the sanity check that the halves are not swapped.
            (date(2026, 9, 30), 2026),  # Last day of FY2026
            (date(2026, 10, 1), 2027),  # First day of FY2027
            (date(2026, 1, 1), 2026),
            (date(2026, 12, 31), 2027),  # A December date belongs to the next year
        ],
    )
    def test_the_fiscal_year_of_a_given_day(self, monkeypatch, today, expected):
        _freeze_today(monkeypatch, today)

        assert current_fiscal_year() == expected

    def test_it_is_importable_from_the_utils_package(self):
        """It is exported, unlike at 0.7.3 where it sat in a module now removed.

        ``usaspending.utils.formatter`` is gone for good, so this is the only
        supported import path and the one the changelog points at.
        """
        import usaspending.utils as utils

        assert utils.current_fiscal_year is current_fiscal_year
        assert "current_fiscal_year" in utils.__all__
