"""Tests for FundingSearch query builder."""

from __future__ import annotations

import pytest

from usaspending.queries.funding_search import FundingSearch
from usaspending.models.funding import Funding
from usaspending.exceptions import ValidationError


class TestFundingSearch:
    """Test FundingSearch query builder functionality."""

    def test_funding_search_initialization(self, mock_usa_client):
        """Test basic FundingSearch initialization."""
        search = FundingSearch(mock_usa_client)

        assert search._client == mock_usa_client
        assert search._award_id is None
        assert search._sort_field == "reporting_fiscal_date"
        assert search._sort_order == "desc"
        assert search._endpoint == "/awards/funding/"

    def test_for_award_required(self, mock_usa_client):
        """Test that award_id is required before building payload."""
        search = FundingSearch(mock_usa_client)

        with pytest.raises(ValidationError, match="An award_id is required"):
            search._build_payload(1)

    def test_for_award_sets_award_id(self, mock_usa_client):
        """Test that for_award properly sets the award_id."""
        search = FundingSearch(mock_usa_client)

        result = search.for_award("CONT_AWD_123")

        assert result._award_id == "CONT_AWD_123"
        assert result is not search  # Should return a clone

    def test_for_award_strips_whitespace(self, mock_usa_client):
        """Test that for_award strips whitespace from award_id."""
        search = FundingSearch(mock_usa_client)

        result = search.for_award("  CONT_AWD_123  ")

        assert result._award_id == "CONT_AWD_123"

    def test_for_award_empty_raises_error(self, mock_usa_client):
        """Test that empty award_id raises ValidationError."""
        search = FundingSearch(mock_usa_client)

        with pytest.raises(ValidationError, match="award_id cannot be empty"):
            search.for_award("")

    def test_build_payload_default(self, mock_usa_client):
        """Test default payload construction."""
        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")

        payload = search._build_payload(1)

        assert payload == {
            "award_id": "CONT_AWD_123",
            "limit": 100,
            "page": 1,
            "sort": "reporting_fiscal_date",
            "order": "desc",
        }

    def test_build_payload_with_limit(self, mock_usa_client):
        """Test payload with custom limit."""
        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123").limit(25)

        payload = search._build_payload(1)

        assert payload["limit"] == 25

    def test_build_payload_with_page(self, mock_usa_client):
        """Test payload with different page numbers."""
        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")

        payload_page_1 = search._build_payload(1)
        payload_page_2 = search._build_payload(2)

        assert payload_page_1["page"] == 1
        assert payload_page_2["page"] == 2

    def test_order_by_valid_fields(self, mock_usa_client):
        """Test order_by with valid fields."""
        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")

        # Test user-friendly field names
        result = search.order_by("fiscal_date", "asc")
        assert result._sort_field == "reporting_fiscal_date"
        assert result._sort_order == "asc"

        result = search.order_by("obligated_amount", "desc")
        assert result._sort_field == "transaction_obligated_amount"
        assert result._sort_order == "desc"

        result = search.order_by("funding_agency")
        assert result._sort_field == "funding_agency_name"
        assert result._sort_order == "desc"  # Default

        # Test API field names directly
        result = search.order_by("gross_outlay_amount", "asc")
        assert result._sort_field == "gross_outlay_amount"
        assert result._sort_order == "asc"

    def test_order_by_all_mapped_fields(self, mock_usa_client):
        """Test all field mappings in SORT_FIELD_MAP."""
        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")

        field_mappings = {
            "account_title": "account_title",
            "awarding_agency": "awarding_agency_name",
            "disaster_code": "disaster_emergency_fund_code",
            "federal_account": "federal_account",
            "funding_agency": "funding_agency_name",
            "gross_outlay": "gross_outlay_amount",
            "object_class": "object_class",
            "program_activity": "program_activity",
            "reporting_date": "reporting_fiscal_date",
            "fiscal_date": "reporting_fiscal_date",
            "obligated_amount": "transaction_obligated_amount",
            "obligation": "transaction_obligated_amount",
        }

        for user_field, api_field in field_mappings.items():
            result = search.order_by(user_field)
            assert result._sort_field == api_field

    def test_order_by_invalid_direction(self, mock_usa_client):
        """Test order_by with invalid direction."""
        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")

        with pytest.raises(ValidationError, match="Invalid sort direction"):
            search.order_by("fiscal_date", "invalid")

    def test_order_by_invalid_field(self, mock_usa_client):
        """Test order_by with invalid field."""
        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")

        with pytest.raises(ValidationError, match="Invalid sort field"):
            search.order_by("invalid_field")

    def test_transform_result(self, mock_usa_client):
        """Test that _transform_result returns Funding model."""
        search = FundingSearch(mock_usa_client)

        data = {"transaction_obligated_amount": 20000.0, "funding_agency_name": "NASA"}

        result = search._transform_result(data)

        assert isinstance(result, Funding)
        assert result.transaction_obligated_amount == 20000.0
        assert result.funding_agency_name == "NASA"

    def test_clone_preserves_attributes(self, mock_usa_client):
        """Test that _clone preserves funding-specific attributes."""
        search = (
            FundingSearch(mock_usa_client)
            .for_award("CONT_AWD_123")
            .order_by("fiscal_date", "asc")
            .limit(50)
        )

        clone = search._clone()

        assert clone._award_id == "CONT_AWD_123"
        assert clone._sort_field == "reporting_fiscal_date"
        assert clone._sort_order == "asc"
        assert clone._total_limit == 50
        assert clone is not search

    def test_count_requires_award_id(self, mock_usa_client):
        """Test that count() requires award_id."""
        search = FundingSearch(mock_usa_client)

        with pytest.raises(ValidationError, match="An award_id is required"):
            search.count()

    def test_count_iterates_results(self, mock_usa_client, load_fixture):
        """Test that count() iterates through all results."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock to return all results from fixture
        mock_usa_client.set_paginated_response(
            "/awards/funding/", fixture_data["results"], page_size=100
        )

        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")
        count = search.count()

        # Should count all results from the fixture
        assert count == len(fixture_data["results"])

    def test_query_chaining(self, mock_usa_client):
        """Test that query methods can be chained."""
        search = (
            FundingSearch(mock_usa_client)
            .for_award("CONT_AWD_123")
            .order_by("fiscal_date", "asc")
            .limit(25)
            .page_size(10)
        )

        assert search._award_id == "CONT_AWD_123"
        assert search._sort_field == "reporting_fiscal_date"
        assert search._sort_order == "asc"
        assert search._total_limit == 25
        assert search._page_size == 10

    def test_iteration_with_fixture_data(self, mock_usa_client, load_fixture):
        """Test iteration through funding results."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock to return paginated fixture data
        # We need multiple responses because list() calls count() which consumes one response
        mock_usa_client.set_paginated_response(
            "/awards/funding/", fixture_data["results"], page_size=100
        )

        # Add another response for the actual iteration after count() consumes the first
        mock_usa_client.add_response_sequence(
            "/awards/funding/", [fixture_data], auto_count=False
        )

        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")
        results = list(search)

        assert len(results) == len(fixture_data["results"])

        # Check first result
        first_result = results[0]
        assert isinstance(first_result, Funding)
        assert first_result.transaction_obligated_amount == 20000.0
        assert (
            first_result.funding_agency_name
            == "National Aeronautics and Space Administration"
        )

    def test_first_returns_single_result(self, mock_usa_client, load_fixture):
        """Test that first() returns only the first result."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock to return fixture data
        mock_usa_client.set_response("/awards/funding/", fixture_data)

        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123")
        first = search.first()

        assert isinstance(first, Funding)
        assert first.transaction_obligated_amount == 20000.0

    def test_all_returns_list(self, mock_usa_client, load_fixture):
        """Test that all() returns a list of results."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock to return fixture data
        mock_usa_client.set_response("/awards/funding/", fixture_data)

        search = FundingSearch(mock_usa_client).for_award("CONT_AWD_123").limit(5)
        results = search.all()

        assert isinstance(results, list)
        assert len(results) == 5
        assert all(isinstance(r, Funding) for r in results)
