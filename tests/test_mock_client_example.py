"""Example tests demonstrating the new MockUSASpendingClient."""

from __future__ import annotations

import pytest

from usaspending.exceptions import APIError
from usaspending.models import Award
from tests.mocks.mock_client import MockUSASpendingClient


class TestMockClientExamples:
    """Examples showing how to use MockUSASpendingClient."""

    def test_simple_award_search(self, mock_usa_client):
        """Test a simple award search with mock data."""
        # Set up mock response
        mock_usa_client.mock_award_search(
            [
                {
                    "Award ID": "CONT_AWD_123",
                    "Recipient Name": "SpaceX",
                    "Award Amount": 1000000,
                },
                {
                    "Award ID": "CONT_AWD_456",
                    "Recipient Name": "Blue Origin",
                    "Award Amount": 2000000,
                },
            ]
        )

        # Execute search
        results = list(mock_usa_client.awards.search().with_award_types("A"))

        # Verify results
        assert len(results) == 2
        assert all(isinstance(r, Award) for r in results)
        assert results[0]._data["Award ID"] == "CONT_AWD_123"
        assert results[1]._data["Recipient Name"] == "Blue Origin"

    def test_paginated_response(self, mock_usa_client):
        """Test automatic pagination handling."""
        # Create 250 mock awards
        awards = [
            {"Award ID": f"AWD-{i}", "Recipient Name": f"Company {i}"}
            for i in range(250)
        ]

        # Set paginated response with 100 items per page
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH, awards, page_size=100
        )

        # Also mock the count endpoint since list() calls __len__ which calls count()
        mock_usa_client.mock_award_count(contracts=250)

        # Execute search and collect all results
        results = list(mock_usa_client.awards.search().with_award_types("A"))

        # Should have fetched all 250 items across 3 pages
        assert len(results) == 250
        assert (
            mock_usa_client.get_request_count(
                MockUSASpendingClient.Endpoints.AWARD_SEARCH
            )
            == 3
        )

    def test_error_simulation(self, mock_usa_client):
        """Test API error simulation."""
        # Set up error response for the count endpoint (since list() calls count() first)
        mock_usa_client.set_error_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            error_code=400,
            detail="Invalid award type code: X",
        )

        # Should raise APIError when calling count()
        with pytest.raises(APIError) as exc_info:
            list(mock_usa_client.awards.search().with_award_types("X"))

        assert exc_info.value.status_code == 400
        assert "Invalid award type code" in str(exc_info.value)

    def test_fixture_loading(self, mock_usa_client):
        """Test loading responses from fixture files."""
        award_id = "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        endpoint = MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(
            award_id=award_id
        )
        # Load award detail from fixture
        mock_usa_client.set_fixture_response(endpoint, "awards/contract")

        # Get award
        award = mock_usa_client.awards.find_by_generated_id(award_id)

        # Verify fixture data was loaded
        assert (
            award.generated_unique_award_id
            == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        )
        assert award.recipient.name == "The University of Iowa"

    def test_request_tracking(self, mock_usa_client):
        """Test request tracking and assertions."""
        mock_usa_client.mock_award_search([])

        # Make a search request
        list(
            mock_usa_client.awards.search()
            .with_award_types("A", "B")
            .with_keywords("space")
            .for_fiscal_year(2024)
        )

        # Verify request was made correctly
        last_request = mock_usa_client.get_last_request()
        assert last_request["method"] == "POST"
        assert last_request["endpoint"] == MockUSASpendingClient.Endpoints.AWARD_SEARCH

        # Check payload
        payload = last_request["json"]
        assert payload["filters"]["award_type_codes"] == ["A", "B"]
        assert payload["filters"]["keywords"] == ["space"]
        assert "time_period" in payload["filters"]

        # Use assert helper
        mock_usa_client.assert_called_with(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH, method="POST"
        )

    def test_award_count_mock(self, mock_usa_client):
        """Test mocking award count responses."""
        # Set up count response
        mock_usa_client.mock_award_count(contracts=150, grants=300, idvs=25, loans=10)

        # Test different award type counts
        assert mock_usa_client.awards.search().contracts().count() == 150
        assert mock_usa_client.awards.search().grants().count() == 300
        assert mock_usa_client.awards.search().idvs().count() == 25
        assert mock_usa_client.awards.search().loans().count() == 10

    def test_sequential_responses(self, mock_usa_client):
        """Test different responses for sequential calls."""
        # Add response sequence
        mock_usa_client.add_response_sequence(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            [
                # First call returns 2 results
                {
                    "results": [{"Award ID": "1"}, {"Award ID": "2"}],
                    "page_metadata": {"hasNext": False},
                },
                # Second call returns 1 result
                {"results": [{"Award ID": "3"}], "page_metadata": {"hasNext": False}},
                # Third call returns empty
                {"results": [], "page_metadata": {"hasNext": False}},
            ],
        )

        # Make three searches
        search = mock_usa_client.awards.search().with_award_types("A")

        results1 = list(search)
        assert len(results1) == 2

        results2 = list(search)
        assert len(results2) == 1

        results3 = list(search)
        assert len(results3) == 0

    def test_complex_scenario(self, mock_usa_client):
        """Test a complex scenario with multiple endpoints."""
        # Set up award search
        mock_usa_client.mock_award_search(
            [{"Award ID": "CONT_AWD_123", "Recipient Name": "SpaceX"}]
        )

        # Set up award detail
        mock_usa_client.mock_award_detail(
            "CONT_AWD_123",
            recipient_name="SpaceX",
            total_obligation=5000000000.0,
            awarding_agency="NASA",
        )

        # Set up transactions for the award
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.TRANSACTIONS,
            [
                {"transaction_id": "TXN-1", "amount": 1000000},
                {"transaction_id": "TXN-2", "amount": 2000000},
            ],
        )

        # Execute complex workflow
        # 1. Search for awards
        awards = list(mock_usa_client.awards.search().with_award_types("A"))
        assert len(awards) == 1

        # 2. Get award detail
        award = mock_usa_client.awards.find_by_generated_id("CONT_AWD_123")
        assert award.recipient.name == "SpaceX"
        assert award.total_obligation == 5000000000.0

        # 3. Get transactions (would need transaction implementation)
        # transactions = list(mock_usa_client.transactions.for_award("CONT_AWD_123"))
        # assert len(transactions) == 2

        # Verify all endpoints were called
        # Expected: search count + search + detail = 3 total requests
        assert mock_usa_client.get_request_count() == 3

    def test_reset_functionality(self, mock_usa_client):
        """Test resetting mock state between tests."""
        # Set up initial state
        mock_usa_client.mock_award_search([{"Award ID": "1"}])
        list(mock_usa_client.awards.search().with_award_types("A"))

        # Verify state
        # Expected: count + search = 2 total requests (list() calls both)
        assert mock_usa_client.get_request_count() == 2

        # Reset
        mock_usa_client.reset()

        # Verify clean state
        assert mock_usa_client.get_request_count() == 0

        # Should return empty results now (no mocks set)
        results = list(mock_usa_client.awards.search().with_award_types("A"))
        assert len(results) == 0
