"""Integration tests for funding functionality."""

from __future__ import annotations


from usaspending.models.funding import Funding
from usaspending.models.award import Award


class TestClientFunding:
    """Test funding functionality through the USASpending client."""

    def test_client_has_funding_resource(self, mock_usa_client):
        """Test that client has funding resource property."""
        assert hasattr(mock_usa_client, "funding")
        assert mock_usa_client.funding.__class__.__name__ == "FundingResource"

    def test_funding_for_award_query_builder(self, mock_usa_client):
        """Test creating funding query through client."""
        query = mock_usa_client.funding.for_award("CONT_AWD_123")

        assert query.__class__.__name__ == "FundingSearch"
        assert query._award_id == "CONT_AWD_123"

    def test_funding_full_query_chain(self, mock_usa_client, load_fixture):
        """Test full query chain with fixture data."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock to return fixture data
        mock_usa_client.set_response("/v2/awards/funding/", fixture_data)

        # Execute query
        results = (
            mock_usa_client.funding.for_award("CONT_AWD_123")
            .order_by("fiscal_date", "asc")
            .limit(5)
            .all()
        )

        assert len(results) == 5
        assert all(isinstance(r, Funding) for r in results)

        # Check that results are properly sorted (fixture should be in date order)
        first = results[0]
        assert first.reporting_fiscal_year == 2018
        assert first.reporting_fiscal_month == 6

    def test_award_funding_property(self, mock_usa_client, load_fixture):
        """Test accessing funding through Award model."""
        # Create an award
        award_data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "description": "Test Award",
        }
        award = Award(award_data, mock_usa_client)

        # Access funding property
        funding_query = award.funding

        assert funding_query.__class__.__name__ == "FundingSearch"
        assert funding_query._award_id == "CONT_AWD_123"

    def test_award_funding_iteration(self, mock_usa_client, load_fixture):
        """Test iterating funding through Award model."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock to return fixture data
        mock_usa_client.set_response("/v2/awards/funding/", fixture_data)

        # Create award and iterate funding
        award = Award({"generated_unique_award_id": "CONT_AWD_123"}, mock_usa_client)

        funding_list = list(award.funding.limit(3))

        assert len(funding_list) == 3
        assert all(isinstance(f, Funding) for f in funding_list)
        assert funding_list[0].transaction_obligated_amount == 20000.0

    def test_funding_count_through_award(self, mock_usa_client, load_fixture):
        """Test counting funding records through Award model."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock for count operation (which iterates all results)
        mock_usa_client.set_paginated_response(
            "/v2/awards/funding/", fixture_data["results"], page_size=100
        )

        # Create award and count funding
        award = Award({"generated_unique_award_id": "CONT_AWD_123"}, mock_usa_client)

        count = award.funding.count()

        assert count == len(fixture_data["results"])

    def test_funding_sorting_options(self, mock_usa_client, load_fixture):
        """Test various sorting options for funding."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock
        mock_usa_client.set_response("/v2/awards/funding/", fixture_data)

        # Test sorting by obligated amount
        query = mock_usa_client.funding.for_award("CONT_AWD_123").order_by(
            "obligated_amount", "desc"
        )

        # Check that the query is properly configured
        assert query._sort_field == "transaction_obligated_amount"
        assert query._sort_order == "desc"

        # Execute query
        results = query.limit(1).all()
        assert len(results) == 1
        assert isinstance(results[0], Funding)

    def test_funding_pagination(self, mock_usa_client, load_fixture):
        """Test pagination of funding results."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock to return paginated results
        # We need enough responses for both count() and the actual iteration
        # First, set up responses for the count operation
        mock_usa_client.set_paginated_response(
            "/v2/awards/funding/", fixture_data["results"], page_size=5
        )

        # Then add responses for the actual all() iteration
        mock_usa_client.add_response_sequence(
            "/v2/awards/funding/",
            [
                {
                    "results": fixture_data["results"][:5],
                    "page_metadata": {"page": 1, "hasNext": True},
                },
                {
                    "results": fixture_data["results"][5:],
                    "page_metadata": {"page": 2, "hasNext": False},
                },
            ],
            auto_count=False,
        )

        # Get all results with small page size
        results = mock_usa_client.funding.for_award("CONT_AWD_123").page_size(5).all()

        # Should get all results across both pages
        assert len(results) == len(fixture_data["results"])

        # Verify first and last results
        assert results[0].transaction_obligated_amount == 20000.0
        assert results[-1].gross_outlay_amount == 39077.94

    def test_funding_first_method(self, mock_usa_client, load_fixture):
        """Test getting first funding record."""
        # Load fixture data
        fixture_data = load_fixture("awards/award_funding_grant.json")

        # Set up mock
        mock_usa_client.set_response("/v2/awards/funding/", fixture_data)

        # Get first result
        first = (
            mock_usa_client.funding.for_award("CONT_AWD_123")
            .order_by("fiscal_date", "asc")
            .first()
        )

        assert isinstance(first, Funding)
        assert first.reporting_fiscal_year == 2018
        assert first.reporting_fiscal_month == 6
        assert first.transaction_obligated_amount == 20000.0

    def test_funding_empty_results(self, mock_usa_client):
        """Test handling of empty funding results."""
        # Set up mock to return empty results
        empty_response = {
            "results": [],
            "page_metadata": {"page": 1, "hasNext": False, "hasPrevious": False},
        }

        mock_usa_client.set_response("/v2/awards/funding/", empty_response)

        # Query should return empty list
        results = mock_usa_client.funding.for_award("CONT_AWD_123").all()

        assert results == []

        # First should return None
        first = mock_usa_client.funding.for_award("CONT_AWD_123").first()
        assert first is None

        # Count should return 0
        mock_usa_client.set_response("/v2/awards/funding/", empty_response)
        count = mock_usa_client.funding.for_award("CONT_AWD_123").count()
        assert count == 0
