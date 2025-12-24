# tests/queries/test_filters.py

from __future__ import annotations

import datetime

# Assuming the filter classes are in this location
import pytest

from usaspending.exceptions import ValidationError
from usaspending.queries.filters import (
    AgencyFilter,
    AgencySpec,
    AwardAmount,
    AwardAmountFilter,
    AwardDateType,
    KeywordsFilter,
    LocationSpec,
    LocationFilter,
    MIN_API_DATE,
    MIN_FISCAL_YEAR,
    NAICSFilter,
    PSCFilter,
    parse_fiscal_year,
    parse_location_spec,
    SimpleListFilter,
    TieredCodeFilter,
    TimePeriodFilter,
    TreasuryAccountComponentsFilter,
)

# ==============================================================================
# Test Cases
# ==============================================================================


def test_time_period_filter_serialization():
    """
    Tests that TimePeriodFilter correctly serializes to the API's expected format.
    """
    # Arrange
    start_date = datetime.date(2024, 10, 1)
    end_date = datetime.date(2025, 9, 30)
    time_period_filter = TimePeriodFilter(start_date=start_date, end_date=end_date)
    expected_dict = {
        "time_period": [{"start_date": "2024-10-01", "end_date": "2025-09-30"}]
    }

    # Act
    result_dict = time_period_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


def test_time_period_filter_with_date_type():
    """
    Tests that TimePeriodFilter correctly includes the optional date_type.
    """
    # Arrange
    time_period_filter = TimePeriodFilter(
        start_date=datetime.date(2024, 1, 1),
        end_date=datetime.date(2024, 1, 31),
        date_type=AwardDateType.NEW_AWARDS_ONLY,
    )
    expected_dict = {
        "time_period": [
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "date_type": "new_awards_only",
            }
        ]
    }

    # Act
    result_dict = time_period_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


def test_simple_list_filter_for_award_types():
    """
    Tests that SimpleListFilter works correctly for award_type_codes.
    """
    # Arrange
    award_type_filter = SimpleListFilter(
        key="award_type_codes", values=["A", "B", "C", "D"]
    )
    expected_dict = {"award_type_codes": ["A", "B", "C", "D"]}

    # Act
    result_dict = award_type_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


def test_treasury_account_components_filter_serialization():
    """
    Tests that TreasuryAccountComponentsFilter serializes correctly.
    """
    # Arrange
    components = [{"aid": "080", "main": "0120"}]
    tas_filter = TreasuryAccountComponentsFilter(components=components)
    expected_dict = {"treasury_account_components": [{"aid": "080", "main": "0120"}]}

    # Act
    result_dict = tas_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


def test_agency_filter_serialization():
    """
    Tests that AgencyFilter serializes agencies correctly.
    """
    
    agency_spec = AgencySpec(
        name="Department of Pizza",
        type="funding",
        tier="toptier"
    )
    
    agency_spec_2 = AgencySpec(
        name="Department of Burgers",
        type="awarding",
        tier="toptier"
    )
    
    # Start with a single agency
    agency_filter = AgencyFilter(agencies=[agency_spec])
    expected_dict = {
        "agencies": [
            {
                "name": "Department of Pizza",
                "type": "funding",
                "tier": "toptier",
            }
        ]
    }
    
    result_dict = agency_filter.to_dict()
    assert result_dict == expected_dict
    
    # Now test with two agencies
    dual_agency_filter = AgencyFilter(agencies=[agency_spec, agency_spec_2])
    dual_expected_dict = {
        "agencies": [
            {
                "name": "Department of Pizza",
                "type": "funding",
                "tier": "toptier",
            },
            {
                "name": "Department of Burgers",
                "type": "awarding",
                "tier": "toptier",
            }
        ]
    }
    
    result_dict = dual_agency_filter.to_dict()
    assert result_dict == dual_expected_dict


def test_location_filter_for_state():
    """
    Tests that LocationFilter serializes a simple state location.
    """
    # Arrange
    location = LocationSpec(country_code="USA", state_code="VA")
    location_filter = LocationFilter(
        key="place_of_performance_locations", locations=[location]
    )
    expected_dict = {
        "place_of_performance_locations": [{"country": "USA", "state": "VA"}]
    }

    # Act
    result_dict = location_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


def test_naics_filter_flat_array_format():
    """
    Tests that NAICSFilter serializes to flat arrays per API documentation.

    Per the USASpending API docs, NAICS codes use flat string arrays,
    not nested arrays like PSC/TAS codes.
    """
    # Arrange
    naics_filter = NAICSFilter(
        require=["33", "31", "32"],
        exclude=["336411"],
    )
    expected_dict = {
        "naics_codes": {
            "require": ["33", "31", "32"],
            "exclude": ["336411"],
        }
    }

    # Act
    result_dict = naics_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


def test_naics_filter_require_only():
    """Tests NAICSFilter with only require codes."""
    naics_filter = NAICSFilter(require=["62"])
    expected_dict = {"naics_codes": {"require": ["62"]}}
    assert naics_filter.to_dict() == expected_dict


