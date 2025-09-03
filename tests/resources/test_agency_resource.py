"""Tests for agency resource implementation."""

import pytest

from usaspending.resources.agency_resource import AgencyResource
from usaspending.models.agency import Agency
from usaspending.exceptions import ValidationError


class TestAgencyResourceInitialization:
    """Test AgencyResource initialization."""

    def test_init_with_client(self, mock_usa_client):
        """Test AgencyResource initialization with client."""
        resource = AgencyResource(mock_usa_client)
        
        assert resource._client is mock_usa_client
        assert resource.client is mock_usa_client


class TestAgencyResourceFindByToptierCode:
    """Test AgencyResource.find_by_toptier_code() method."""

    @pytest.fixture
    def agency_resource(self, mock_usa_client):
        """Create an AgencyResource instance with mocked client."""
        return AgencyResource(mock_usa_client)

    def test_get_agency_success_without_fiscal_year(
        self, agency_resource, mock_usa_client, agency_fixture_data
    ):
        """Test successful agency retrieval without fiscal year."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"
        
        # Setup mock response using fixture
        mock_usa_client.set_fixture_response(endpoint, "agency")
        
        # Call the method
        agency = agency_resource.find_by_toptier_code(toptier_code)
        
        # Verify return value
        assert isinstance(agency, Agency)
        assert agency._client is mock_usa_client
        assert agency.toptier_code == agency_fixture_data["toptier_code"]
        assert agency.name == agency_fixture_data["name"]
        
        # Verify correct API call was made
        last_request = mock_usa_client.get_last_request()
        assert last_request["endpoint"] == endpoint
        assert last_request["method"] == "GET"
        assert last_request["params"] is None

    def test_get_agency_success_with_fiscal_year(
        self, agency_resource, mock_usa_client, agency_fixture_data
    ):
        """Test successful agency retrieval with fiscal year."""
        toptier_code = agency_fixture_data["toptier_code"]
        fiscal_year = 2023
        endpoint = f"/agency/{toptier_code}/"
        
        # Setup mock response using fixture
        mock_usa_client.set_fixture_response(endpoint, "agency")
        
        # Call the method
        agency = agency_resource.find_by_toptier_code(toptier_code, fiscal_year=fiscal_year)
        
        # Verify return value
        assert isinstance(agency, Agency)
        assert agency._client is mock_usa_client
        
        # Verify correct API call was made with params
        last_request = mock_usa_client.get_last_request()
        assert last_request["endpoint"] == endpoint
        assert last_request["method"] == "GET"
        assert last_request["params"] == {"fiscal_year": fiscal_year}

    def test_get_agency_with_full_fixture_properties(
        self, agency_resource, mock_usa_client, agency_fixture_data
    ):
        """Test agency retrieval contains all fixture properties."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"
        
        mock_usa_client.set_fixture_response(endpoint, "agency")
        
        agency = agency_resource.find_by_toptier_code(toptier_code)
        
        # Test all major properties using fixture data
        assert agency.fiscal_year == agency_fixture_data["fiscal_year"]
        assert agency.toptier_code == agency_fixture_data["toptier_code"]
        assert agency.name == agency_fixture_data["name"]
        assert agency.abbreviation == agency_fixture_data["abbreviation"]
        assert agency.agency_id == agency_fixture_data["agency_id"]
        assert agency.icon_filename == agency_fixture_data["icon_filename"]
        assert agency.mission == agency_fixture_data["mission"]
        assert agency.website == agency_fixture_data["website"]
        assert agency.congressional_justification_url == agency_fixture_data["congressional_justification_url"]
        assert agency.about_agency_data == agency_fixture_data["about_agency_data"]
        assert agency.subtier_agency_count == agency_fixture_data["subtier_agency_count"]
        assert agency.messages == agency_fixture_data["messages"]
        
        # Test def_codes
        def_codes = agency.def_codes
        expected_def_codes = agency_fixture_data["def_codes"]
        assert len(def_codes) == len(expected_def_codes)

    def test_get_agency_empty_toptier_code_raises_validation_error(self, agency_resource):
        """Test that empty toptier_code raises ValidationError."""
        with pytest.raises(ValidationError, match="toptier_code is required"):
            agency_resource.find_by_toptier_code("")

    def test_get_agency_invalid_toptier_code_raises_validation_error(self, agency_resource):
        """Test that invalid toptier_code raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid toptier_code"):
            agency_resource.find_by_toptier_code("ABC")  # Non-numeric

    def test_get_agency_api_error_propagates(self, agency_resource, mock_usa_client):
        """Test that API errors are propagated."""
        toptier_code = "999"
        endpoint = f"/agency/{toptier_code}/"
        
        # Set up error response
        mock_usa_client.set_error_response(
            endpoint, 404, error_message="Agency not found"
        )
        
        from usaspending.exceptions import HTTPError
        
        with pytest.raises(HTTPError, match="Agency not found"):
            agency_resource.find_by_toptier_code(toptier_code)


class TestAgencyResourceClientIntegration:
    """Test AgencyResource integration with USASpending client."""

    def test_agency_resource_accessible_via_client(self, mock_usa_client):
        """Test that AgencyResource is accessible via client.agencies property."""
        agencies = mock_usa_client.agencies
        
        assert isinstance(agencies, AgencyResource)
        assert agencies._client is mock_usa_client

    def test_agency_resource_lazy_loaded_in_client(self, mock_usa_client):
        """Test that AgencyResource is lazy-loaded in client."""
        # First access should create the resource
        agencies1 = mock_usa_client.agencies
        
        # Second access should return the same instance
        agencies2 = mock_usa_client.agencies
        
        assert agencies1 is agencies2

    def test_client_agencies_get_integration(
        self, mock_usa_client, agency_fixture_data
    ):
        """Test integration: client.agencies.find_by_toptier_code() works end-to-end."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"
        
        mock_usa_client.set_fixture_response(endpoint, "agency")
        
        # Call through client
        agency = mock_usa_client.agencies.find_by_toptier_code(toptier_code)
        
        # Verify it works
        assert isinstance(agency, Agency)
        assert agency.toptier_code == agency_fixture_data["toptier_code"]
        assert agency.name == agency_fixture_data["name"]

    def test_client_agencies_get_with_fiscal_year_integration(
        self, mock_usa_client, agency_fixture_data
    ):
        """Test integration: client.agencies.find_by_toptier_code() with fiscal_year works end-to-end."""
        toptier_code = agency_fixture_data["toptier_code"]
        fiscal_year = 2023
        endpoint = f"/agency/{toptier_code}/"
        
        mock_usa_client.set_fixture_response(endpoint, "agency")
        
        # Call through client with fiscal_year
        agency = mock_usa_client.agencies.find_by_toptier_code(toptier_code, fiscal_year=fiscal_year)
        
        # Verify it works
        assert isinstance(agency, Agency)
        
        # Verify fiscal_year parameter was passed
        last_request = mock_usa_client.get_last_request()
        assert last_request["params"] == {"fiscal_year": fiscal_year}


