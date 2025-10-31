"""Tests for the SearchQueryBuilder base class.

This test file covers the common filter methods inherited by AwardsSearch
and SpendingSearch from the SearchQueryBuilder intermediate class.

Following the existing pattern (test_query_builder_pagination.py,
test_query_builder_list_behavior.py), we test the base class functionality
using AwardsSearch as the concrete implementation.
"""

from __future__ import annotations

import datetime

import pytest

from usaspending.queries.awards_search import AwardsSearch
from usaspending.exceptions import ValidationError


@pytest.fixture
def search_builder(mock_usa_client):
    """Create an AwardsSearch instance to test SearchQueryBuilder methods."""
    return AwardsSearch(mock_usa_client)


class TestKeywordsFilter:
    """Test keywords filter method."""

    def test_keywords(self, search_builder):
        """Test keywords filter creation and immutability."""
        result = search_builder.keywords("NASA", "space", "research")

        # Should return new instance
        assert result is not search_builder
        assert len(result._filter_objects) == 1
        assert len(search_builder._filter_objects) == 0

        # Check filter content
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"keywords": ["NASA", "space", "research"]}


class TestTimePeriodFilter:
    """Test time_period filter method."""

    def test_time_period_with_dates(self, search_builder):
        """Test time_period with date objects."""
        start = datetime.date(2024, 1, 1)
        end = datetime.date(2024, 12, 31)

        result = search_builder.time_period(
            start_date=start, end_date=end, date_type="action_date"
        )

        assert result is not search_builder
        assert len(result._filter_objects) == 1

        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "time_period": [
                {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "date_type": "action_date",
                }
            ]
        }

    def test_time_period_with_string_dates(self, search_builder):
        """Test time_period with string dates."""
        result = search_builder.time_period(
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "time_period": [
                {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                }
            ]
        }

    def test_time_period_new_awards_convenience(self, search_builder):
        """Test time_period with new_awards_only convenience parameter."""
        result = search_builder.time_period(
            start_date="2024-01-01",
            end_date="2024-12-31",
            new_awards_only=True,
        )

        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict["time_period"][0]["date_type"] == "new_awards_only"

    def test_time_period_invalid_string_format(self, search_builder):
        """Test time_period rejects invalid date format."""
        with pytest.raises(ValidationError, match="Invalid start_date format"):
            search_builder.time_period(
                start_date="01/01/2024",  # Wrong format
                end_date="2024-12-31",
            )


class TestFiscalYearFilter:
    """Test fiscal_year convenience method."""

    def test_fiscal_year_basic(self, search_builder):
        """Test fiscal_year creates correct date range."""
        result = search_builder.fiscal_year(year=2024)

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()

        # FY2024 runs from Oct 1, 2023 to Sep 30, 2024
        assert filter_dict == {
            "time_period": [{"start_date": "2023-10-01", "end_date": "2024-09-30"}]
        }

    def test_fiscal_year_new_awards_only(self, search_builder):
        """Test fiscal_year with new_awards_only parameter."""
        result = search_builder.fiscal_year(year=2024, new_awards_only=True)

        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "time_period": [
                {
                    "start_date": "2023-10-01",
                    "end_date": "2024-09-30",
                    "date_type": "new_awards_only",
                }
            ]
        }

    def test_fiscal_year_invalid_year(self, search_builder):
        """Test fiscal_year rejects invalid year format."""
        with pytest.raises(ValidationError, match="4-digit integer"):
            search_builder.fiscal_year(year=24)  # Should be 2024


class TestPlaceOfPerformanceFilters:
    """Test place of performance filter methods."""

    def test_place_of_performance_scope(self, search_builder):
        """Test place_of_performance_scope filter."""
        result = search_builder.place_of_performance_scope("domestic")

        assert len(result._filter_objects) == 1
        filter_obj = result._filter_objects[0]
        assert filter_obj.key == "place_of_performance_scope"
        assert filter_obj.scope.value == "domestic"

        filter_dict = filter_obj.to_dict()
        assert filter_dict == {"place_of_performance_scope": "domestic"}

    def test_place_of_performance_locations(self, search_builder):
        """Test place_of_performance_locations filter."""
        loc1 = {"country_code": "USA", "state_code": "CA", "city_name": "Los Angeles"}
        loc2 = {"country_code": "USA", "state_code": "TX"}

        result = search_builder.place_of_performance_locations(loc1, loc2)

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "place_of_performance_locations": [
                {"country": "USA", "state": "CA", "city": "Los Angeles"},
                {"country": "USA", "state": "TX"},
            ]
        }