def test_naics_filter_exclude_only():
    """Tests NAICSFilter with only exclude codes."""
    naics_filter = NAICSFilter(exclude=["325"])
    expected_dict = {"naics_codes": {"exclude": ["325"]}}
    assert naics_filter.to_dict() == expected_dict


def test_naics_filter_empty():
    """Tests that empty NAICSFilter produces empty dict."""
    naics_filter = NAICSFilter()
    expected_dict = {"naics_codes": {}}
    assert naics_filter.to_dict() == expected_dict


def test_tiered_code_filter_handles_empty_lists():
    """
    Tests that TieredCodeFilter correctly omits keys for empty require/exclude lists.
    """
    # Arrange
    empty_filter = TieredCodeFilter(key="psc_codes", require=[], exclude=[])
    require_only_filter = TieredCodeFilter(key="psc_codes", require=[["Service", "B"]])
    exclude_only_filter = TieredCodeFilter(key="psc_codes", exclude=[["Service", "C"]])

    # Act
    empty_dict = empty_filter.to_dict()
    require_dict = require_only_filter.to_dict()
    exclude_dict = exclude_only_filter.to_dict()

    # Assert
    assert empty_dict == {"psc_codes": {}}
    assert require_dict == {"psc_codes": {"require": [["Service", "B"]]}}
    assert exclude_dict == {"psc_codes": {"exclude": [["Service", "C"]]}}


def test_award_amount_filter_serialization():
    """
    Tests that AwardAmountFilter serializes various amount ranges.
    """
    # Arrange
    amounts = [
        AwardAmount(lower_bound=1000000.00, upper_bound=25000000.00),
        AwardAmount(upper_bound=1000000.00),
        AwardAmount(lower_bound=500000000.00),
    ]
    amount_filter = AwardAmountFilter(amounts=amounts)
    expected_dict = {
        "award_amounts": [
            {"lower_bound": 1000000.00, "upper_bound": 25000000.00},
            {"upper_bound": 1000000.00},
            {"lower_bound": 500000000.00},
        ]
    }

    # Act
    result_dict = amount_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


def test_award_amount_handles_empty_object():
    """
    Tests that an empty AwardAmount object serializes to an empty dictionary.
    """
    # Arrange
    amount = AwardAmount()

    # Act
    result_dict = amount.to_dict()

    # Assert
    assert result_dict == {}


def test_keywords_filter():
    """
    Tests that KeywordsFilter serializes a list of keywords.
    """
    # Arrange
    keywords_filter = KeywordsFilter(values=["transport", "logistics"])
    expected_dict = {"keywords": ["transport", "logistics"]}

    # Act
    result_dict = keywords_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


# ==============================================================================
# Fiscal Year Validation Tests
# ==============================================================================


class TestParseFiscalYear:
    """Tests for parse_fiscal_year validation function."""

    def test_valid_integer_year(self):
        """Test that valid integer years are accepted."""
        assert parse_fiscal_year(2024) == 2024
        assert parse_fiscal_year(2008) == 2008  # Minimum valid year
        assert parse_fiscal_year(2100) == 2100

    def test_valid_string_year(self):
        """Test that valid string years are converted to integers."""
        assert parse_fiscal_year("2024") == 2024
        assert parse_fiscal_year("2008") == 2008

    def test_year_before_2008_raises_error(self):
        """Test that years before 2008 raise ValidationError."""
        with pytest.raises(ValidationError, match="Must be >= 2008"):
            parse_fiscal_year(2007)

        with pytest.raises(ValidationError, match="Must be >= 2008"):
            parse_fiscal_year(1999)

        with pytest.raises(ValidationError, match="Must be >= 2008"):
            parse_fiscal_year("2007")

    def test_invalid_string_raises_error(self):
        """Test that non-numeric strings raise ValidationError."""
        with pytest.raises(ValidationError, match="Must be an integer"):
            parse_fiscal_year("invalid")

        with pytest.raises(ValidationError, match="Must be an integer"):
            parse_fiscal_year("twenty-twenty")

    def test_min_fiscal_year_constant(self):
        """Test that MIN_FISCAL_YEAR constant is set correctly."""
        assert MIN_FISCAL_YEAR == 2008

    def test_min_api_date_derived_from_fiscal_year(self):
        """Test that MIN_API_DATE is correctly derived from MIN_FISCAL_YEAR."""
        # Fiscal years start on October 1 of the prior calendar year
        assert MIN_API_DATE == datetime.date(MIN_FISCAL_YEAR - 1, 10, 1)
        assert MIN_API_DATE == datetime.date(2007, 10, 1)


# ==============================================================================
# PSC Filter Tests
# ==============================================================================


