"""Tests for DistrictSpending model functionality."""

from __future__ import annotations

import pytest
from decimal import Decimal

from usaspending.models.district_spending import DistrictSpending
from usaspending.models.spending import Spending


class TestDistrictSpendingInitialization:
    """Test DistrictSpending model initialization."""

    def test_init_with_dict_data(self, mock_usa_client):
        """Test DistrictSpending initialization with dictionary data."""
        data = {
            "id": None,
            "name": "TX-12",
            "code": "12",
            "amount": 1777649549.5,
            "total_outlays": None,
            "category": "district",
        }
        district_spending = DistrictSpending(data, mock_usa_client)

        assert district_spending._data["name"] == "TX-12"
        assert district_spending._data["code"] == "12"
        assert district_spending._client is not None
        assert isinstance(district_spending, DistrictSpending)
        assert isinstance(district_spending, Spending)  # Should inherit from Spending


class TestDistrictSpendingProperties:
    """Test district spending properties."""

    def test_district_specific_properties(self, mock_usa_client):
        """Test district-specific properties."""
        data = {"id": None, "name": "TX-12", "code": "12", "amount": 1777649549.5}
        district_spending = DistrictSpending(data, mock_usa_client)

        assert district_spending.district_code == "12"
        assert district_spending.state_code == "TX"
        assert district_spending.district_number == "12"
        assert not district_spending.is_multiple_districts

    def test_multiple_districts_property(self, mock_usa_client):
        """Test multiple districts parsing."""
        data = {"name": "MS-MULTIPLE DISTRICTS", "code": "90"}
        district_spending = DistrictSpending(data, mock_usa_client)

        assert district_spending.state_code == "MS"
        assert district_spending.district_number == "MULTIPLE DISTRICTS"
        assert district_spending.is_multiple_districts

    def test_properties_with_none_values(self, mock_usa_client):
        """Test properties when values are None."""
        data = {"name": None, "code": None}
        district_spending = DistrictSpending(data, mock_usa_client)

        assert district_spending.district_code is None
        assert district_spending.state_code is None
        assert district_spending.district_number is None
        assert not district_spending.is_multiple_districts

    def test_malformed_district_name(self, mock_usa_client):
        """Test handling of malformed district names."""
        data = {"name": "InvalidFormat", "code": "00"}
        district_spending = DistrictSpending(data, mock_usa_client)

        assert district_spending.state_code is None
        assert district_spending.district_number is None
        assert not district_spending.is_multiple_districts

    def test_repr(self, mock_usa_client):
        """Test string representation of DistrictSpending."""
        data = {"name": "TX-12", "amount": 1777649549.5}
        district_spending = DistrictSpending(data, mock_usa_client)

        repr_str = repr(district_spending)
        assert "TX-12" in repr_str
        assert "1,777,649,549.50" in repr_str
        assert "DistrictSpending" in repr_str

    def test_repr_with_none_values(self, mock_usa_client):
        """Test string representation with None values."""
        data = {}
        district_spending = DistrictSpending(data, mock_usa_client)

        repr_str = repr(district_spending)
        assert "Unknown District" in repr_str
        assert "0.00" in repr_str


class TestDistrictSpendingWithFixture:
    """Test DistrictSpending with real fixture data."""

    @pytest.fixture
    def district_fixture_data(self, load_fixture):
        """Load district spending fixture."""
        data = load_fixture("spending_by_district.json")
        return data["results"][0]  # First district: WA-09

    def test_district_spending_properties_from_fixture(self, district_fixture_data, mock_usa_client):
        """Test DistrictSpending properties match fixture data."""
        district = DistrictSpending(district_fixture_data, mock_usa_client)

        # Test base properties match fixture
        assert district.id == district_fixture_data.get("id")
        assert district.code == district_fixture_data["code"]
        assert district.name == district_fixture_data["name"]
        assert district.amount == Decimal(str(district_fixture_data["amount"]))
        assert district.total_outlays == district_fixture_data.get("total_outlays")

        # Test district-specific properties derived from fixture data
        assert district.district_code == district_fixture_data["code"]

        # Extract expected values from fixture name field
        expected_state = district_fixture_data["name"].split("-")[0] if "-" in district_fixture_data["name"] else None
        expected_district_num = district_fixture_data["name"].split("-")[1] if "-" in district_fixture_data["name"] else None

        assert district.state_code == expected_state
        assert district.district_number == expected_district_num
        assert not district.is_multiple_districts

    def test_district_spending_repr_from_fixture(self, district_fixture_data, mock_usa_client):
        """Test string representation with fixture data."""
        district = DistrictSpending(district_fixture_data, mock_usa_client)

        # Build expected repr from fixture data
        name = district_fixture_data["name"]
        amount = Decimal(str(district_fixture_data["amount"]))
        expected_repr = f"<DistrictSpending {name}: ${amount:,.2f}>"

        assert repr(district) == expected_repr
