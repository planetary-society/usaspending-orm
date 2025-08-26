"""Tests for Grant.subawards integration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from usaspending.models.grant import Grant
from usaspending.queries.subawards_search import SubAwardsSearch


class TestGrantSubawardsIntegration:
    """Test Grant model's subawards property integration."""

    def test_grant_subawards_property_returns_query_builder(self, mock_usa_client):
        """Test that grant.subawards returns a SubAwardsSearch query builder."""
        # Create a grant with a generated_unique_award_id
        grant_data = {
            "generated_unique_award_id": "ASST_AWD_123_456",
            "Award ID": "123456",
            "fain": "123456",
            "Award Type": "Grant",
        }
        grant = Grant(grant_data, mock_usa_client)
        
        # Mock the subawards resource on the client's _resources dict
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Mock the for_award method to return a SubAwardsSearch instance
        mock_search = SubAwardsSearch(mock_usa_client)
        mock_search._award_id = "ASST_AWD_123_456"
        mock_subawards_resource.for_award.return_value = mock_search
        
        # Access the subawards property
        result = grant.subawards
        
        # Verify it returns a SubAwardsSearch instance
        assert isinstance(result, SubAwardsSearch)
        assert result._award_id == "ASST_AWD_123_456"
        
        # Verify for_award was called with the correct award ID
        mock_subawards_resource.for_award.assert_called_once_with("ASST_AWD_123_456")

    def test_grant_subawards_applies_assistance_award_types(self, mock_usa_client):
        """Test that grant.subawards automatically applies assistance award types."""
        grant_data = {
            "generated_unique_award_id": "ASST_AWD_123_456",
            "Award ID": "123456",
            "fain": "123456",
        }
        grant = Grant(grant_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Expected grant award types (grants only due to validation constraints)
        expected_types = {"02", "03", "04", "05"}
        
        # Create a SubAwardsSearch instance for testing chaining
        search = SubAwardsSearch(mock_usa_client).with_award_types(*expected_types)
        search._award_id = "ASST_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Access the subawards property
        result = grant.subawards
        
        # Build the payload to verify assistance award types are applied
        payload = result._build_payload(page=1)
        
        # Verify assistance award types are included
        assert set(payload["filters"]["award_type_codes"]) == expected_types
        
        # Verify subaward-specific fields
        assert payload["subawards"] is True
        assert payload["spending_level"] == "subawards"
        
        # Verify the award filter is included
        assert payload["filters"]["award_unique_id"] == "ASST_AWD_123_456"

    def test_grant_subawards_can_be_chained(self, mock_usa_client):
        """Test that grant.subawards can be chained with additional filters."""
        grant_data = {
            "generated_unique_award_id": "ASST_AWD_123_456",
            "Award ID": "123456",
        }
        grant = Grant(grant_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Expected grant award types
        grant_types = {"02", "03", "04", "05"}
        
        # Create a SubAwardsSearch instance for testing chaining
        search = SubAwardsSearch(mock_usa_client).with_award_types(*grant_types)
        search._award_id = "ASST_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Chain additional methods on the subawards property
        query = grant.subawards.with_keywords("research").limit(25)
        
        # Verify the chain worked
        assert query._award_id == "ASST_AWD_123_456"
        assert query._total_limit == 25
        
        # Verify payload includes all filters
        payload = query._build_payload(page=1)
        assert set(payload["filters"]["award_type_codes"]) == grant_types
        assert "keywords" in payload["filters"]
        assert payload["limit"] == 25

    def test_grant_subawards_count_integration(self, mock_usa_client):
        """Test that grant.subawards.count() works correctly."""
        grant_data = {
            "generated_unique_award_id": "ASST_AWD_123_456",
            "Award ID": "123456",
        }
        grant = Grant(grant_data, mock_usa_client)
        
        # Mock the subawards resource
        mock_subawards_resource = MagicMock()
        mock_usa_client._resources["subawards"] = mock_subawards_resource
        
        # Expected grant award types
        grant_types = {"02", "03", "04", "05"}
        
        # Create a SubAwardsSearch instance with grant types
        search = SubAwardsSearch(mock_usa_client).with_award_types(*grant_types)
        search._award_id = "ASST_AWD_123_456"
        mock_subawards_resource.for_award.return_value = search
        
        # Mock the API response for count
        mock_usa_client._make_request = MagicMock(return_value={"subawards": 8})
        
        # Call count through the property
        count = grant.subawards.count()
        
        # Verify the result
        assert count == 8
        
        # Verify the correct endpoint was called
        mock_usa_client._make_request.assert_called_once_with(
            "GET", "/v2/awards/count/subaward/ASST_AWD_123_456/"
        )