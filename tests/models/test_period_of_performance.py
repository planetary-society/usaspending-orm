from datetime import date
from unittest.mock import patch

import pytest

from usaspending.models.period_of_performance import PeriodOfPerformance


class TestSearchResultKeys:
    """The flat keys an award search result carries are read by this model.

    An award search result reports these dates as flat, title-cased keys rather
    than the nested object a detail response sends. Reading them here, rather than
    having `Award` translate them on the way in, keeps one owner for the mapping.
    """

    def test_every_flat_key_is_read(self):
        """Each documented flat spelling reaches the property that owns it."""
        period = PeriodOfPerformance(
            {
                "Start Date": "2020-01-01",
                "End Date": "2021-06-30",
                "Last Modified Date": "2022-03-15",
                "Period of Performance Potential End Date": "2023-09-30",
            }
        )

        assert period.start_date == date(2020, 1, 1)
        assert period.end_date == date(2021, 6, 30)
        assert period.last_modified_date == date(2022, 3, 15)
        assert period.potential_end_date == date(2023, 9, 30)

    def test_base_obligation_date_backs_the_start_date(self):
        """`Base Obligation Date` is the third spelling of a start date.

        Award search results use it where others send `Start Date`. It was read by
        `Award` and not by this model, which is why `Award` could not simply hand
        its payload over.
        """
        assert PeriodOfPerformance({"Base Obligation Date": "2019-05-05"}).start_date == date(
            2019, 5, 5
        )

    def test_an_explicit_start_date_wins_over_base_obligation_date(self):
        """Order matters: the more specific spelling is preferred."""
        period = PeriodOfPerformance(
            {"Start Date": "2020-01-01", "Base Obligation Date": "2019-05-05"}
        )

        assert period.start_date == date(2020, 1, 1)

    def test_from_search_result_takes_only_its_own_keys(self):
        """The projection is scoped, so `raw` describes a period and not an award.

        It must also copy, not alias: `Award._fetch_details` replaces its payload
        in place, and this model reads `last_modified_date` lazily, so a shared
        reference would let a later fetch change an already-built object.
        """
        award_data = {
            "Start Date": "2020-01-01",
            "Last Modified Date": "2022-03-15",
            "Award ID": "CONT_AWD_1",
            "Recipient Name": "ACME",
        }

        period = PeriodOfPerformance._from_search_result(award_data)

        assert set(period.raw) == {"Start Date", "Last Modified Date"}

        award_data.clear()
        assert period.last_modified_date == date(2022, 3, 15)


