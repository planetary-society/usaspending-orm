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

from usaspending.exceptions import ValidationError
from usaspending.queries.awards_search import AwardsSearch


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
        # Canonical order, not insertion order: see _canonical.
        assert filter_dict == {"keywords": ["NASA", "research", "space"]}


class TestTimePeriodFilter:
    """Test time_period filter method."""

    def test_time_period_with_dates(self, search_builder):
        """Test time_period with date objects."""
        start = datetime.date(2024, 1, 1)
        end = datetime.date(2024, 12, 31)

        result = search_builder.time_period(start_date=start, end_date=end, date_type="action_date")

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

    def test_time_period_with_datetimes(self, search_builder):
        """A datetime is accepted wherever a date is, and serializes the same.

        Regression: datetime subclasses date, so this was always type-legal, but
        the unnarrowed bound reached the FY2008 floor check and raised
        ``TypeError: can't compare datetime.datetime to datetime.date``.
        """
        result = search_builder.time_period(
            start_date=datetime.datetime(2024, 1, 1, 9, 30, 0),
            end_date=datetime.datetime(2024, 12, 31, 17, 45, 30),
            date_type="action_date",
        )

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

    def test_time_period_still_validates_datetime_bounds(self, search_builder):
        """The FY2008 floor is enforced for a datetime bound, not skipped.

        Guards a different repair than the test above: the TypeError came from
        this comparison, so the tempting bad fix is to skip it for datetimes
        rather than to narrow them. Narrowing correctly and validating are two
        claims, and only this one fails if the second is dropped.
        """
        with pytest.raises(ValidationError, match="before the minimum supported date"):
            search_builder.time_period(
                start_date=datetime.datetime(2007, 9, 30, 23, 59, 59),
                end_date=datetime.datetime(2008, 9, 30, 0, 0),
            )

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

    def test_time_period_rejects_date_before_fy2008_start(self, search_builder):
        """Test time_period rejects start_date before FY2008 (2007-10-01)."""
        with pytest.raises(ValidationError, match="before the minimum supported date"):
            search_builder.time_period(
                start_date="2007-09-30",  # One day before FY2008
                end_date="2008-09-30",
            )

    def test_time_period_rejects_end_date_before_fy2008(self, search_builder):
        """Test time_period rejects end_date before FY2008."""
        with pytest.raises(ValidationError, match="before the minimum supported date"):
            search_builder.time_period(
                start_date="2007-10-01",  # Valid
                end_date="2007-09-30",  # Invalid - before FY2008
            )

    def test_time_period_accepts_fy2008_start_date(self, search_builder):
        """Test time_period accepts dates starting from FY2008."""
        # 2007-10-01 is the first day of FY2008 and should be valid
        result = search_builder.time_period(
            start_date="2007-10-01",
            end_date="2008-09-30",
        )
        assert len(result._filter_objects) == 1

    def test_time_period_rejects_end_before_start(self, search_builder):
        """Invalid ranges (end < start) are rejected.

        Regression: previously only the FY2008 floor was checked; nonsensical
        ranges such as ``time_period("2024-06-01", "2024-01-01")`` passed
        validation and were silently sent to the API.
        """
        with pytest.raises(ValidationError, match="must be on or after start_date"):
            search_builder.time_period(
                start_date="2024-06-01",
                end_date="2024-01-01",
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
        """Test fiscal_year rejects year before 2008."""
        with pytest.raises(ValidationError, match="Must be >= 2008"):
            search_builder.fiscal_year(year=24)  # Invalid: too low


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
        """Test recipient_search_text filter with single term."""
        result = search_builder.recipient_search_text("SpaceX")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"recipient_search_text": ["SpaceX"]}

    def test_recipient_search_text_empty_raises_error(self, search_builder):
        """Test recipient_search_text rejects empty string."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            search_builder.recipient_search_text("")

    def test_recipient_search_text_whitespace_raises_error(self, search_builder):
        """Test recipient_search_text rejects whitespace-only string."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            search_builder.recipient_search_text("   ")

    def test_recipient_type_names(self, search_builder):
        """Test recipient_type_names filter."""
        result = search_builder.recipient_type_names("small_business", "woman_owned_business")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"recipient_type_names": ["small_business", "woman_owned_business"]}


