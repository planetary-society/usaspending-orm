"""Tests for Award.subawards integration."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

from usaspending.models.award import Award
from usaspending.models.contract import Contract
from usaspending.queries.subawards_search import SubAwardsSearch


class TestAwardSubawardsIntegration:
    """Test Award model's subawards property integration."""

    def test_award_subawards_property_returns_query_builder(self, mock_usa_client):
        """Test that contract.subawards returns a SubAwardsSearch query builder."""
        # Create a contract with a generated_unique_award_id
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
            "Recipient Name": "Test Company",
            "piid": "123456",
        }
        award = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource on the client's _resources dict
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Mock the for_award method to return a SubAwardsSearch instance
        mock_search = SubAwardsSearch(mock_usa_client)
        mock_search._award_id = "CONT_AWD_123_456"
        mock_subawards_resource.for_award.return_value = mock_search
        
        # Access the subawards property
        result = award.subawards
        
        # Verify it returns a SubAwardsSearch instance
        assert isinstance(result, SubAwardsSearch)
        assert result._award_id == "CONT_AWD_123_456"
        
        # Verify for_award was called with the correct award ID
        mock_subawards_resource.for_award.assert_called_once_with("CONT_AWD_123_456")

    def test_award_subawards_can_be_chained(self, mock_usa_client):
        """Test that contract.subawards can be chained with query methods."""
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
            "piid": "123456",
        }
        award = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Create a real SubAwardsSearch instance for testing chaining
        search = SubAwardsSearch(mock_usa_client)
        search._award_id = "CONT_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Chain methods on the subawards property
        query = award.subawards.limit(10).page_size(5)
        
        # Verify the chain worked
        assert query._award_id == "CONT_AWD_123_456"
        assert query._total_limit == 10
        assert query._page_size == 5

    def test_award_subawards_count_integration(self, mock_usa_client):
        """Test that contract.subawards.count() works correctly."""
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
            "piid": "123456",
        }
        award = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Create a SubAwardsSearch instance
        search = SubAwardsSearch(mock_usa_client)
        search._award_id = "CONT_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Mock the API response for count
        mock_usa_client._make_request = MagicMock(return_value={"subawards": 7})
        
        # Call count through the property
        count = award.subawards.count()
        
        # Verify the result
        assert count == 7
        
        # Verify the correct endpoint was called
        mock_usa_client._make_request.assert_called_once_with(
            "GET", "/v2/awards/count/subaward/CONT_AWD_123_456/"
        )

    def test_award_subawards_with_filters(self, mock_usa_client):
        """Test that contract.subawards can apply additional filters."""
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
            "piid": "123456",
        }
        award = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Create a SubAwardsSearch instance
        search = SubAwardsSearch(mock_usa_client)
        search._award_id = "CONT_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Apply filters through the property (contract.subawards already has award types A,B,C,D)
        query = (award.subawards
                .in_time_period("2024-01-01", "2024-12-31")
                .limit(25))
        
        # Build the payload to verify filters are applied
        payload = query._build_payload(page=1)
        
        # Verify subaward-specific fields
        assert payload["subawards"] is True
        assert payload["spending_level"] == "subawards"
        
        # Verify the award filter is included
        assert payload["filters"]["prime_award_generated_internal_id"] == "CONT_AWD_123_456"
        
        # Verify contract award types are automatically applied
        assert set(payload["filters"]["award_type_codes"]) == {"A", "B", "C", "D"}
        assert "time_period" in payload["filters"]
        assert payload["limit"] == 25

    def test_award_without_id_raises_error_on_subawards(self, mock_usa_client):
        """Test that accessing subawards on a contract without generated_unique_award_id works."""
        # Contract without generated_unique_award_id
        contract_data = {
            "Award ID": "123456",
            "Recipient Name": "Test Company",
            "piid": "123456",
        }
        award = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # The property should still work but pass None
        search = SubAwardsSearch(mock_usa_client)
        mock_subawards_resource.for_award.return_value = search
        
        # Access should work but with None as the award_id
        result = award.subawards
        
        # Verify for_award was called with None
        mock_subawards_resource.for_award.assert_called_once_with(None)

    def test_award_subawards_iteration(self, mock_usa_client):
        """Test that iterating over contract.subawards works correctly."""
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "piid": "123456",
        }
        contract = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Create a SubAwardsSearch instance with pre-set award types for contract
        search = SubAwardsSearch(mock_usa_client)
        search._award_id = "CONT_AWD_123_456"
        
        # Mock the _execute_query method to return the mock data
        def mock_execute(page):
            if page == 1:
                return {
                    "results": [
                        {"internal_id": "Z1", "Sub-Award ID": "Z1", "Sub-Award Amount": 1000},
                        {"internal_id": "Z2", "Sub-Award ID": "Z2", "Sub-Award Amount": 2000},
                    ],
                    "page_metadata": {"hasNext": False}
                }
            return {"results": [], "page_metadata": {"hasNext": False}}
        
        # Mock any method chaining operations to return the same search instance
        from usaspending.models.subaward import SubAward
        chained_search = MagicMock(spec=SubAwardsSearch)
        chained_search._execute_query = MagicMock(side_effect=mock_execute)
        chained_search._award_id = "CONT_AWD_123_456"
        
        # Define the mock subaward objects outside the lambda
        mock_subaward_1 = SubAward({"internal_id": "Z1", "Sub-Award ID": "Z1", "Sub-Award Amount": 1000})
        mock_subaward_2 = SubAward({"internal_id": "Z2", "Sub-Award ID": "Z2", "Sub-Award Amount": 2000})
        chained_search.__iter__ = lambda self: iter([mock_subaward_1, mock_subaward_2])
        
        # Mock the for_award method to return our base search
        mock_subawards_resource.for_award.return_value = search
        
        # Mock with_award_types to return the chained search
        search.with_award_types = MagicMock(return_value=chained_search)
        
        # Iterate over subawards through the contract property
        subawards_list = list(contract.subawards)
        
        # Verify results
        assert len(subawards_list) == 2
        assert all(isinstance(s, SubAward) for s in subawards_list)
        assert subawards_list[0].sub_award_id == "Z1"
        assert subawards_list[1].sub_award_id == "Z2"