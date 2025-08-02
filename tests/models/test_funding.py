"""Tests for Funding model."""

from __future__ import annotations

import pytest

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
        assert funding.transaction_obligated_amount == 20000.0
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

        assert funding.transaction_obligated_amount is None
        assert funding.gross_outlay_amount is None
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
        assert funding.transaction_obligated_amount == 20000.0
        assert funding.gross_outlay_amount == 31734.8
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

        assert (
            repr_str
            == "<Funding 2020-06 National Aeronautics and Space Administration $130,834.00>"
        )

    def test_funding_repr_with_missing_data(self):
        """Test string representation with missing data."""
        data = {}

        funding = Funding(data)
        repr_str = repr(funding)

        assert repr_str == "<Funding ?-? Unknown Agency ?>"

    def test_funding_repr_with_partial_data(self):
        """Test string representation with partial data."""
        data = {"reporting_fiscal_year": 2020, "transaction_obligated_amount": 50000.0}

        funding = Funding(data)
        repr_str = repr(funding)

        assert repr_str == "<Funding 2020-? Unknown Agency $50,000.00>"

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

        assert funding.transaction_obligated_amount == 20000.0
        assert funding.gross_outlay_amount is None
        assert funding.disaster_emergency_fund_code is None
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
            funding.awarding_agency_name
            == "National Aeronautics and Space Administration"
        )
        assert funding.awarding_agency_id == 862
        assert funding.awarding_toptier_agency_id == 72
        assert funding.object_class == "41.0"
        assert funding.object_class_name == "Grants, subsidies, and contributions"
        assert funding.program_activity_code == "0001"
        assert funding.program_activity_name == "SCIENCE (DIRECT)"
        assert funding.reporting_fiscal_year == 2018
        assert funding.reporting_fiscal_quarter == 2
        assert funding.reporting_fiscal_month == 6
        assert funding.is_quarterly_submission is True
        assert (
            funding.awarding_agency_slug
            == "national-aeronautics-and-space-administration"
        )
        assert (
            funding.funding_agency_slug
            == "national-aeronautics-and-space-administration"
        )
