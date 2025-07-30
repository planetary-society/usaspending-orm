"""Tests for SpendingSearch count functionality."""

from __future__ import annotations

import pytest

from usaspending.queries.spending_search import SpendingSearch
from usaspending.exceptions import ValidationError


class TestSpendingSearchCount:
    """Test SpendingSearch count method."""
    
    def test_count_without_category_raises_error(self, mock_usa_client):
        """Test that count() raises error without category set."""
        search = SpendingSearch(mock_usa_client)
        
        with pytest.raises(ValidationError, match="Category must be set"):
            search.count()
    
    def test_count_with_single_page_results(self, mock_usa_client):
        """Test count with results that fit on a single page."""
        # Create district format test data
        district_fixture = {
            "category": "district",
            "spending_level": "transactions",
            "limit": 2,
            "page_metadata": {
                "page": 1,
                "hasNext": False,
                "hasPrevious": False
            },
            "results": [
                {
                    "id": None,
                    "name": "TX-12",
                    "code": "12",
                    "amount": 1777649549.5,
                    "total_outlays": None
                },
                {
                    "id": None,
                    "name": "MS-MULTIPLE DISTRICTS",
                    "code": "90",
                    "amount": 4223116662.42,
                    "total_outlays": None
                }
            ]
        }
        
        # Set up mock to return the district fixture data
        mock_usa_client.set_response("/api/v2/search/spending_by_category/district/", district_fixture)
        
        search = SpendingSearch(mock_usa_client).by_district()
        count = search.count()
        
        # The fixture has 2 results
        assert count == 2
        
        # Verify the API was called once (single page)
        assert mock_usa_client.get_request_count() == 1
    
    def test_count_with_multiple_pages(self, mock_usa_client):
        """Test count with results spanning multiple pages."""
        # Create responses for multiple pages
        page1_response = {
            "category": "recipient",
            "spending_level": "transactions",
            "limit": 2,
            "page_metadata": {
                "page": 1,
                "hasNext": True,
                "hasPrevious": False
            },
            "results": [
                {"id": 1, "name": "Recipient 1", "amount": 1000000.0},
                {"id": 2, "name": "Recipient 2", "amount": 2000000.0}
            ]
        }
        
        page2_response = {
            "category": "recipient",
            "spending_level": "transactions",
            "limit": 2,
            "page_metadata": {
                "page": 2,
                "hasNext": True,
                "hasPrevious": True
            },
            "results": [
                {"id": 3, "name": "Recipient 3", "amount": 3000000.0},
                {"id": 4, "name": "Recipient 4", "amount": 4000000.0}
            ]
        }
        
        page3_response = {
            "category": "recipient",
            "spending_level": "transactions",
            "limit": 2,
            "page_metadata": {
                "page": 3,
                "hasNext": False,
                "hasPrevious": True
            },
            "results": [
                {"id": 5, "name": "Recipient 5", "amount": 5000000.0}
            ]
        }
        
        # Set up mock to return different responses for each page
        mock_usa_client.add_response_sequence("/api/v2/search/spending_by_category/recipient/", [page1_response, page2_response, page3_response])
        
        search = SpendingSearch(mock_usa_client).by_recipient()
        count = search.count()
        
        # Total results: 2 + 2 + 1 = 5
        assert count == 5
        
        # Verify the API was called 3 times (three pages)
        assert mock_usa_client.get_request_count() == 3
    
    def test_count_with_no_results(self, mock_usa_client):
        """Test count when there are no results."""
        empty_response = {
            "category": "district",
            "spending_level": "awards",
            "limit": 100,
            "page_metadata": {
                "page": 1,
                "hasNext": False,
                "hasPrevious": False
            },
            "results": []
        }
        
        mock_usa_client.set_response("/api/v2/search/spending_by_category/district/", empty_response)
        
        search = SpendingSearch(mock_usa_client).by_district().spending_level("awards")
        count = search.count()
        
        assert count == 0
        assert mock_usa_client.get_request_count() == 1
    
    def test_count_consistency_with_iteration(self, mock_usa_client):
        """Test that count matches the number of items when iterating."""
        # Create district fixture data
        district_fixture = {
            "category": "district",
            "spending_level": "transactions",
            "limit": 2,
            "page_metadata": {
                "page": 1,
                "hasNext": False,
                "hasPrevious": False
            },
            "results": [
                {
                    "id": None,
                    "name": "TX-12",
                    "code": "12",
                    "amount": 1777649549.5,
                    "total_outlays": None
                },
                {
                    "id": None,
                    "name": "MS-MULTIPLE DISTRICTS",
                    "code": "90",
                    "amount": 4223116662.42,
                    "total_outlays": None
                }
            ]
        }
        
        # Set up mock to return the fixture data twice (once for count, once for iteration)
        mock_usa_client.add_response_sequence("/api/v2/search/spending_by_category/district/", [district_fixture, district_fixture])
        
        search = SpendingSearch(mock_usa_client).by_district()
        
        # Get count
        count_result = search.count()
        
        # Reset mock for iteration
        mock_usa_client.reset()
        mock_usa_client.set_response("/api/v2/search/spending_by_category/district/", district_fixture)
        
        # Iterate and count items
        items = list(search)
        
        # Count should match the number of items
        assert count_result == len(items)
        assert count_result == 2  # From fixture