class TestAgencyFilters:
    """Test agency filter methods."""

    def test_agencies_single(self, search_builder):
        """Test agencies filter with single agency."""
        result = search_builder.agencies({"name": "NASA", "type": "awarding", "tier": "toptier"})

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
        result = search_builder.agency("NASA", agency_type="awarding", tier="toptier")

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
        assert set(filter_dict["award_type_codes"]) == {"07", "08", "F003", "F004"}

    def test_grants(self, search_builder):
        """Test grants convenience method."""
        result = search_builder.grants()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert set(filter_dict["award_type_codes"]) == {"02", "03", "04", "05", "F001", "F002"}

    def test_direct_payments(self, search_builder):
        """Test direct_payments convenience method."""
        result = search_builder.direct_payments()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert set(filter_dict["award_type_codes"]) == {"06", "10", "F006", "F007"}

    def test_other_assistance(self, search_builder):
        """Test other_assistance convenience method."""
        result = search_builder.other_assistance()

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert set(filter_dict["award_type_codes"]) == {
            "09",
            "11",
            "-1",
            "F005",
            "F008",
            "F009",
            "F010",
        }


class TestClassificationCodeFilters:
    """Test classification code filter methods."""

    def test_program_numbers(self, search_builder):
        """Test program_numbers filter (CFDA/Assistance Listing numbers)."""
        result = search_builder.program_numbers("10.001", "10.002")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"program_numbers": ["10.001", "10.002"]}

    def test_naics_codes(self, search_builder):
        """Test naics_codes filter with require and exclude using flat arrays."""
        result = search_builder.naics_codes(
            require=["54", "541512"],
            exclude=["541519"],
        )

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        # Per API docs, NAICS uses flat arrays (not nested like TAS/PSC)
        assert filter_dict == {
            "naics_codes": {
                "require": ["54", "541512"],
                "exclude": ["541519"],
            }
        }

    def test_naics_codes_require_only(self, search_builder):
        """Test naics_codes filter with only require."""
        result = search_builder.naics_codes(require=["62"])

        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"naics_codes": {"require": ["62"]}}

    def test_naics_codes_accepts_200_combined_codes(self, search_builder):
        """The upstream combined-code boundary remains valid."""
        result = search_builder.naics_codes(
            require=[f"R{i}" for i in range(120)],
            exclude=[f"E{i}" for i in range(80)],
        )

        filter_dict = result._filter_objects[0].to_dict()["naics_codes"]
        assert len(filter_dict["require"]) + len(filter_dict["exclude"]) == 200

    def test_naics_codes_rejects_more_than_200_combined_codes(
        self, search_builder, mock_usa_client
    ):
        """An oversized NAICS request fails before HTTP."""
        mock_usa_client.forbid_requests()

        with pytest.raises(ValidationError, match=r"naics_codes.*201.*200"):
            search_builder.naics_codes(
                require=[f"R{i}" for i in range(120)],
                exclude=[f"E{i}" for i in range(81)],
            )

        assert mock_usa_client._request_history == []

    def test_naics_codes_copies_caller_owned_lists(self, search_builder):
        """Mutating inputs cannot alter an already-built filter."""
        require = ["54"]
        exclude = ["62"]
        result = search_builder.naics_codes(require=require, exclude=exclude)

        require.append("92")
        exclude.clear()

        assert result._filter_objects[0].to_dict() == {
            "naics_codes": {"require": ["54"], "exclude": ["62"]}
        }

    def test_psc_codes_simple_format(self, search_builder):
        """Test psc_codes filter with simple list format."""
        result = search_builder.psc_codes("1510", "1520")

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"psc_codes": ["1510", "1520"]}

    def test_psc_codes_simple_format_accepts_200_codes(self, search_builder):
        """The upstream simple-code boundary remains valid."""
        result = search_builder.psc_codes(*(f"A{i}" for i in range(200)))

        assert len(result._filter_objects[0].to_dict()["psc_codes"]) == 200

    def test_psc_codes_simple_format_rejects_more_than_200_codes(
        self, search_builder, mock_usa_client
    ):
        """Upstream converts flat PSC codes to paths before its 200-code guard."""
        mock_usa_client.forbid_requests()

        with pytest.raises(ValidationError, match=r"psc_codes.*201.*200"):
            search_builder.psc_codes(*(f"A{i}" for i in range(201)))

        assert mock_usa_client._request_history == []

    def test_psc_codes_hierarchical_format(self, search_builder):
        """Test psc_codes filter with hierarchical require/exclude format."""
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

    def test_psc_codes_accepts_200_combined_hierarchical_paths(self, search_builder):
        """Both sides may reach 100 paths for a combined total of 200."""
        result = search_builder.psc_codes(
            require=[["Service", "R"] for _ in range(100)],
            exclude=[["Product", "1"] for _ in range(100)],
        )

        filter_dict = result._filter_objects[0].to_dict()["psc_codes"]
        assert len(filter_dict["require"]) + len(filter_dict["exclude"]) == 200

    def test_psc_tier_one_expansion_counts_toward_combined_limit(
        self, search_builder, mock_usa_client
    ):
        """Nine Service roots become 225 paths before upstream complexity checks."""
        mock_usa_client.forbid_requests()

        with pytest.raises(ValidationError, match=r"psc_codes.*225.*200"):
            search_builder.psc_codes(require=[["Service"] for _ in range(9)])

        assert mock_usa_client._request_history == []

    @pytest.mark.parametrize("side", ["require", "exclude"])
    def test_psc_codes_rejects_more_than_100_paths_per_side(
        self, search_builder, mock_usa_client, side
    ):
        """Each hierarchical PSC side has its own upstream request bound."""
        mock_usa_client.forbid_requests()
        kwargs = {
            "require": [[f"R{i}"] for i in range(100)],
            "exclude": [[f"E{i}"] for i in range(100)],
        }
        kwargs[side].append([f"{side}-overflow"])

        with pytest.raises(ValidationError, match=rf"psc_codes\.{side}.*101.*100"):
            search_builder.psc_codes(**kwargs)

        assert mock_usa_client._request_history == []

    def test_psc_codes_accepts_depth_10_and_rejects_depth_11(self, search_builder):
        """PSC depth is measured after removing its Tier-1 group name."""
        valid_path = ["Product", *["1" for _ in range(10)]]
        invalid_path = ["Product", *["1" for _ in range(11)]]
        valid = search_builder.psc_codes(require=[valid_path])

        assert valid._filter_objects[0].to_dict()["psc_codes"]["require"][0] == valid_path
        with pytest.raises(ValidationError, match=r"psc_codes.*11.*10"):
            search_builder.psc_codes(require=[invalid_path])

    def test_psc_codes_copies_nested_caller_owned_lists(self, search_builder):
        """Outer and inner path mutations cannot alter a built PSC filter."""
        require = [["Service", "R"]]
        exclude = [["Product", "15"]]
        result = search_builder.psc_codes(require=require, exclude=exclude)

        require[0].append("R499")
        require.append(["Service", "D"])
        exclude.clear()

        assert result._filter_objects[0].to_dict() == {
            "psc_codes": {
                "require": [["Service", "R"]],
                "exclude": [["Product", "15"]],
            }
        }

    def test_psc_codes_mixed_format_raises_error(self, search_builder):
        """Test psc_codes rejects mixing simple codes with require/exclude."""
        with pytest.raises(ValidationError, match="Cannot mix"):
            search_builder.psc_codes("1510", require=[["Service", "R"]])

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
        # Canonical order, not insertion order: see _canonical.
        assert filter_dict == {"set_aside_type_codes": ["8AN", "SBA"]}

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

    def test_tas_codes_accepts_200_combined_paths(self, search_builder):
        """Both sides may reach 100 paths for a combined total of 200."""
        result = search_builder.tas_codes(
            require=[[f"R{i}"] for i in range(100)],
            exclude=[[f"E{i}"] for i in range(100)],
        )

        filter_dict = result._filter_objects[0].to_dict()["tas_codes"]
        assert len(filter_dict["require"]) + len(filter_dict["exclude"]) == 200

    @pytest.mark.parametrize("side", ["require", "exclude"])
    def test_tas_codes_rejects_more_than_100_paths_per_side(
        self, search_builder, mock_usa_client, side
    ):
        """Each hierarchical TAS side has its own upstream request bound."""
        mock_usa_client.forbid_requests()
        kwargs = {
            "require": [[f"R{i}"] for i in range(100)],
            "exclude": [[f"E{i}"] for i in range(100)],
        }
        kwargs[side].append([f"{side}-overflow"])

        with pytest.raises(ValidationError, match=rf"tas_codes\.{side}.*101.*100"):
            search_builder.tas_codes(**kwargs)

        assert mock_usa_client._request_history == []

    def test_tas_codes_accepts_depth_10_and_rejects_depth_11(self, search_builder):
        """Hierarchical TAS paths mirror the upstream depth boundary."""
        valid = search_builder.tas_codes(require=[[f"T{i}" for i in range(10)]])

        assert len(valid._filter_objects[0].to_dict()["tas_codes"]["require"][0]) == 10
        with pytest.raises(ValidationError, match=r"tas_codes.*11.*10"):
            search_builder.tas_codes(require=[[f"T{i}" for i in range(11)]])

    def test_tas_codes_copies_nested_caller_owned_lists(self, search_builder):
        """Outer and inner path mutations cannot alter a built TAS filter."""
        require = [["012"]]
        exclude = [["012", "0123"]]
        result = search_builder.tas_codes(require=require, exclude=exclude)

        require[0].append("012-0001")
        require.append(["080"])
        exclude.clear()

        assert result._filter_objects[0].to_dict() == {
            "tas_codes": {
                "require": [["012"]],
                "exclude": [["012", "0123"]],
            }
        }

    def test_treasury_account_components(self, search_builder):
        """Test treasury_account_components filter."""
        result = search_builder.treasury_account_components({"aid": "012", "main": "0100"})

        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"treasury_account_components": [{"aid": "012", "main": "0100"}]}

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
            search_builder.keywords("space")
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


