"""Tests for Location model."""

import json
import pytest
from pathlib import Path

from usaspending.models.location import Location


@pytest.fixture
def grant_data():
    """Load grant fixture data."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "grant.json"
    with open(fixture_path, "r") as f:
        return json.load(f)


@pytest.fixture
def recipient_location_data(grant_data):
    """Extract recipient location data from grant fixture."""
    return grant_data["recipient"]["location"]


@pytest.fixture
def place_of_performance_data(grant_data):
    """Extract place of performance data from grant fixture."""
    return grant_data["place_of_performance"]


@pytest.fixture
def recipient_location(recipient_location_data):
    """Create Location instance from recipient location data."""
    return Location(recipient_location_data)


@pytest.fixture
def place_of_performance_location(place_of_performance_data):
    """Create Location instance from place of performance data."""
    return Location(place_of_performance_data)


class TestLocationSimpleFields:
    """Test simple direct fields from Location model."""

    def test_address_fields(self, recipient_location):
        """Test address line fields."""
        assert recipient_location.address_line1 == "301 SPARKMAN DR NW"
        assert recipient_location.address_line2 is None
        assert recipient_location.address_line3 is None

    def test_city_fields(self, recipient_location):
        """Test city name and alias."""
        assert recipient_location.city_name == "HUNTSVILLE"
        assert recipient_location.city == "HUNTSVILLE"  # Test alias

    def test_state_name(self, recipient_location):
        """Test state name field."""
        assert recipient_location.state_name == "ALABAMA"

    def test_country_name(self, recipient_location):
        """Test country name field."""
        assert recipient_location.country_name == "UNITED STATES"

    def test_zip4(self, recipient_location):
        """Test zip4 field."""
        assert recipient_location.zip4 == "1911"

    def test_county_fields(self, recipient_location):
        """Test county name and code."""
        assert recipient_location.county_name == "MADISON"
        assert recipient_location.county_code == "089"

    def test_congressional_code(self, recipient_location):
        """Test congressional code field."""
        assert recipient_location.congressional_code == "05"

    def test_foreign_fields(self, recipient_location):
        """Test foreign province and postal code fields."""
        assert recipient_location.foreign_province is None
        assert recipient_location.foreign_postal_code is None


class TestLocationDualSourceFields:
    """Test dual-source fields that check multiple keys."""

    def test_state_code_from_standard_field(self, recipient_location):
        """Test state code from standard field."""
        assert recipient_location.state_code == "AL"

    def test_state_code_from_place_of_performance(self):
        """Test state code from Place of Performance field."""
        data = {"Place of Performance State Code": "CA"}
        location = Location(data)
        assert location.state_code == "CA"

    def test_state_code_priority(self):
        """Test that standard state_code takes priority."""
        data = {"state_code": "TX", "Place of Performance State Code": "CA"}
        location = Location(data)
        assert location.state_code == "TX"

    def test_country_code_from_location_country_code(self, recipient_location):
        """Test country code from location_country_code field."""
        assert recipient_location.country_code == "USA"

    def test_country_code_from_place_of_performance(self):
        """Test country code from Place of Performance field."""
        data = {"Place of Performance Country Code": "CAN"}
        location = Location(data)
        assert location.country_code == "CAN"

    def test_country_code_priority(self):
        """Test that location_country_code takes priority."""
        data = {
            "location_country_code": "MEX",
            "Place of Performance Country Code": "CAN",
        }
        location = Location(data)
        assert location.country_code == "MEX"

    def test_zip5_from_standard_field(self, recipient_location):
        """Test zip5 from standard field."""
        assert recipient_location.zip5 == "35805"

    def test_zip5_from_place_of_performance(self):
        """Test zip5 from Place of Performance field."""
        data = {"Place of Performance Zip5": "90210"}
        location = Location(data)
        assert location.zip5 == "90210"

    def test_zip5_numeric_conversion(self):
        """Test zip5 converts numeric values to string."""
        data = {"zip5": 12345}
        location = Location(data)
        assert location.zip5 == "12345"

    def test_zip5_none_returns_empty_string(self):
        """Test zip5 returns empty string when None."""
        data = {}
        location = Location(data)
        assert location.zip5 == ""


class TestLocationConvenienceMethods:
    """Test convenience methods for Location model."""

    def test_district_with_both_codes(self, recipient_location):
        """Test district formatting with state and congressional codes."""
        assert recipient_location.district == "AL-05"

    def test_district_with_only_state_code(self):
        """Test district with only state code."""
        data = {"state_code": "TX"}
        location = Location(data)
        assert location.district == "TX"

    def test_district_with_only_congressional_code(self):
        """Test district with only congressional code."""
        data = {"congressional_code": "10"}
        location = Location(data)
        assert location.district == "10"

    def test_district_empty(self):
        """Test district with no codes returns empty string."""
        data = {}
        location = Location(data)
        assert location.district == ""

    def test_formatted_address_full(self, recipient_location):
        """Test formatted address with all components."""
        expected = "301 SPARKMAN DR NW\nHUNTSVILLE, AL, 35805\nUNITED STATES"
        assert recipient_location.formatted_address == expected

    def test_formatted_address_minimal(self):
        """Test formatted address with minimal data."""
        data = {"address_line1": "123 Main St", "city_name": "Austin"}
        location = Location(data)
        assert location.formatted_address == "123 Main St\nAustin"

    def test_formatted_address_multiple_lines(self):
        """Test formatted address with multiple address lines."""
        data = {
            "address_line1": "123 Main St",
            "address_line2": "Suite 200",
            "address_line3": "Building A",
            "city_name": "Austin",
            "state_code": "TX",
            "zip5": "78701",
        }
        location = Location(data)
        expected = "123 Main St\nSuite 200\nBuilding A\nAustin, TX, 78701"
        assert location.formatted_address == expected

    def test_formatted_address_empty(self):
        """Test formatted address with no data returns None."""
        data = {}
        location = Location(data)
        assert location.formatted_address is None


class TestLocationRepr:
    """Test Location string representation."""

    def test_repr_with_all_fields(self, recipient_location):
        """Test repr with city, state, and country codes."""
        assert repr(recipient_location) == "<Location HUNTSVILLE AL USA>"

    def test_repr_with_missing_city(self):
        """Test repr with missing city shows placeholder."""
        data = {"state_code": "TX", "location_country_code": "USA"}
        location = Location(data)
        assert repr(location) == "<Location ? TX USA>"

    def test_repr_with_minimal_data(self):
        """Test repr with minimal data."""
        data = {}
        location = Location(data)
        assert repr(location) == "<Location ?  >"


class TestLocationWithPlaceOfPerformanceData:
    """Test Location model with actual Place of Performance data from fixture."""

    def test_place_of_performance_basic_fields(self, place_of_performance_location):
        """Test basic fields from place of performance data."""
        assert place_of_performance_location.city_name == "HUNTSVILLE"
        assert place_of_performance_location.state_name == "ALABAMA"
        assert place_of_performance_location.country_name == "UNITED STATES"
        assert place_of_performance_location.county_name == "MADISON"
        assert place_of_performance_location.county_code == "089"

    def test_place_of_performance_codes(self, place_of_performance_location):
        """Test code fields from place of performance data."""
        assert place_of_performance_location.state_code == "AL"
        assert place_of_performance_location.country_code == "USA"
        assert place_of_performance_location.congressional_code == "05"

    def test_place_of_performance_zip_fields(self, place_of_performance_location):
        """Test zip fields from place of performance data."""
        assert place_of_performance_location.zip5 == "35805"
        assert place_of_performance_location.zip4 == "1912"

    def test_place_of_performance_null_address_lines(
        self, place_of_performance_location
    ):
        """Test that null address lines are handled correctly."""
        assert place_of_performance_location.address_line1 is None
        assert place_of_performance_location.address_line2 is None
        assert place_of_performance_location.address_line3 is None

    def test_place_of_performance_formatted_address(
        self, place_of_performance_location
    ):
        """Test formatted address for place of performance location."""
        # Since address lines are null, formatted address should only have city/state/zip
        expected = "HUNTSVILLE, AL, 35805\nUNITED STATES"
        assert place_of_performance_location.formatted_address == expected


class TestLocationEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_data(self):
        """Test Location with empty data dictionary."""
        location = Location({})
        assert location.address_line1 is None
        assert location.city_name is None
        assert location.state_code is None
        assert location.zip5 == ""

    def test_none_data_handled_gracefully(self):
        """Test Location with None data is handled gracefully."""
        location = Location(None)
        # Should return None for all properties instead of raising error
        assert location.city_name is None
        assert location.address_line1 is None
        assert location.state_code is None
        assert location.zip5 == ""  # zip5 returns empty string when None

    def test_client_parameter_ignored(self):
        """Test that client parameter is properly ignored."""
        # Should not raise an error
        location = Location({"city_name": "Test City"}, client="dummy_client")
        assert location.city_name == "Test City"
