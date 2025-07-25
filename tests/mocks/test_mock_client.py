"""Tests for the MockUSASpendingClient itself."""

from __future__ import annotations

import pytest

from usaspending.exceptions import APIError, HTTPError
from tests.mocks import MockUSASpendingClient, ResponseBuilder


class TestMockUSASpendingClient:
    """Test the mock client implementation."""
    
    def test_initialization(self):
        """Test mock client initializes correctly."""
        client = MockUSASpendingClient()
        assert client is not None
        assert isinstance(client, MockUSASpendingClient)

    def test_default_empty_response(self):
        """Test that unmocked endpoints return empty results."""
        client = MockUSASpendingClient()
        
        response = client._make_request("GET", "/test/endpoint")
        
        assert response["results"] == []
        assert response["page_metadata"]["hasNext"] is False
    
    def test_set_single_response(self):
        """Test setting a single response."""
        client = MockUSASpendingClient()
        
        test_response = {"results": [{"id": 1}], "page_metadata": {"hasNext": False}}
        client.set_response("/test/endpoint", test_response)
        
        # Should return the response every time
        assert client._make_request("GET", "/test/endpoint") == test_response
        assert client._make_request("GET", "/test/endpoint") == test_response
    
    def test_set_error_response(self):
        """Test error response simulation."""
        client = MockUSASpendingClient()
        
        # Test 400 error
        client.set_error_response(
            "/test/400",
            error_code=400,
            detail="Bad request detail"
        )
        
        with pytest.raises(APIError) as exc_info:
            client._make_request("GET", "/test/400")
        
        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == "Bad request detail"
        
        # Test 500 error
        client.set_error_response(
            "/test/500",
            error_code=500,
            error_message="Internal server error"
        )
        
        with pytest.raises(HTTPError) as exc_info:
            client._make_request("GET", "/test/500")
        
        assert exc_info.value.status_code == 500
        assert "HTTP 500" in str(exc_info.value)
    
    def test_paginated_response(self):
        """Test automatic pagination."""
        client = MockUSASpendingClient()
        
        # Create 250 items
        items = [{"id": i} for i in range(250)]
        client.set_paginated_response("/test/paginated", items, page_size=100)
        
        # Fetch pages
        page1 = client._make_request("POST", "/test/paginated", json={"page": 1})
        assert len(page1["results"]) == 100
        assert page1["page_metadata"]["hasNext"] is True
        assert page1["page_metadata"]["page"] == 1
        
        page2 = client._make_request("POST", "/test/paginated", json={"page": 2})
        assert len(page2["results"]) == 100
        assert page2["page_metadata"]["hasNext"] is True
        
        page3 = client._make_request("POST", "/test/paginated", json={"page": 3})
        assert len(page3["results"]) == 50
        assert page3["page_metadata"]["hasNext"] is False
    
    def test_response_sequence(self):
        """Test sequential responses."""
        client = MockUSASpendingClient()
        
        responses = [
            {"results": [{"id": 1}]},
            {"results": [{"id": 2}]},
            {"results": [{"id": 3}]}
        ]
        
        client.add_response_sequence("/test/sequence", responses)
        
        # Each call should return the next response
        assert client._make_request("GET", "/test/sequence")["results"][0]["id"] == 1
        assert client._make_request("GET", "/test/sequence")["results"][0]["id"] == 2
        assert client._make_request("GET", "/test/sequence")["results"][0]["id"] == 3
        
        # After sequence is exhausted, returns empty
        assert client._make_request("GET", "/test/sequence")["results"] == []
    
    def test_request_tracking(self):
        """Test request tracking functionality."""
        client = MockUSASpendingClient()
        
        # Make some requests
        client._make_request("GET", "/test/1")
        client._make_request("POST", "/test/2", json={"filter": "value"})
        client._make_request("GET", "/test/1")
        
        # Check counts
        assert client.get_request_count() == 3
        assert client.get_request_count("/test/1") == 2
        assert client.get_request_count("/test/2") == 1
        
        # Check last request
        last = client.get_last_request()
        assert last["endpoint"] == "/test/1"
        assert last["method"] == "GET"
        
        # Check last request for specific endpoint
        last_2 = client.get_last_request("/test/2")
        assert last_2["endpoint"] == "/test/2"
        assert last_2["json"] == {"filter": "value"}
    
    def test_assert_called_with(self):
        """Test request assertion helper."""
        client = MockUSASpendingClient()
        
        client._make_request("POST", "/test", json={"key": "value"})
        
        # Should pass
        client.assert_called_with(
            "/test",
            method="POST",
            json={"key": "value"}
        )
        
        # Should fail
        with pytest.raises(AssertionError):
            client.assert_called_with(
                "/test",
                method="GET"  # Wrong method
            )
    
    def test_reset(self):
        """Test reset functionality."""
        client = MockUSASpendingClient()
        
        # Set up state
        client.set_response("/test", {"data": "value"})
        client._make_request("GET", "/test")
        
        # Verify state exists
        assert client.get_request_count() == 1
        assert "/test" in client._default_responses
        
        # Reset
        client.reset()
        
        # Verify clean state
        assert client.get_request_count() == 0
        assert len(client._default_responses) == 0
        assert len(client._request_history) == 0