class TestPSCFilter:
    """Tests for PSCFilter with both simple and hierarchical formats."""

    def test_simple_list_format(self):
        """Test PSC filter with simple code list."""
        psc_filter = PSCFilter(codes=["1510", "1520"])
        expected = {"psc_codes": ["1510", "1520"]}
        assert psc_filter.to_dict() == expected

    def test_hierarchical_require_format(self):
        """Test PSC filter with hierarchical require structure."""
        psc_filter = PSCFilter(require=[["Service", "D"]])
        expected = {"psc_codes": {"require": [["Service", "D"]]}}
        assert psc_filter.to_dict() == expected

    def test_hierarchical_exclude_format(self):
        """Test PSC filter with hierarchical exclude structure."""
        psc_filter = PSCFilter(exclude=[["Service", "A", "AN"]])
        expected = {"psc_codes": {"exclude": [["Service", "A", "AN"]]}}
        assert psc_filter.to_dict() == expected

    def test_hierarchical_both_require_and_exclude(self):
        """Test PSC filter with both require and exclude."""
        psc_filter = PSCFilter(
            require=[["Service", "A"]],
            exclude=[["Service", "A", "AN"]],
        )
        expected = {
            "psc_codes": {
                "require": [["Service", "A"]],
                "exclude": [["Service", "A", "AN"]],
            }
        }
        assert psc_filter.to_dict() == expected

    def test_simple_format_takes_precedence(self):
        """Test that simple codes format takes precedence over hierarchical."""
        # When both are provided, codes should be used
        psc_filter = PSCFilter(
            codes=["1510"],
            require=[["Service", "D"]],
        )
        expected = {"psc_codes": ["1510"]}
        assert psc_filter.to_dict() == expected

    def test_empty_filter(self):
        """Test empty PSC filter produces empty structure."""
        psc_filter = PSCFilter()
        expected = {"psc_codes": {}}
        assert psc_filter.to_dict() == expected


# ==============================================================================
# Location Validation Tests
# ==============================================================================


class TestLocationValidation:
    """Tests for parse_location_spec validation rules."""

    def test_valid_country_only(self):
        """Test that country-only location is valid."""
        location = parse_location_spec({"country": "DEU"})
        assert location.country_code == "DEU"

    def test_valid_state_with_country(self):
        """Test that state with country is valid."""
        location = parse_location_spec({"country": "USA", "state": "VA"})
        assert location.country_code == "USA"
        assert location.state_code == "VA"

    def test_valid_county_with_state_and_country(self):
        """Test that county with state and country is valid."""
        location = parse_location_spec({
            "country": "USA",
            "state": "VA",
            "county": "059"
        })
        assert location.county_code == "059"

    def test_valid_district_with_state_and_usa(self):
        """Test that district with state and USA country is valid."""
        location = parse_location_spec({
            "country": "USA",
            "state": "VA",
            "district_original": "11"
        })
        assert location.district_original == "11"

    def test_missing_country_raises_error(self):
        """Test that missing country raises ValidationError."""
        with pytest.raises(ValidationError, match="must include 'country'"):
            parse_location_spec({"state": "VA"})

    def test_county_without_state_raises_error(self):
        """Test that county without state raises ValidationError."""
        with pytest.raises(ValidationError, match="county requires state"):
            parse_location_spec({"country": "USA", "county": "059"})

    def test_county_with_district_raises_error(self):
        """Test that county and district together raises ValidationError."""
        with pytest.raises(ValidationError, match="mutually exclusive"):
            parse_location_spec({
                "country": "USA",
                "state": "VA",
                "county": "059",
                "district_original": "11"
            })

    def test_district_original_and_current_raises_error(self):
        """Test that both district types together raises ValidationError."""
        with pytest.raises(ValidationError, match="mutually exclusive"):
            parse_location_spec({
                "country": "USA",
                "state": "VA",
                "district_original": "11",
                "district_current": "12"
            })

    def test_district_without_state_raises_error(self):
        """Test that district without state raises ValidationError."""
        with pytest.raises(ValidationError, match="district requires state"):
            parse_location_spec({
                "country": "USA",
                "district_original": "11"
            })

    def test_district_with_non_usa_country_raises_error(self):
        """Test that district with non-USA country raises ValidationError."""
        with pytest.raises(ValidationError, match="only valid for USA"):
            parse_location_spec({
                "country": "DEU",
                "state": "BY",
                "district_original": "11"
            })

    def test_key_mapping_country(self):
        """Test that 'country' maps to 'country_code'."""
        location = parse_location_spec({"country": "USA"})
        assert location.country_code == "USA"

    def test_key_mapping_state(self):
        """Test that 'state' maps to 'state_code'."""
        location = parse_location_spec({"country": "USA", "state": "CA"})
        assert location.state_code == "CA"

    def test_key_mapping_zip(self):
        """Test that 'zip' maps to 'zip_code'."""
        location = parse_location_spec({"country": "USA", "zip": "90210"})
        assert location.zip_code == "90210"

    def test_key_mapping_city(self):
        """Test that 'city' maps to 'city_name'."""
        location = parse_location_spec({"country": "USA", "city": "Portland"})
        assert location.city_name == "Portland"
