"""Tests for Contract.subawards integration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from usaspending.models.contract import Contract
from usaspending.queries.subawards_search import SubAwardsSearch


class TestContractSubawardsIntegration:
    """Test Contract model's subawards property integration."""

    def test_contract_subawards_property_returns_query_builder(self, mock_usa_client):
        """Test that contract.subawards returns a SubAwardsSearch query builder."""
        # Create a contract with a generated_unique_award_id
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
            "piid": "123456",
            "Contract Award Type": "Definitive Contract",
        }
        contract = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource on the client's _resources dict
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Mock the for_award method to return a SubAwardsSearch instance
        mock_search = SubAwardsSearch(mock_usa_client)
        mock_search._award_id = "CONT_AWD_123_456"
        mock_subawards_resource.for_award.return_value = mock_search
        
        # Access the subawards property
        result = contract.subawards
        
        # Verify it returns a SubAwardsSearch instance
        assert isinstance(result, SubAwardsSearch)
        assert result._award_id == "CONT_AWD_123_456"
        
        # Verify for_award was called with the correct award ID
        mock_subawards_resource.for_award.assert_called_once_with("CONT_AWD_123_456")

    def test_contract_subawards_applies_contract_award_types(self, mock_usa_client):
        """Test that contract.subawards automatically applies contract award types."""
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
            "piid": "123456",
        }
        contract = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Create a SubAwardsSearch instance for testing chaining
        search = SubAwardsSearch(mock_usa_client).with_award_types("A", "B", "C", "D")
        search._award_id = "CONT_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Access the subawards property
        result = contract.subawards
        
        # Build the payload to verify contract award types are applied
        payload = result._build_payload(page=1)
        
        # Verify contract award types are included
        assert set(payload["filters"]["award_type_codes"]) == {"A", "B", "C", "D"}
        
        # Verify subaward-specific fields
        assert payload["subawards"] is True
        assert payload["spending_level"] == "subawards"
        
        # Verify the award filter is included
        assert payload["filters"]["award_unique_id"] == "CONT_AWD_123_456"

    def test_contract_subawards_can_be_chained(self, mock_usa_client):
        """Test that contract.subawards can be chained with additional filters."""
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
        }
        contract = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Create a SubAwardsSearch instance for testing chaining
        search = SubAwardsSearch(mock_usa_client).with_award_types("A", "B", "C", "D")
        search._award_id = "CONT_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Chain additional methods on the subawards property
        query = contract.subawards.in_time_period("2024-01-01", "2024-12-31").limit(25)
        
        # Verify the chain worked
        assert query._award_id == "CONT_AWD_123_456"
        assert query._total_limit == 25
        
        # Verify payload includes all filters
        payload = query._build_payload(page=1)
        assert set(payload["filters"]["award_type_codes"]) == {"A", "B", "C", "D"}
        assert "time_period" in payload["filters"]
        assert payload["limit"] == 25

    def test_contract_subawards_count_integration(self, mock_usa_client):
        """Test that contract.subawards.count() works correctly."""
        contract_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
        }
        contract = Contract(contract_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Create a SubAwardsSearch instance with contract types
        search = SubAwardsSearch(mock_usa_client).with_award_types("A", "B", "C", "D")
        search._award_id = "CONT_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Mock the API response for count
        mock_usa_client._make_request = MagicMock(return_value={"subawards": 15})
        
        # Call count through the property
        count = contract.subawards.count()
        
        # Verify the result
        assert count == 15
        
        # Verify the correct endpoint was called
        mock_usa_client._make_request.assert_called_once_with(
            "GET", "/v2/awards/count/subaward/CONT_AWD_123_456/"
        )