class TestResponseBuilder:
    """Test the ResponseBuilder helper."""
    
    def test_paginated_response(self):
        """Test building paginated responses."""
        response = ResponseBuilder.paginated_response(
            results=[{"id": 1}, {"id": 2}],
            page=2,
            has_next=True
        )
        
        assert response["results"] == [{"id": 1}, {"id": 2}]
        assert response["page_metadata"]["page"] == 2
        assert response["page_metadata"]["hasNext"] is True
        assert response["page_metadata"]["hasNext"] is True
    
    def test_award_search_response(self):
        """Test building award search responses."""
        response = ResponseBuilder.award_search_response(
            awards=[
                {"existing": "data"},
                {"Award ID": "123", "other": "field"}
            ]
        )
        
        # Should add missing required fields
        assert response["results"][0]["Award ID"].startswith("AWARD-")
        assert response["results"][0]["Recipient Name"] == "Unknown Recipient"
        assert response["results"][0]["Award Amount"] == 0
        
        # Should preserve existing fields
        assert response["results"][1]["Award ID"] == "123"
        assert response["results"][1]["other"] == "field"
    
    def test_count_response(self):
        """Test building count responses."""
        response = ResponseBuilder.count_response(
            contracts=100,
            grants=200,
            loans=50
        )
        
        assert response["results"]["contracts"] == 100
        assert response["results"]["grants"] == 200
        assert response["results"]["loans"] == 50
        assert response["results"]["idvs"] == 0  # Default
        assert response["spending_level"] == "awards"
    
    def test_error_response(self):
        """Test building error responses."""
        # With detail
        response1 = ResponseBuilder.error_response(
            status_code=400,
            detail="Detailed error message"
        )
        assert response1 == {"detail": "Detailed error message"}
        
        # With error
        response2 = ResponseBuilder.error_response(
            status_code=500,
            error="General error"
        )
        assert response2 == {"error": "General error"}
        
        # Default
        response3 = ResponseBuilder.error_response(status_code=404)
        assert response3 == {"error": "HTTP 404 Error"}
    
    def test_award_detail_response(self):
        """Test building award detail responses."""
        response = ResponseBuilder.award_detail_response(
            award_id="CONT_AWD_123",
            recipient_name="SpaceX",
            total_obligation=1000000.0,
            awarding_agency="NASA"
        )
        
        assert response["generated_unique_award_id"] == "CONT_AWD_123"
        assert response["recipient"]["recipient_name"] == "SpaceX"
        assert response["total_obligation"] == 1000000.0
        assert response["total_outlay"] == 800000.0  # 80% of obligations
        assert response["awarding_agency"]["toptier_agency"]["name"] == "NASA"
        assert response["category"] == "contract"  # Based on award_type "A"