class TestSpendingSearchCountWithLimits:
    """Test SpendingSearch count method with pagination limits."""
    
    def test_count_with_limit_smaller_than_results(self, mock_usa_client):
        """Test count respects limit when limit is smaller than total results."""
        # Create a response with more results than our limit
        response = {
            "category": "recipient",
            "spending_level": "transactions",
            "limit": 10,
            "page_metadata": {
                "page": 1,
                "hasNext": True,
                "hasPrevious": False
            },
            "results": [
                {"id": i, "name": f"Recipient {i}", "amount": 1000000.0 * i}
                for i in range(1, 11)  # 10 results
            ]
        }
        
        mock_usa_client.set_response("/api/v2/search/spending_by_category/recipient/", response)
        
        search = SpendingSearch(mock_usa_client).by_recipient().limit(5)
        count = search.count()
        
        # Should return only 5, not 10
        assert count == 5
        # Should only call API once since limit is reached
        assert mock_usa_client.get_request_count() == 1
    
    def test_count_with_limit_zero(self, mock_usa_client):
        """Test count with zero limit returns zero without API calls."""
        search = SpendingSearch(mock_usa_client).by_recipient().limit(0)
        count = search.count()
        
        assert count == 0
        # Should not make any API calls
        assert mock_usa_client.get_request_count() == 0
    
    def test_count_with_limit_larger_than_results(self, mock_usa_client):
        """Test count with limit larger than actual results."""
        response = {
            "category": "district",
            "spending_level": "awards",
            "limit": 10,
            "page_metadata": {
                "page": 1,
                "hasNext": False,
                "hasPrevious": False
            },
            "results": [
                {"id": i, "name": f"District-{i}", "amount": 500000.0 * i}
                for i in range(1, 4)  # Only 3 results
            ]
        }
        
        mock_usa_client.set_response("/api/v2/search/spending_by_category/district/", response)
        
        search = SpendingSearch(mock_usa_client).by_district().limit(10)
        count = search.count()
        
        # Should return actual count (3), not limit (10)
        assert count == 3
        assert mock_usa_client.get_request_count() == 1
    
    def test_count_with_max_pages_limit(self, mock_usa_client):
        """Test count respects max_pages limit."""
        # Create multiple pages of responses
        page1_response = {
            "category": "recipient",
            "spending_level": "transactions",
            "limit": 3,
            "page_metadata": {
                "page": 1,
                "hasNext": True,
                "hasPrevious": False
            },
            "results": [{"id": i, "name": f"Page1-Recipient{i}", "amount": 1000.0} for i in range(1, 4)]
        }
        
        page2_response = {
            "category": "recipient",
            "spending_level": "transactions",
            "limit": 3,
            "page_metadata": {
                "page": 2,
                "hasNext": True,
                "hasPrevious": True
            },
            "results": [{"id": i, "name": f"Page2-Recipient{i}", "amount": 1000.0} for i in range(4, 7)]
        }
        
        mock_usa_client.add_response_sequence("/api/v2/search/spending_by_category/recipient/", [page1_response, page2_response])
        
        search = SpendingSearch(mock_usa_client).by_recipient().max_pages(1)
        count = search.count()
        
        # Should only count first page (3 items)
        assert count == 3
        # Should only call API once due to max_pages
        assert mock_usa_client.get_request_count() == 1
    
    def test_count_consistency_with_iteration_limits(self, mock_usa_client):
        """Test that count() and len() return the same value with limits."""
        # Create response with multiple items
        response = {
            "category": "recipient",
            "spending_level": "transactions",
            "limit": 8,
            "page_metadata": {
                "page": 1,
                "hasNext": False,
                "hasPrevious": False
            },
            "results": [
                {"id": i, "name": f"Recipient {i}", "amount": 1000000.0 * i}
                for i in range(1, 9)  # 8 results
            ]
        }
        
        # Set up responses for both count and iteration
        mock_usa_client.add_response_sequence("/api/v2/search/spending_by_category/recipient/", [response, response])
        
        search = SpendingSearch(mock_usa_client).by_recipient().limit(5)
        
        # Get count first
        count_result = search.count()
        
        # Reset mock and get iteration count
        mock_usa_client.reset()
        mock_usa_client.set_response("/api/v2/search/spending_by_category/recipient/", response)
        
        items = list(search.limit(5))  # Create new search with same limit
        
        assert count_result == len(items) == 5