class TestAgencyResourceUsagePatterns:
    """Test common usage patterns for AgencyResource."""

    def test_get_nasa_current_fiscal_year(self, mock_usa_client, agency_fixture_data):
        """Test getting NASA for current fiscal year (common usage pattern)."""
        if agency_fixture_data["toptier_code"] == "080":  # NASA
            endpoint = "/agency/080/"
            mock_usa_client.set_fixture_response(endpoint, "agency")
            
            # Common usage: get current fiscal year data
            agency = mock_usa_client.agencies.find_by_toptier_code("080")
            
            assert agency.name == agency_fixture_data["name"]
            assert agency.abbreviation == agency_fixture_data["abbreviation"]
            assert isinstance(agency.def_codes, list)

    def test_get_agency_specific_fiscal_year(self, mock_usa_client, agency_fixture_data):
        """Test getting agency for specific fiscal year (common usage pattern)."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"
        mock_usa_client.set_fixture_response(endpoint, "agency")
        
        # Common usage: get specific fiscal year data
        agency = mock_usa_client.agencies.find_by_toptier_code(toptier_code, fiscal_year=2023)
        
        assert agency.toptier_code == toptier_code
        assert isinstance(agency.messages, list)

    def test_access_agency_mission_and_website(self, mock_usa_client, agency_fixture_data):
        """Test accessing agency mission and website (common usage pattern)."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"
        mock_usa_client.set_fixture_response(endpoint, "agency")
        
        agency = mock_usa_client.agencies.find_by_toptier_code(toptier_code)
        
        # Common usage: access agency details
        assert agency.mission == agency_fixture_data["mission"]
        assert agency.website == agency_fixture_data["website"]
        assert agency.subtier_agency_count == agency_fixture_data["subtier_agency_count"]