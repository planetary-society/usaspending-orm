"""Tests for Location model."""

import pytest

from usaspending.models.location import Location


def assert_text_matches(actual, raw):
    """Compare a formatted location string with its recorded source text."""
    if raw is None:
        assert actual is None
    else:
        assert actual
        assert actual.casefold() == raw.strip().casefold()


@pytest.fixture
def grant_data(load_fixture):
    """Load grant fixture data."""
    return load_fixture("awards/grant.json")


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

    def test_address_fields(self, recipient_location, recipient_location_data):
        """Test address line fields."""
        for field in ("address_line1", "address_line2", "address_line3"):
            assert_text_matches(getattr(recipient_location, field), recipient_location_data[field])

    def test_city_fields(self, recipient_location, recipient_location_data):
        """Test city name and alias."""
        assert_text_matches(recipient_location.city, recipient_location_data["city_name"])
        assert recipient_location.city == recipient_location.city_name

    def test_state_name(self, recipient_location, recipient_location_data):
        """Test state name field."""
        assert_text_matches(recipient_location.state_name, recipient_location_data["state_name"])

    def test_state_name_none(self):
        """Test state name returns None when value is None."""
        location = Location({"state_name": None})
        assert location.state_name is None

    def test_country_name(self, recipient_location, recipient_location_data):
        """Test country name field."""
        assert_text_matches(
            recipient_location.country_name, recipient_location_data["country_name"]
        )

    def test_zip4(self, recipient_location, recipient_location_data):
        """Test zip4 field."""
        assert recipient_location.zip4 == recipient_location_data["zip4"]

    def test_county_fields(self, recipient_location, recipient_location_data):
        """Test county name and code."""
        assert_text_matches(recipient_location.county_name, recipient_location_data["county_name"])
        assert recipient_location.county_code == recipient_location_data["county_code"]

    def test_county_name_none(self):
        """Test county name returns None when value is None."""
        location = Location({"county_name": None})
        assert location.county_name is None

    def test_congressional_code(self, recipient_location, recipient_location_data):
        """Test congressional code field."""
        assert (
            recipient_location.congressional_code == recipient_location_data["congressional_code"]
        )

    def test_foreign_fields(self, recipient_location, recipient_location_data):
        """Test foreign province and postal code fields."""
        assert recipient_location.foreign_province == recipient_location_data["foreign_province"]
        assert (
            recipient_location.foreign_postal_code == recipient_location_data["foreign_postal_code"]
        )


class TestLocationDualSourceFields:
    """Test dual-source fields that check multiple keys."""

    def test_state_code_from_standard_field(self, recipient_location, recipient_location_data):
        """Test state code from standard field."""
        assert recipient_location.state_code == recipient_location_data["state_code"]

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

    def test_country_code_from_location_country_code(
        self, recipient_location, recipient_location_data
    ):
        """Test country code from location_country_code field."""
        assert recipient_location.country_code == recipient_location_data["location_country_code"]

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

    def test_zip5_from_standard_field(self, recipient_location, recipient_location_data):
        """Test zip5 from standard field."""
        assert recipient_location.zip5 == str(recipient_location_data["zip5"])

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

    def test_zip5_absent_returns_none(self):
        """An absent ZIP is None, matching the declared Optional[str]."""
        location = Location({})
        assert location.zip5 is None


class TestLocationConvenienceMethods:
    """Test convenience methods for Location model."""

    def test_district_with_both_codes(self, recipient_location):
        """Test district formatting with state and congressional codes."""
        expected = f"{recipient_location.state_code}-{recipient_location.congressional_code}"
        assert recipient_location.district == expected

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
        """With neither state nor district code, district is None."""
        location = Location({})
        assert location.district is None

    def test_formatted_address_full(self, recipient_location):
        """Test formatted address with all components."""
        expected = "\n".join(
            [
                recipient_location.address_line1,
                ", ".join(
                    [
                        recipient_location.city,
                        recipient_location.state_code,
                        recipient_location.zip5,
                    ]
                ),
                recipient_location.country_name,
            ]
        )
        assert recipient_location.formatted_address == expected

    def test_formatted_address_minimal(self):
        """Test formatted address with minimal data."""
        data = {"address_line1": "123 Main St", "city": "Austin"}
        location = Location(data)
        assert location.formatted_address == "123 Main St\nAustin"

    def test_formatted_address_multiple_lines(self):
        """Test formatted address with multiple address lines."""
        data = {
            "address_line1": "123 Main St",
            "address_line2": "Suite 200",
            "address_line3": "Building A",
            "city": "Austin",
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
        expected = (
            f"<Location {recipient_location.city} {recipient_location.state_code} "
            f"{recipient_location.country_code}>"
        )
        assert repr(recipient_location) == expected

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

    def test_place_of_performance_basic_fields(
        self, place_of_performance_location, place_of_performance_data
    ):
        """Test basic fields from place of performance data."""
        for prop, raw_key in (
            ("city", "city_name"),
            ("state_name", "state_name"),
            ("country_name", "country_name"),
            ("county_name", "county_name"),
        ):
            assert_text_matches(
                getattr(place_of_performance_location, prop), place_of_performance_data[raw_key]
            )
        assert place_of_performance_location.county_code == place_of_performance_data["county_code"]

    def test_place_of_performance_codes(
        self, place_of_performance_location, place_of_performance_data
    ):
        """Test code fields from place of performance data."""
        assert place_of_performance_location.state_code == place_of_performance_data["state_code"]
        assert (
            place_of_performance_location.country_code
            == place_of_performance_data["location_country_code"]
        )
        assert (
            place_of_performance_location.congressional_code
            == place_of_performance_data["congressional_code"]
        )

    def test_place_of_performance_zip_fields(
        self, place_of_performance_location, place_of_performance_data
    ):
        """Test zip fields from place of performance data."""
        assert place_of_performance_location.zip5 == str(place_of_performance_data["zip5"])
        assert place_of_performance_location.zip4 == place_of_performance_data["zip4"]

    def test_place_of_performance_null_address_lines(
        self, place_of_performance_location, place_of_performance_data
    ):
        """Test that null address lines are handled correctly."""
        for field in ("address_line1", "address_line2", "address_line3"):
            assert getattr(place_of_performance_location, field) == place_of_performance_data[field]

    def test_place_of_performance_formatted_address(self, place_of_performance_location):
        """Test formatted address for place of performance location."""
        expected = "\n".join(
            [
                ", ".join(
                    [
                        place_of_performance_location.city,
                        place_of_performance_location.state_code,
                        place_of_performance_location.zip5,
                    ]
                ),
                place_of_performance_location.country_name,
            ]
        )
        assert place_of_performance_location.formatted_address == expected


class TestLocationEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_data(self):
        """Test Location with empty data dictionary."""
        location = Location({})
        assert location.address_line1 is None
        assert location.city is None
        assert location.state_code is None
        assert location.zip5 is None

    def test_none_data_handled_gracefully(self):
        """Test Location with None data is handled gracefully."""
        location = Location(None)
        # Should return None for all properties instead of raising error
        assert location.city is None
        assert location.address_line1 is None
        assert location.state_code is None
        assert location.zip5 is None