class TestPeriodOfPerformance:
    """Test PeriodOfPerformance model"""

    @pytest.fixture
    def sample_period_data(self):
        """Sample period of performance data from contract.json"""
        return {
            "start_date": "2018-03-05",
            "end_date": "2025-08-23",
            "last_modified_date": "2025-06-23",
            "potential_end_date": "2025-08-23 00:00:00",
        }

    @pytest.fixture
    def period_with_alternate_keys(self):
        """Period data with alternate key names"""
        return {
            "Start Date": "2020-01-01",
            "End Date": "2021-12-31",
            "Last Modified Date": "2021-06-15",
            "Period of Performance Start Date": "2020-01-01",
            "Period of Performance Current End Date": "2021-12-31",
        }

    @pytest.fixture
    def empty_period_data(self):
        """Empty period data"""
        return {}

    def test_initialization(self, sample_period_data):
        """Test basic initialization with valid data"""
        period = PeriodOfPerformance(sample_period_data)
        assert period._data == sample_period_data
        assert isinstance(period, PeriodOfPerformance)

    def test_start_date_property(self, sample_period_data):
        """Test start_date property returns correct date"""
        period = PeriodOfPerformance(sample_period_data)
        start_date = period.start_date
        assert isinstance(start_date, date)
        assert start_date.year == 2018
        assert start_date.month == 3
        assert start_date.day == 5

    def test_end_date_property(self, sample_period_data):
        """Test end_date property returns correct date"""
        period = PeriodOfPerformance(sample_period_data)
        end_date = period.end_date
        assert isinstance(end_date, date)
        assert end_date.year == 2025
        assert end_date.month == 8
        assert end_date.day == 23

    def test_last_modified_date_property(self, sample_period_data):
        """Test last_modified_date property returns correct date"""
        period = PeriodOfPerformance(sample_period_data)
        last_modified = period.last_modified_date
        assert isinstance(last_modified, date)
        assert last_modified.year == 2025
        assert last_modified.month == 6
        assert last_modified.day == 23

    def test_alternate_key_names(self, period_with_alternate_keys):
        """Test that alternate key names are properly handled"""
        period = PeriodOfPerformance(period_with_alternate_keys)

        # Should pick up "Start Date"
        start_date = period.start_date
        assert isinstance(start_date, date)
        assert start_date.year == 2020
        assert start_date.month == 1
        assert start_date.day == 1

        # Should pick up "End Date"
        end_date = period.end_date
        assert isinstance(end_date, date)
        assert end_date.year == 2021
        assert end_date.month == 12
        assert end_date.day == 31

        # Should pick up "Last Modified Date"
        last_modified = period.last_modified_date
        assert isinstance(last_modified, date)
        assert last_modified.year == 2021
        assert last_modified.month == 6
        assert last_modified.day == 15

    def test_period_of_performance_keys_priority(self):
        """Test that Period of Performance keys have lower priority"""
        data = {
            "start_date": "2022-01-01",
            "Period of Performance Start Date": "2020-01-01",
            "end_date": "2022-12-31",
            "Period of Performance Current End Date": "2020-12-31",
        }
        period = PeriodOfPerformance(data)

        # Should use start_date over Period of Performance Start Date
        assert period.start_date.year == 2022
        assert period.end_date.year == 2022

    def test_empty_data_returns_none(self, empty_period_data):
        """Test that empty data returns None for all properties"""
        period = PeriodOfPerformance(empty_period_data)
        assert period.start_date is None
        assert period.end_date is None
        assert period.last_modified_date is None

    def test_missing_keys_return_none(self):
        """Test that missing keys return None"""
        partial_data = {
            "start_date": "2020-01-01",
            # end_date and last_modified_date are missing
        }
        period = PeriodOfPerformance(partial_data)
        assert period.start_date is not None
        assert period.end_date is None
        assert period.last_modified_date is None

    def test_invalid_date_format_returns_none(self):
        """Test that invalid date formats return None"""
        invalid_data = {
            "start_date": "invalid-date",
            "end_date": "2020/01/01",  # Wrong format
            "last_modified_date": "January 1, 2020",  # Wrong format
        }
        period = PeriodOfPerformance(invalid_data)
        assert period.start_date is None
        assert period.end_date is None
        assert period.last_modified_date is None

    def test_repr_with_complete_data(self, sample_period_data):
        """Test __repr__ with complete data"""
        period = PeriodOfPerformance(sample_period_data)
        repr_str = repr(period)
        assert repr_str == "<Period of Performance 2018-03-05 -> 2025-08-23>"

    def test_repr_with_missing_start_date(self):
        """Test __repr__ with missing start date"""
        data = {"end_date": "2025-08-23"}
        period = PeriodOfPerformance(data)
        repr_str = repr(period)
        assert repr_str == "<Period of Performance ? -> 2025-08-23>"

    def test_repr_with_missing_end_date(self):
        """Test __repr__ with missing end date"""
        data = {"start_date": "2018-03-05"}
        period = PeriodOfPerformance(data)
        repr_str = repr(period)
        assert repr_str == "<Period of Performance 2018-03-05 -> ?>"

    def test_repr_with_no_dates(self, empty_period_data):
        """Test __repr__ with no dates"""
        period = PeriodOfPerformance(empty_period_data)
        repr_str = repr(period)
        assert repr_str == "<Period of Performance ? -> ?>"

    def test_null_values_return_none(self):
        """Test that null values return None"""
        null_data = {"start_date": None, "end_date": None, "last_modified_date": None}
        period = PeriodOfPerformance(null_data)
        assert period.start_date is None
        assert period.end_date is None
        assert period.last_modified_date is None

    def test_empty_string_values_return_none(self):
        """Test that empty string values return None"""
        empty_string_data = {"start_date": "", "end_date": "", "last_modified_date": ""}
        period = PeriodOfPerformance(empty_string_data)
        assert period.start_date is None
        assert period.end_date is None
        assert period.last_modified_date is None

    def test_get_value_prioritization(self):
        """Test that get_value properly prioritizes keys"""
        # Data with multiple possible keys
        data = {
            "start_date": None,  # Empty, should be skipped
            "Start Date": "2020-01-01",  # Should be used
            "Period of Performance Start Date": "2019-01-01",  # Should be ignored
        }
        period = PeriodOfPerformance(data)
        assert period.start_date.year == 2020

    def test_raw_data_access(self, sample_period_data):
        """Test access to raw data through inherited methods"""
        period = PeriodOfPerformance(sample_period_data)
        assert period.raw == sample_period_data
        assert period.to_dict() == sample_period_data

    def test_initialization_with_none(self):
        """Test initialization with None returns None for all properties"""
        period = PeriodOfPerformance(None)
        # With None data, all properties should return None
        assert period.start_date is None
        assert period.end_date is None
        assert period.last_modified_date is None

    @patch("usaspending.utils.dates.logger")
    def test_date_parsing_warning(self, mock_logger):
        """Test that invalid dates log warnings"""
        invalid_data = {"start_date": "invalid-date-format"}
        period = PeriodOfPerformance(invalid_data)
        _ = period.start_date
        mock_logger.warning.assert_called_once()