# ==============================================================================
# Subaward Date Type Restriction Tests
# ==============================================================================


class TestSubAwardTimePeriodRestrictions:
    """Test that SubAwardsSearch restricts date_type options per API docs."""

    @pytest.fixture
    def subaward_builder(self, mock_usa_client):
        """Create a SubAwardsSearch instance."""
        from usaspending.queries.subawards_search import SubAwardsSearch

        return SubAwardsSearch(mock_usa_client)

    def test_subaward_accepts_action_date(self, subaward_builder):
        """Test that subaward search accepts action_date date_type."""
        result = subaward_builder.time_period(
            start_date="2024-01-01",
            end_date="2024-12-31",
            date_type="action_date",
        )
        assert len(result._filter_objects) == 1

    def test_subaward_accepts_last_modified_date(self, subaward_builder):
        """Test that subaward search accepts last_modified_date date_type."""
        result = subaward_builder.time_period(
            start_date="2024-01-01",
            end_date="2024-12-31",
            date_type="last_modified_date",
        )
        assert len(result._filter_objects) == 1

    def test_subaward_rejects_date_signed(self, subaward_builder):
        """Test that subaward search rejects date_signed date_type."""
        with pytest.raises(ValidationError, match="Only 'action_date' or 'last_modified_date'"):
            subaward_builder.time_period(
                start_date="2024-01-01",
                end_date="2024-12-31",
                date_type="date_signed",
            )

    def test_subaward_rejects_new_awards_only_flag(self, subaward_builder):
        """Test that subaward search rejects new_awards_only parameter."""
        with pytest.raises(ValidationError, match="not supported for subaward"):
            subaward_builder.time_period(
                start_date="2024-01-01",
                end_date="2024-12-31",
                new_awards_only=True,
            )

    def test_subaward_default_date_type(self, subaward_builder):
        """Test that subaward search works with no date_type (defaults to action_date)."""
        result = subaward_builder.time_period(
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        assert len(result._filter_objects) == 1