class TestRecipientFilters:
    """Test recipient filter methods."""

    def test_recipient_scope(self, search_builder):
        """Test recipient_scope filter."""
        result = search_builder.recipient_scope("foreign")

        assert len(result._filter_objects) == 1
        filter_obj = result._filter_objects[0]
        assert filter_obj.key == "recipient_scope"
        assert filter_obj.scope.value == "foreign"

        filter_dict = filter_obj.to_dict()
        assert filter_dict == {"recipient_scope": "foreign"}

    def test_recipient_locations(self, search_builder):
        """Test recipient_locations filter."""
        loc = {"country_code": "CAN", "state_code": "ON", "city_name": "Toronto"}

        result = search_builder.recipient_locations(loc)

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "recipient_locations": [{"country": "CAN", "state": "ON", "city": "Toronto"}]
        }

    def test_recipient_search_text(self, search_builder):
        """Test recipient_search_text filter."""
        result = search_builder.recipient_search_text("SpaceX", "123456789")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"recipient_search_text": ["SpaceX", "123456789"]}

    def test_recipient_type_names(self, search_builder):
        """Test recipient_type_names filter."""
        result = search_builder.recipient_type_names(
            "small_business", "woman_owned_business"
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "recipient_type_names": ["small_business", "woman_owned_business"]
        }


class TestAgencyFilters:
    """Test agency filter methods."""

    def test_agencies_single(self, search_builder):
        """Test agencies filter with single agency."""
        result = search_builder.agencies(
            {"name": "NASA", "type": "awarding", "tier": "toptier"}
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "agencies": [{"name": "NASA", "type": "awarding", "tier": "toptier"}]
        }

    def test_agencies_multiple(self, search_builder):
        """Test agencies filter with multiple agencies."""
        result = search_builder.agencies(
            {"name": "NASA", "type": "awarding", "tier": "toptier"},
            {"name": "DOD", "type": "funding", "tier": "toptier"},
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert len(filter_dict["agencies"]) == 2

    def test_agency_convenience_method(self, search_builder):
        """Test agency convenience method for single agency."""
        result = search_builder.agency(
            "NASA", agency_type="awarding", tier="toptier"
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "agencies": [{"type": "awarding", "tier": "toptier", "name": "NASA"}]
        }


class TestAwardFilters:
    """Test award-related filter methods."""

    def test_award_ids(self, search_builder):
        """Test award_ids filter."""
        result = search_builder.award_ids("CONT_AWD_123", "CONT_AWD_456")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"award_ids": ["CONT_AWD_123", "CONT_AWD_456"]}

    def test_award_amounts(self, search_builder):
        """Test award_amounts filter."""
        result = search_builder.award_amounts(
            {"lower_bound": 1000000, "upper_bound": 5000000},
            {"lower_bound": 10000000},
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "award_amounts": [
                {"lower_bound": 1000000, "upper_bound": 5000000},
                {"lower_bound": 10000000},
            ]
        }

    def test_award_type_codes(self, search_builder):
        """Test award_type_codes filter (base implementation without validation)."""
        # Note: AwardsSearch overrides this with validation
        # Here we test the base SearchQueryBuilder implementation
        result = search_builder.award_type_codes("A", "B", "C", "D")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"award_type_codes": ["A", "B", "C", "D"]}


