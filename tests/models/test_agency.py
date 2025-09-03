"""Tests for the restructured Agency model functionality."""

from __future__ import annotations

from usaspending.models.agency import Agency


class TestAgencyNewStructure:
    """Test Agency model with new clean structure."""

    def test_agency_with_toptier_data_only(self, mock_usa_client):
        """Test Agency with just toptier data and top-level fields."""
        data = {
            "id": 862,
            "has_agency_page": True,
            "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER",
            "name": "National Aeronautics and Space Administration",
            "code": "080",
            "abbreviation": "NASA",
            "slug": "national-aeronautics-and-space-administration"
        }
        
        agency = Agency(data, mock_usa_client)
        
        # Test direct data access
        assert agency.agency_id == 862
        assert agency.has_agency_page is True
        assert agency.office_agency_name == "NASA GODDARD SPACE FLIGHT CENTER"
        assert agency.name == "National Aeronautics and Space Administration"
        assert agency.code == "080"
        assert agency.abbreviation == "NASA"
        assert agency.slug == "national-aeronautics-and-space-administration"
        
        # Agency now represents toptier data directly
        # No toptier_agency or subtier_agency properties needed

    def test_agency_with_subtier_data(self, mock_usa_client):
        """Test Agency with both toptier and subtier data."""
        toptier_data = {
            "id": 862,
            "has_agency_page": True,
            "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER",
            "name": "National Aeronautics and Space Administration",
            "code": "080",
            "abbreviation": "NASA",
            "slug": "national-aeronautics-and-space-administration"
        }
        
        subtier_data = {
            "name": "National Aeronautics and Space Administration",
            "code": "8000",
            "abbreviation": "NASA"
        }
        
        agency = Agency(toptier_data, mock_usa_client, subtier_data)
        
        # Test toptier data
        assert agency.name == "National Aeronautics and Space Administration"
        assert agency.code == "080"
        assert agency.abbreviation == "NASA"
        
        # With the new structure, Agency only handles toptier data directly
        # Subtier data would be handled separately by SubTierAgency if needed
        # The subtier data is passed to constructor but not exposed as a property

    def test_agency_with_minimal_required_data(self, mock_usa_client):
        """Test Agency with minimal required data."""
        data = {
            "id": 862,
            "name": "NASA",
            "code": "080"
        }
        
        agency = Agency(data, mock_usa_client)
        
        assert agency.agency_id == 862
        assert agency.name == "NASA"
        assert agency.code == "080"

    def test_agency_string_representation(self, mock_usa_client):
        """Test Agency string representation."""
        data = {
            "name": "National Aeronautics and Space Administration",
            "code": "080"
        }
        
        agency = Agency(data, mock_usa_client)
        
        repr_str = repr(agency)
        assert repr_str == "<Agency 080: National Aeronautics and Space Administration>"

    def test_agency_with_minimal_data(self, mock_usa_client):
        """Test Agency with minimal data."""
        data = {"id": 862}
        
        agency = Agency(data, mock_usa_client)
        
        assert agency.agency_id == 862
        assert agency.name is None
        assert agency.code is None
        
        # String representation with missing data
        repr_str = repr(agency)
        assert repr_str == "<Agency ?: ?>"


class TestAgencyObligationMethodsNewStructure:
    """Test Agency obligation methods with new structure."""

    def test_obligations_method_existing_data(self, mock_usa_client):
        """Test obligations method returns existing data when no filters."""
        data = {"id": 862, "total_obligations": 1000000.50, "code": "080"}
        agency = Agency(data, mock_usa_client)
        
        assert agency.obligations() == 1000000.50
        assert isinstance(agency.obligations(), float)

    def test_contract_obligations_with_minimal_data(self, mock_usa_client):
        """Test contract obligations returns None when no data is available."""
        data = {"id": 862, "code": "080"}
        agency = Agency(data, mock_usa_client)
        
        # Should return None when no award summary data is available
        assert agency.contract_obligations() is None

    def test_get_toptier_code_new_structure(self, mock_usa_client):
        """Test _get_toptier_code with new structure."""
        data = {"code": "080", "id": 862}
        agency = Agency(data, mock_usa_client)
        
        assert agency.code == "080"

    def test_get_toptier_code_with_toptier_code_field(self, mock_usa_client):
        """Test _get_toptier_code prefers toptier_code field."""
        data = {"toptier_code": "080", "id": 862}
        agency = Agency(data, mock_usa_client)
        
        assert agency.code == "080"


class TestAgencyLazyLoadingNewStructure:
    """Test Agency lazy loading with new structure."""

    def test_agency_lazy_loading_simple(self, mock_usa_client, agency_fixture_data):
        """Test lazy loading works with new structure."""
        # Start with minimal data
        minimal_data = {
            "id": 862,
            "code": "080"
        }
        
        agency = Agency(minimal_data, mock_usa_client)
        
        # Mock the full agency response
        endpoint = "/agency/080/"
        mock_usa_client.set_fixture_response(endpoint, "agency")
        
        # Access a lazy-loaded property
        mission = agency.mission
        
        # Should have fetched the full data
        assert mission == agency_fixture_data["mission"]

    def test_agency_with_minimal_data_lazy_loading(self, mock_usa_client):
        """Test that agency with minimal data can still attempt lazy loading."""
        data = {"id": 862, "code": "080"}
        agency = Agency(data, mock_usa_client)
        
        # Should return None for lazy-loaded properties when no fixture is set
        assert agency.mission is None
        # _fetch_details may return data from the mock client
        result = agency._fetch_details()
        assert result is not None  # Mock client returns data


class TestAgencyIntegrationWithFixtures:
    """Test Agency with real fixture data using new structure."""

    def test_agency_from_award_fixture(self, contract_fixture_data, mock_usa_client):
        """Test creating Agency from award fixture data."""
        # Extract the award agency data
        award_agency_data = contract_fixture_data["funding_agency"]
        
        # Create Agency using new structure
        toptier_data = award_agency_data.get("toptier_agency", {})
        agency_data = {
            "id": award_agency_data.get("id"),
            "has_agency_page": award_agency_data.get("has_agency_page"),
            "office_agency_name": award_agency_data.get("office_agency_name"),
            **toptier_data
        }
        
        subtier_data = award_agency_data.get("subtier_agency")
        agency = Agency(agency_data, mock_usa_client, subtier_data)
        
        # Test the data
        assert agency.agency_id == 862
        assert agency.has_agency_page is True
        assert agency.name == "National Aeronautics and Space Administration"
        assert agency.code == "080"
        assert agency.abbreviation == "NASA"
        assert agency.slug == "national-aeronautics-and-space-administration"
        assert agency.office_agency_name == "NASA GODDARD SPACE FLIGHT CENTER"
        
        # Agency now only handles toptier data directly
        # Subtier data would need to be handled separately via SubTierAgency if needed
        # The agency constructor received subtier_data but doesn't expose it as a property