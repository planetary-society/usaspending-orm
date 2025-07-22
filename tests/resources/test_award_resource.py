"""Tests for award resource implementation."""

import json
import pytest
from unittest.mock import Mock
from pathlib import Path

from usaspending.resources import AwardResource
from usaspending.models import Award, Recipient
from usaspending.exceptions import ValidationError


class TestAwardResource:
    """Tests for AwardResource.get() method."""

    @pytest.fixture
    def award_fixture_data(self):
        """Load award fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "contract.json"
        with open(fixture_path) as f:
            return json.load(f)

    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing."""
        client = Mock()
        client._make_request = Mock()
        return client

    @pytest.fixture
    def award_resource(self, mock_client):
        """Create an AwardResource instance with mocked client."""
        return AwardResource(mock_client)

    def test_get_award_success(self, award_resource, mock_client, award_fixture_data):
        """Test successful award retrieval."""
        # Setup mock response
        mock_client._make_request.return_value = award_fixture_data
        
        # Call the method
        award = award_resource.get("CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-")
        
        # Verify API call
        mock_client._make_request.assert_called_once_with(
            "GET", 
            "/v2/awards/CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-/"
        )
        
        # Verify return value
        assert isinstance(award, Award)
        assert award._client is mock_client
        assert award.generated_unique_award_id == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"

    def test_get_award_strips_whitespace(self, award_resource, mock_client, award_fixture_data):
        """Test that award_id is stripped of whitespace."""
        mock_client._make_request.return_value = award_fixture_data
        
        award = award_resource.get("  CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-  ")
        
        mock_client._make_request.assert_called_once_with(
            "GET", 
            "/v2/awards/CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-/"
        )

    def test_get_award_empty_id_raises_validation_error(self, award_resource):
        """Test that empty award_id raises ValidationError."""
        with pytest.raises(ValidationError):
            award_resource.get("")
        with pytest.raises(ValidationError):
            award_resource.get(None)
        with pytest.raises(ValidationError):
            award_resource.get("   ")

    def test_get_award_api_error_propagates(self, award_resource, mock_client):
        """Test that API errors are propagated."""
        from usaspending.exceptions import APIError
        
        mock_client._make_request.side_effect = APIError("Award not found")
        
        with pytest.raises(APIError, match="Award not found"):
            award_resource.get("INVALID_AWARD_ID")

    def test_award_model_initialization_with_client(self, award_fixture_data, mock_client):
        """Test Award model initialization with client parameter."""
        award = Award(award_fixture_data, client=mock_client)
        
        assert award._client is mock_client
        assert award.generated_unique_award_id == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"

    def test_award_model_initialization_without_client(self, award_fixture_data):
        """Test Award model initialization without client parameter."""
        
        with pytest.raises(TypeError):
            award = Award(award_fixture_data)
    
    def test_award_model_properties_from_fixture(self, award_fixture_data, mock_client):
        """Test that Award model properties work with fixture data."""
        award = Award(award_fixture_data, mock_client)
        
        # Test basic properties
        assert award.generated_unique_award_id == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        assert award.total_obligation == 168657782.95
        assert award.total_outlay == 150511166.49
        
        # Test helper methods
        
        # Preferentially return the external Award ID
        assert award.prime_award_id == award_fixture_data.get("piid", "")
        
        # Test description is present
        assert award.description
        
        # Ensure description is not all uppercase
        assert not award.description.isupper()
    
    def test_award_loads_related_models(self, award_fixture_data, mock_client):
        """Test that Award model properties work with fixture data."""
        award = Award(award_fixture_data, mock_client)
        
        # Test that recipient data is accessible
        assert isinstance(award.recipient, Recipient)
        assert award.recipient.name == "The University of Iowa"
        
        # Test place of performance
        assert award.place_of_performance is not None
        assert award.place_of_performance.state_code == "IA"
        assert award.place_of_performance.city_name == "IOWA CITY"