class TestAwardTypeConvenienceMethods:
    """Test award type convenience methods."""

    def test_contracts(self, search_builder):
        """Test contracts convenience method."""
        result = search_builder.contracts()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        # Should include all contract codes
        assert set(filter_dict["award_type_codes"]) == {"A", "B", "C", "D"}

    def test_idvs(self, search_builder):
        """Test idvs convenience method."""
        result = search_builder.idvs()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        # Should include all IDV codes
        assert "IDV_A" in filter_dict["award_type_codes"]
        assert "IDV_B" in filter_dict["award_type_codes"]

    def test_loans(self, search_builder):
        """Test loans convenience method."""
        result = search_builder.loans()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert set(filter_dict["award_type_codes"]) == {"07", "08"}

    def test_grants(self, search_builder):
        """Test grants convenience method."""
        result = search_builder.grants()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert set(filter_dict["award_type_codes"]) == {"02", "03", "04", "05"}

    def test_direct_payments(self, search_builder):
        """Test direct_payments convenience method."""
        result = search_builder.direct_payments()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert set(filter_dict["award_type_codes"]) == {"06", "10"}

    def test_other_assistance(self, search_builder):
        """Test other_assistance convenience method."""
        result = search_builder.other_assistance()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert set(filter_dict["award_type_codes"]) == {"09", "11", "-1"}


class TestClassificationCodeFilters:
    """Test classification code filter methods."""

    def test_program_numbers(self, search_builder):
        """Test program_numbers filter (CFDA/Assistance Listing numbers)."""
        result = search_builder.program_numbers("10.001", "10.002")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"program_numbers": ["10.001", "10.002"]}

    def test_naics_codes(self, search_builder):
        """Test naics_codes filter with require and exclude."""
        result = search_builder.naics_codes(
            require=[["54"], ["541512"]],
            exclude=[["541519"]],
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "naics_codes": {
                "require": [[["54"]], [["541512"]]],
                "exclude": [[["541519"]]],
            }
        }

    def test_psc_codes(self, search_builder):
        """Test psc_codes filter."""
        result = search_builder.psc_codes(
            require=[["Service", "R"]],
            exclude=[["Service", "R499"]],
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "psc_codes": {
                "require": [["Service", "R"]],
                "exclude": [["Service", "R499"]],
            }
        }

    def test_contract_pricing_type_codes(self, search_builder):
        """Test contract_pricing_type_codes filter."""
        result = search_builder.contract_pricing_type_codes("A", "B")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"contract_pricing_type_codes": ["A", "B"]}

    def test_set_aside_type_codes(self, search_builder):
        """Test set_aside_type_codes filter."""
        result = search_builder.set_aside_type_codes("SBA", "8AN")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"set_aside_type_codes": ["SBA", "8AN"]}

    def test_extent_competed_type_codes(self, search_builder):
        """Test extent_competed_type_codes filter."""
        result = search_builder.extent_competed_type_codes("A", "B")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"extent_competed_type_codes": ["A", "B"]}

    def test_tas_codes(self, search_builder):
        """Test tas_codes filter."""
        result = search_builder.tas_codes(
            require=[["012"]],
            exclude=[["012", "0123"]],
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "tas_codes": {
                "require": [["012"]],
                "exclude": [["012", "0123"]],
            }
        }

    def test_treasury_account_components(self, search_builder):
        """Test treasury_account_components filter."""
        result = search_builder.treasury_account_components(
            {"aid": "012", "main": "0100"}
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "treasury_account_components": [{"aid": "012", "main": "0100"}]
        }

    def test_def_codes(self, search_builder):
        """Test def_codes filter (Disaster Emergency Fund codes)."""
        result = search_builder.def_codes("L", "M", "N")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"def_codes": ["L", "M", "N"]}


class TestMethodChaining:
    """Test that all filter methods support chaining and immutability."""

    def test_multiple_filters_chain(self, search_builder):
        """Test chaining multiple SearchQueryBuilder filter methods."""
        result = (
            search_builder
            .keywords("space")
            .fiscal_year(2024)
            .place_of_performance_scope("domestic")
            .recipient_type_names("small_business")
        )

        # Should have 4 separate filter objects
        assert len(result._filter_objects) == 4
        # Original should be unchanged
        assert len(search_builder._filter_objects) == 0
        # Each step should return a new instance
        assert result is not search_builder

    def test_immutability(self, search_builder):
        """Test that filter methods don't modify the original instance."""
        original_count = len(search_builder._filter_objects)

        # Apply filters
        result1 = search_builder.keywords("test")
        result2 = search_builder.fiscal_year(2024)
        result3 = result1.fiscal_year(2024)

        # Original unchanged
        assert len(search_builder._filter_objects) == original_count
        # Each result is independent
        assert len(result1._filter_objects) == 1
        assert len(result2._filter_objects) == 1
        assert len(result3._filter_objects) == 2  # Chained from result1
