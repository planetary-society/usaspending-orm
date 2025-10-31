# tests/queries/test_filters.py

from __future__ import annotations

import datetime

# Assuming the filter classes are in this location
from usaspending.queries.filters import (
    AgencyFilter,
    AgencySpec,
    AgencyTier,
    AgencyType,
    AwardAmount,
    AwardAmountFilter,
    AwardDateType,
    KeywordsFilter,
    LocationSpec,
    LocationFilter,
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


def test_tiered_code_filter_for_naics():
    """
    Tests that TieredCodeFilter serializes correctly for NAICS codes.
    """
    # Arrange
    naics_filter = TieredCodeFilter(
        key="naics_codes",
        require=[["33"]],
        exclude=[["33", "336411"]],
    )
    expected_dict = {
        "naics_codes": {
            "require": [["33"]],
            "exclude": [["33", "336411"]],
        }
    }

    # Act
    result_dict = naics_filter.to_dict()

    # Assert
    assert result_dict == expected_dict


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
