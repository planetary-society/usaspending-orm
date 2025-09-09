"""Tests for Funding model."""

from __future__ import annotations

from tests.utils import assert_decimal_equal
from usaspending.models.funding import Funding


class TestFundingModel:
    """Test Funding model functionality."""

    def test_funding_initialization(self):
        """Test basic funding initialization."""
        data = {
            "transaction_obligated_amount": 20000.0,
            "gross_outlay_amount": 15000.0,
            "federal_account": "080-0120",
            "funding_agency_name": "National Aeronautics and Space Administration",
        }

        funding = Funding(data)

        assert funding.raw == data
        assert_decimal_equal(funding.transaction_obligated_amount, 20000.0)
        assert funding.gross_outlay_amount == 15000.0
        assert funding.federal_account == "080-0120"
        assert (
            funding.funding_agency_name
            == "National Aeronautics and Space Administration"
        )

    def test_funding_numeric_conversions(self):
        """Test that numeric fields are properly converted."""
        data = {
            "transaction_obligated_amount": "20000.50",
            "gross_outlay_amount": "15000.25",
            "funding_agency_id": "862",
            "funding_toptier_agency_id": "72",
            "awarding_agency_id": "862",
            "awarding_toptier_agency_id": "72",
            "reporting_fiscal_year": "2020",
            "reporting_fiscal_quarter": "2",
            "reporting_fiscal_month": "6",
        }

        funding = Funding(data)

        # Float conversions
        assert funding.transaction_obligated_amount == 20000.50
        assert funding.gross_outlay_amount == 15000.25

        # Integer conversions
        assert funding.funding_agency_id == 862
        assert funding.funding_toptier_agency_id == 72
        assert funding.awarding_agency_id == 862
        assert funding.awarding_toptier_agency_id == 72
        assert funding.reporting_fiscal_year == 2020
        assert funding.reporting_fiscal_quarter == 2
        assert funding.reporting_fiscal_month == 6

    def test_funding_null_handling(self):
        """Test that null/None values are handled properly."""
        data = {
            "transaction_obligated_amount": None,
            "gross_outlay_amount": None,
            "disaster_emergency_fund_code": None,
            "funding_agency_id": None,
            "reporting_fiscal_year": None,
            "is_quarterly_submission": None,
        }

        funding = Funding(data)

        assert funding.transaction_obligated_amount == 0.0
        assert funding.gross_outlay_amount == 0.0
        assert funding.disaster_emergency_fund_code is None
        assert funding.funding_agency_id is None
        assert funding.reporting_fiscal_year is None
        assert funding.is_quarterly_submission is None

    def test_funding_all_properties(self):
        """Test all funding properties with complete data."""
        data = {
            "transaction_obligated_amount": 20000.0,
            "gross_outlay_amount": 31734.8,
            "disaster_emergency_fund_code": "Q",
            "federal_account": "080-0120",
            "account_title": "Science, National Aeronautics and Space Administration",
            "funding_agency_name": "National Aeronautics and Space Administration",
            "funding_agency_id": 862,
            "funding_toptier_agency_id": 72,
            "funding_agency_slug": "national-aeronautics-and-space-administration",
            "awarding_agency_name": "National Aeronautics and Space Administration",
            "awarding_agency_id": 862,
            "awarding_toptier_agency_id": 72,
            "awarding_agency_slug": "national-aeronautics-and-space-administration",
            "object_class": "41.0",
            "object_class_name": "Grants, subsidies, and contributions",
            "program_activity_code": "0001",
            "program_activity_name": "SCIENCE (DIRECT)",
            "reporting_fiscal_year": 2020,
            "reporting_fiscal_quarter": 3,
            "reporting_fiscal_month": 9,
            "is_quarterly_submission": False,
        }

        funding = Funding(data)

        # Test all properties
        assert_decimal_equal(funding.transaction_obligated_amount, 20000.0)
        assert_decimal_equal(funding.gross_outlay_amount, 31734.8)
        assert funding.disaster_emergency_fund_code == "Q"
        assert funding.federal_account == "080-0120"
        assert (
            funding.account_title
            == "Science, National Aeronautics and Space Administration"
        )
        assert (
            funding.funding_agency_name
            == "National Aeronautics and Space Administration"
        )
        assert funding.funding_agency_id == 862
        assert funding.funding_toptier_agency_id == 72
        assert (
            funding.funding_agency_slug
            == "national-aeronautics-and-space-administration"
        )
        assert (
            funding.awarding_agency_name
            == "National Aeronautics and Space Administration"
        )
        assert funding.awarding_agency_id == 862
        assert funding.awarding_toptier_agency_id == 72
        assert (
            funding.awarding_agency_slug
            == "national-aeronautics-and-space-administration"
        )
        assert funding.object_class == "41.0"
        assert funding.object_class_name == "Grants, subsidies, and contributions"
        assert funding.program_activity_code == "0001"
        assert funding.program_activity_name == "SCIENCE (DIRECT)"
        assert funding.reporting_fiscal_year == 2020
        assert funding.reporting_fiscal_quarter == 3
        assert funding.reporting_fiscal_month == 9
        assert funding.is_quarterly_submission is False

    def test_funding_repr_with_complete_data(self):
        """Test string representation with complete data."""
        data = {
            "reporting_fiscal_year": 2020,
            "reporting_fiscal_month": 6,
            "transaction_obligated_amount": 130834.0,
            "funding_agency_name": "National Aeronautics and Space Administration",
        }

        funding = Funding(data)
        repr_str = repr(funding)

        assert "2020" in repr_str
        assert "06" in repr_str
        assert "130,834" in repr_str

    def test_funding_repr_with_missing_data(self):
        """Test string representation with missing data."""
        data = {}

        funding = Funding(data)

        try:
            repr(funding)
        except Exception as e:
            assert False, f"Repr with missing data failed with exception: {e}"

    def test_funding_repr_with_partial_data(self):
        """Test string representation with partial data."""
        data = {"reporting_fiscal_year": 2020, "transaction_obligated_amount": 50000.0}

        funding = Funding(data)
        repr_str = repr(funding)

        assert "Unknown Agency" in repr_str
        assert "2020-?" in repr_str

    def test_funding_boolean_field(self):
        """Test boolean field handling."""
        # Test True value
        funding_quarterly = Funding({"is_quarterly_submission": True})
        assert funding_quarterly.is_quarterly_submission is True

        # Test False value
        funding_monthly = Funding({"is_quarterly_submission": False})
        assert funding_monthly.is_quarterly_submission is False

        # Test missing value
        funding_missing = Funding({})
        assert funding_missing.is_quarterly_submission is None

    def test_funding_from_fixture_data(self, load_fixture):
        """Test funding model with real fixture data."""
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Test first result
        first_result = fixture_data["results"][0]
        funding = Funding(first_result)

        expected_transaction_obligated = first_result.get(
            "transaction_obligated_amount"
        )
        assert funding.transaction_obligated_amount == (
            expected_transaction_obligated
            if expected_transaction_obligated is not None
            else 0.0
        )
        expected_gross_outlay = first_result.get("gross_outlay_amount")
        assert funding.gross_outlay_amount == (
            expected_gross_outlay if expected_gross_outlay is not None else 0.0
        )
        assert funding.disaster_emergency_fund_code == first_result.get(
            "disaster_emergency_fund_code"
        )
        assert funding.federal_account == first_result.get("federal_account")
        assert funding.account_title == first_result.get("account_title")
        assert funding.funding_agency_name == first_result.get("funding_agency_name")
        assert funding.funding_agency_id == first_result.get("funding_agency_id")
        assert funding.funding_toptier_agency_id == first_result.get(
            "funding_toptier_agency_id"
        )
        assert funding.awarding_agency_name == first_result.get("awarding_agency_name")
        assert funding.awarding_agency_id == first_result.get("awarding_agency_id")
        assert funding.awarding_toptier_agency_id == first_result.get(
            "awarding_toptier_agency_id"
        )
        assert funding.object_class == first_result.get("object_class")
        assert funding.object_class_name == first_result.get("object_class_name")
        assert funding.program_activity_code == first_result.get(
            "program_activity_code"
        )
        assert funding.program_activity_name == first_result.get(
            "program_activity_name"
        )
        assert funding.reporting_fiscal_year == first_result.get(
            "reporting_fiscal_year"
        )
        assert funding.reporting_fiscal_quarter == first_result.get(
            "reporting_fiscal_quarter"
        )
        assert funding.reporting_fiscal_month == first_result.get(
            "reporting_fiscal_month"
        )
        assert funding.is_quarterly_submission is first_result.get(
            "is_quarterly_submission"
        )
        assert funding.awarding_agency_slug == first_result.get("awarding_agency_slug")
        assert funding.funding_agency_slug == first_result.get("funding_agency_slug")
