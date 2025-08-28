"""Tests for Agency model subagencies property integration."""

import pytest
from usaspending.models.agency import Agency
from usaspending.models.subtier_agency import SubTierAgency


class TestAgencySubagencies:
    """Test Agency model subagencies property integration."""

    def test_subagencies_property_basic(self, mock_usa_client, agency_subagencies_fixture_data):
        """Test that agency.subagencies returns SubTierAgency objects."""
        # Set up mock response
        mock_usa_client.set_response(
            "/api/v2/agency/080/sub_agency/", 
            agency_subagencies_fixture_data
        )
        
        # Create agency with minimal required data
        agency_data = {
            "code": "080",
            "toptier_code": "080",
            "name": "NASA",
            "fiscal_year": 2025
        }
        
        agency = Agency(agency_data, mock_usa_client)
        subagencies = agency.subagencies
        
        # Verify API call was made
        mock_usa_client.assert_called_with(
            "/api/v2/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
                "fiscal_year": 2025
            }
        )
        
        # Verify results
        assert len(subagencies) == 1
        assert all(isinstance(sub, SubTierAgency) for sub in subagencies)
        
        subagency = subagencies[0]
        assert subagency.name == "National Aeronautics and Space Administration"
        assert subagency.abbreviation == "NASA"
        assert subagency.total_obligations == 17275121376.15
        assert subagency.transaction_count == 29818
        assert subagency.new_award_count == 5465

    def test_subagencies_property_with_offices(self, mock_usa_client, agency_subagencies_fixture_data):
        """Test that subagencies have offices populated."""
        # Set up mock response
        mock_usa_client.set_response(
            "/api/v2/agency/080/sub_agency/", 
            agency_subagencies_fixture_data
        )
        
        # Create agency with minimal required data
        agency_data = {
            "code": "080",
            "toptier_code": "080",
            "name": "NASA"
        }
        
        agency = Agency(agency_data, mock_usa_client)
        subagencies = agency.subagencies
        
        assert len(subagencies) == 1
        subagency = subagencies[0]
        
        # Check that offices are populated
        offices = subagency.offices
        assert len(offices) == 13  # Should match fixture data
        assert all(isinstance(office, SubTierAgency) for office in offices)
        
        # Check first office details
        first_office = offices[0]
        assert first_office.code == "80JSC0"
        assert first_office.name == "NASA JOHNSON SPACE CENTER"
        assert first_office.total_obligations == 3938738374.3
        assert first_office.transaction_count == 1899
        assert first_office.new_award_count == 210

    def test_subagencies_property_no_code(self, mock_usa_client):
        """Test that subagencies returns empty list when agency has no code."""
        agency_data = {
            "name": "Test Agency"
            # No code provided
        }
        
        agency = Agency(agency_data, mock_usa_client)
        subagencies = agency.subagencies
        
        assert subagencies == []

    def test_subagencies_property_api_error(self, mock_usa_client):
        """Test that subagencies returns empty list on API error."""
        # Mock API error
        mock_usa_client.set_error_response(
            "/api/v2/agency/080/sub_agency/", 
            error_code=500, 
            error_message="API Error"
        )
        
        agency_data = {
            "code": "080",
            "toptier_code": "080",
            "name": "Test Agency"
        }
        
        agency = Agency(agency_data, mock_usa_client)
        subagencies = agency.subagencies
        
        assert subagencies == []

    def test_subagencies_property_uses_fiscal_year(self, mock_usa_client, agency_subagencies_fixture_data):
        """Test that subagencies uses agency's fiscal year if available."""
        # Set up mock response
        mock_usa_client.set_response(
            "/api/v2/agency/080/sub_agency/", 
            agency_subagencies_fixture_data
        )
        
        agency_data = {
            "code": "080",
            "toptier_code": "080", 
            "name": "NASA",
            "fiscal_year": 2024  # Specific fiscal year
        }
        
        agency = Agency(agency_data, mock_usa_client)
        subagencies = agency.subagencies
        
        # Verify API was called with the agency's fiscal year
        mock_usa_client.assert_called_with(
            "/api/v2/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
                "fiscal_year": 2024
            }
        )
        
        assert len(subagencies) == 1

    def test_subagencies_property_no_fiscal_year(self, mock_usa_client, agency_subagencies_fixture_data):
        """Test that subagencies works without fiscal year."""
        # Set up mock response
        mock_usa_client.set_response(
            "/api/v2/agency/080/sub_agency/", 
            agency_subagencies_fixture_data
        )
        
        agency_data = {
            "code": "080",
            "toptier_code": "080",
            "name": "NASA"
            # No fiscal year
        }
        
        agency = Agency(agency_data, mock_usa_client)
        subagencies = agency.subagencies
        
        # Verify API was called without fiscal year
        mock_usa_client.assert_called_with(
            "/api/v2/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100
            }
        )
        
        assert len(subagencies) == 1

    def test_subagencies_property_empty_results(self, mock_usa_client):
        """Test subagencies with empty API results."""
        empty_response = {
            "toptier_code": "080",
            "fiscal_year": 2025,
            "page_metadata": {
                "page": 1,
                "total": 0,
                "limit": 100,
                "next": None,
                "previous": None,
                "hasNext": False,
                "hasPrevious": False
            },
            "results": [],
            "messages": []
        }
        
        mock_usa_client.set_response("/api/v2/agency/080/sub_agency/", empty_response)
        
        agency_data = {
            "code": "080",
            "name": "Test Agency"
        }
        
        agency = Agency(agency_data, mock_usa_client)
        subagencies = agency.subagencies
        
        assert subagencies == []

    def test_subagencies_property_invalid_result_format(self, mock_usa_client):
        """Test subagencies handles invalid result format gracefully."""
        invalid_response = {
            "toptier_code": "080",
            "fiscal_year": 2025,
            "results": ["invalid", {"valid": "data"}, None]  # Mixed invalid data
        }
        
        mock_usa_client.set_response("/api/v2/agency/080/sub_agency/", invalid_response)
        
        agency_data = {
            "code": "080", 
            "name": "Test Agency"
        }
        
        agency = Agency(agency_data, mock_usa_client)
        subagencies = agency.subagencies
        
        # Should only include the valid dict entry
        assert len(subagencies) == 1
        assert isinstance(subagencies[0], SubTierAgency)