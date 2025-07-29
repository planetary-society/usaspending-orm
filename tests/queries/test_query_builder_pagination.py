"""Tests for QueryBuilder pagination logic."""

from __future__ import annotations

import pytest
from usaspending.queries.awards_search import AwardsSearch



@pytest.fixture
def awards_search(mock_usa_client):
    """Create an AwardsSearch instance with a mock client."""
    return AwardsSearch(mock_usa_client).with_award_types("A")


class TestLimitFunctionality:
    """Test the limit() method properly limits total results."""
    
    def test_limit_stops_iteration_at_limit(self, awards_search, mock_usa_client):
        """Test that limit() stops iteration at the specified number of items."""
        # Mock 3 pages with 10 items each using add_response_sequence
        mock_usa_client.add_response_sequence(
            "/v2/search/spending_by_award/",
            [
                {
                    "results": [{"Award ID": f"{i}"} for i in range(10)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+10}"} for i in range(10)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+20}"} for i in range(10)],
                    "page_metadata": {"hasNext": False}
                }
            ]
        )
        
        # Request only 15 items
        search = awards_search.limit(15)
        results = list(search)
        
        assert len(results) == 15
        # Should have fetched 2 pages to get 15 items
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 2
    
    def test_limit_less_than_page_size(self, awards_search, mock_usa_client):
        """Test limit when it's less than a single page."""
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [{"Award ID": f"{i}"} for i in range(100)],
                "page_metadata": {"hasNext": True}
            }
        )
        
        # Request only 5 items
        search = awards_search.limit(5)
        results = list(search)
        
        assert len(results) == 5
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 1
    
    def test_limit_exact_page_boundary(self, awards_search, mock_usa_client):
        """Test limit that matches exactly with page boundaries."""
        mock_usa_client.add_response_sequence(
            "/v2/search/spending_by_award/",
            [
                {
                    "results": [{"Award ID": f"{i}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+100}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                }
            ]
        )
        
        # Request exactly 100 items (one full page)
        search = awards_search.limit(100)
        results = list(search)
        
        assert len(results) == 100
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 1
    
    def test_limit_with_smaller_page_size(self, awards_search, mock_usa_client):
        """Test limit with custom page size."""
        # Set page size to 20
        mock_usa_client.add_response_sequence(
            "/v2/search/spending_by_award/",
            [
                {
                    "results": [{"Award ID": f"{i}"} for i in range(20)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+20}"} for i in range(20)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+40}"} for i in range(20)],
                    "page_metadata": {"hasNext": True}
                }
            ]
        )
        
        # Request 50 items with page size of 20
        search = awards_search.page_size(20).limit(50)
        results = list(search)
        
        assert len(results) == 50
        # Should fetch 3 pages (20 + 20 + 10)
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 3
    
    def test_limit_zero_returns_empty(self, awards_search, mock_usa_client):
        """Test that limit(0) returns no results."""
        # Even if API has results, limit(0) should return nothing
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [{"Award ID": "1"}],
                "page_metadata": {"hasNext": True}
            }
        )
        
        search = awards_search.limit(0)
        results = list(search)
        
        assert len(results) == 0
        # Should not make any API calls
        assert mock_usa_client.get_request_count() == 0
    
    def test_no_limit_fetches_all(self, awards_search, mock_usa_client):
        """Test that no limit fetches all available results."""
        mock_usa_client.add_response_sequence(
            "/v2/search/spending_by_award/",
            [
                {
                    "results": [{"Award ID": f"{i}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+100}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+200}"} for i in range(50)],
                    "page_metadata": {"hasNext": False}
                }
            ]
        )
        
        # No limit() call - should fetch all results
        results = list(awards_search)
        
        assert len(results) == 250
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 3


class TestMaxPagesWithLimit:
    """Test interaction between max_pages and limit."""
    
    def test_limit_takes_precedence_over_max_pages(self, awards_search, mock_usa_client):
        """Test that limit stops iteration even if max_pages would allow more."""
        mock_usa_client.add_response_sequence(
            "/v2/search/spending_by_award/",
            [
                {
                    "results": [{"Award ID": f"{i}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+100}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+200}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                }
            ]
        )
        
        # Allow 3 pages but limit to 150 items
        search = awards_search.max_pages(3).limit(150)
        results = list(search)
        
        assert len(results) == 150
        # Should stop after 2 pages (100 + 50)
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 2
    
    def test_max_pages_stops_before_limit(self, awards_search, mock_usa_client):
        """Test that max_pages can stop iteration before limit is reached."""
        mock_usa_client.add_response_sequence(
            "/v2/search/spending_by_award/",
            [
                {
                    "results": [{"Award ID": f"{i}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [{"Award ID": f"{i+100}"} for i in range(100)],
                    "page_metadata": {"hasNext": True}
                }
            ]
        )
        
        # Limit to 300 items but only allow 2 pages
        search = awards_search.limit(300).max_pages(2)
        results = list(search)
        
        assert len(results) == 200  # 2 pages * 100 items
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 2


class TestFirstMethodWithLimit:
    """Test first() method behavior."""
    
    def test_first_uses_limit_one(self, awards_search, mock_usa_client):
        """Test that first() effectively sets limit to 1."""
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [
                    {"Award ID": "1"},
                    {"Award ID": "2"},
                    {"Award ID": "3"}
                ],
                "page_metadata": {"hasNext": True}
            }
        )
        
        result = awards_search.first()
        
        assert result is not None
        assert result._data["Award ID"] == "1"
        # Should only iterate once
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 1
    
    def test_first_with_existing_limit(self, awards_search, mock_usa_client):
        """Test that first() overrides any existing limit."""
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [{"Award ID": "1"}],
                "page_metadata": {"hasNext": True}
            }
        )
        
        # Set a higher limit, but first() should still return only one
        result = awards_search.limit(100).first()
        
        assert result is not None
        assert result._data["Award ID"] == "1"


class TestPageSizeFunctionality:
    """Test the page_size() method."""
    
    def test_page_size_changes_request_limit(self, awards_search, mock_usa_client):
        """Test that page_size affects the API request limit parameter."""
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [],
                "page_metadata": {"hasNext": False}
            }
        )
        
        search = awards_search.page_size(50)
        list(search)
        
        # Check that the payload had limit=50
        last_request = mock_usa_client.get_last_request("/v2/search/spending_by_award/")
        payload = last_request["json"]
        assert payload["limit"] == 50
    
    def test_page_size_capped_at_100(self, awards_search, mock_usa_client):
        """Test that page_size is capped at API maximum of 100."""
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [],
                "page_metadata": {"hasNext": False}
            }
        )
        
        search = awards_search.page_size(200)  # Try to set above max
        list(search)
        
        # Check that the payload had limit=100 (capped)
        last_request = mock_usa_client.get_last_request("/v2/search/spending_by_award/")
        payload = last_request["json"]
        assert payload["limit"] == 100
    
    def test_effective_page_size_uses_smaller_of_limit_and_page_size(self, awards_search, mock_usa_client):
        """Test that effective page size is min(page_size, total_limit)."""
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [],
                "page_metadata": {"hasNext": False}
            }
        )
        
        # Case 1: limit(10) with default page_size(100)
        search1 = awards_search.limit(10)
        list(search1)
        
        last_request1 = mock_usa_client.get_last_request("/v2/search/spending_by_award/")
        payload1 = last_request1["json"]
        assert payload1["limit"] == 10  # Should use limit, not page_size
        
        mock_usa_client.reset()
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [],
                "page_metadata": {"hasNext": False}
            }
        )
        
        # Case 2: limit(150) with default page_size(100)
        search2 = awards_search.limit(150)
        list(search2)
        
        last_request2 = mock_usa_client.get_last_request("/v2/search/spending_by_award/")
        payload2 = last_request2["json"]
        assert payload2["limit"] == 100  # Should use page_size, not limit
        
        mock_usa_client.reset()
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [],
                "page_metadata": {"hasNext": False}
            }
        )
        
        # Case 3: limit(30) with page_size(50)
        search3 = awards_search.limit(30).page_size(50)
        list(search3)
        
        last_request3 = mock_usa_client.get_last_request("/v2/search/spending_by_award/")
        payload3 = last_request3["json"]
        assert payload3["limit"] == 30  # Should use limit, not page_size


class TestEmptyResults:
    """Test handling of empty results."""
    
    def test_empty_first_page(self, awards_search, mock_usa_client):
        """Test handling when first page returns no results."""
        mock_usa_client.set_response(
            "/v2/search/spending_by_award/",
            {
                "results": [],
                "page_metadata": {"hasNext": False}
            }
        )
        
        results = list(awards_search.limit(10))
        
        assert len(results) == 0
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 1
    
    def test_empty_page_stops_iteration(self, awards_search, mock_usa_client):
        """Test that an empty page stops iteration even if hasNext is True."""
        mock_usa_client.add_response_sequence(
            "/v2/search/spending_by_award/",
            [
                {
                    "results": [{"Award ID": "1"}],
                    "page_metadata": {"hasNext": True}
                },
                {
                    "results": [],  # Empty second page
                    "page_metadata": {"hasNext": True}
                }
            ]
        )
        
        results = list(awards_search)
        
        assert len(results) == 1
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 2