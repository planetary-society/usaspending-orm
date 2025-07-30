"""Tests for Agency model functionality."""

from __future__ import annotations


from usaspending.models.agency import Agency, AgencyTier


class TestAgencyInitialization:
    """Test Agency model initialization."""
    
    def test_init_with_dict_data(self, mock_usa_client):
        """Test Agency initialization with dictionary data."""
        data = {
            "id": 862,
            "has_agency_page": True,
            "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER"
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency._data["id"] == 862
        assert agency._data["has_agency_page"] is True
        assert agency._data["office_agency_name"] == "NASA GODDARD SPACE FLIGHT CENTER"
        assert agency._client is not None


class TestAgencyBasicProperties:
    """Test basic Agency properties."""
    
    def test_id_property(self, mock_usa_client):
        """Test agency ID property."""
        data = {"id": 862, "has_agency_page": True}
        agency = Agency(data, mock_usa_client)
        
        assert agency.id == 862
        assert isinstance(agency.id, int)
    
    def test_id_property_none(self, mock_usa_client):
        """Test ID property when not present."""
        data = {"has_agency_page": True}
        agency = Agency(data, mock_usa_client)
        
        assert agency.id is None
    
    def test_has_agency_page_property(self, mock_usa_client):
        """Test has_agency_page property."""
        data = {"id": 862, "has_agency_page": True}
        agency = Agency(data, mock_usa_client)
        
        assert agency.has_agency_page is True
        assert isinstance(agency.has_agency_page, bool)
    
    def test_has_agency_page_default_false(self, mock_usa_client):
        """Test has_agency_page defaults to False."""
        data = {"id": 862}
        agency = Agency(data, mock_usa_client)
        
        assert agency.has_agency_page is False
    
    def test_office_agency_name_property(self, mock_usa_client):
        """Test office agency name property."""
        data = {
            "id": 862,
            "office_agency_name": "NASA JOHNSON SPACE CENTER"
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.office_agency_name == "NASA JOHNSON SPACE CENTER"
    
    def test_office_agency_name_none(self, mock_usa_client):
        """Test office agency name when not present."""
        data = {"id": 862}
        agency = Agency(data, mock_usa_client)
        
        assert agency.office_agency_name is None


class TestAgencyTierProperties:
    """Test Agency tier-related properties."""
    
    def test_toptier_agency_property(self, mock_usa_client):
        """Test toptier agency property returns AgencyTier."""
        toptier_data = {
            "name": "National Aeronautics and Space Administration",
            "code": "080",
            "abbreviation": "NASA",
            "slug": "national-aeronautics-and-space-administration"
        }
        data = {
            "id": 862,
            "toptier_agency": toptier_data
        }
        agency = Agency(data, mock_usa_client)
        
        toptier = agency.toptier_agency
        assert isinstance(toptier, AgencyTier)
        assert toptier.name == "National Aeronautics and Space Administration"
        assert toptier.code == "080"
        assert toptier.abbreviation == "NASA"
        assert toptier.slug == "national-aeronautics-and-space-administration"
    
    def test_toptier_agency_cached(self, mock_usa_client):
        """Test toptier agency property is cached."""
        toptier_data = {
            "name": "NASA",
            "code": "080"
        }
        data = {
            "id": 862,
            "toptier_agency": toptier_data
        }
        agency = Agency(data, mock_usa_client)
        
        toptier1 = agency.toptier_agency
        toptier2 = agency.toptier_agency
        
        assert toptier1 is toptier2  # Same instance (cached)
    
    def test_subtier_agency_property(self, mock_usa_client):
        """Test subtier agency property returns AgencyTier."""
        subtier_data = {
            "name": "National Aeronautics and Space Administration",
            "code": "8000",
            "abbreviation": "NASA"
        }
        data = {
            "id": 862,
            "subtier_agency": subtier_data
        }
        agency = Agency(data, mock_usa_client)
        
        subtier = agency.subtier_agency
        assert isinstance(subtier, AgencyTier)
        assert subtier.name == "National Aeronautics and Space Administration"
        assert subtier.code == "8000"
        assert subtier.abbreviation == "NASA"
    
    def test_subtier_agency_cached(self, mock_usa_client):
        """Test subtier agency property is cached."""
        subtier_data = {
            "name": "NASA",
            "code": "8000"
        }
        data = {
            "id": 862,
            "subtier_agency": subtier_data
        }
        agency = Agency(data, mock_usa_client)
        
        subtier1 = agency.subtier_agency
        subtier2 = agency.subtier_agency
        
        assert subtier1 is subtier2  # Same instance (cached)
    
    def test_toptier_agency_none(self, mock_usa_client):
        """Test toptier agency when not present."""
        data = {"id": 862}
        agency = Agency(data, mock_usa_client)
        
        assert agency.toptier_agency is None
    
    def test_subtier_agency_none(self, mock_usa_client):
        """Test subtier agency when not present."""
        data = {"id": 862}
        agency = Agency(data, mock_usa_client)
        
        assert agency.subtier_agency is None


class TestAgencyConvenienceProperties:
    """Test Agency convenience properties that prioritize toptier over subtier."""
    
    def test_name_property_prefers_toptier(self, mock_usa_client):
        """Test name property prefers toptier over subtier."""
        data = {
            "id": 862,
            "toptier_agency": {
                "name": "Toptier Name",
                "code": "080"
            },
            "subtier_agency": {
                "name": "Subtier Name",
                "code": "8000"
            }
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.name == "Toptier Name"
    
    def test_name_property_falls_back_to_subtier(self, mock_usa_client):
        """Test name property falls back to subtier when no toptier."""
        data = {
            "id": 862,
            "subtier_agency": {
                "name": "Subtier Name",
                "code": "8000"
            }
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.name == "Subtier Name"
    
    def test_name_property_falls_back_to_office_name(self, mock_usa_client):
        """Test name property falls back to office name when no tiers."""
        data = {
            "id": 862,
            "office_agency_name": "Office Name"
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.name == "Office Name"
    
    def test_code_property_prefers_toptier(self, mock_usa_client):
        """Test code property prefers toptier over subtier."""
        data = {
            "id": 862,
            "toptier_agency": {
                "name": "NASA",
                "code": "080"
            },
            "subtier_agency": {
                "name": "NASA",
                "code": "8000"
            }
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.code == "080"
    
    def test_code_property_falls_back_to_subtier(self, mock_usa_client):
        """Test code property falls back to subtier when no toptier."""
        data = {
            "id": 862,
            "subtier_agency": {
                "name": "NASA",
                "code": "8000"
            }
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.code == "8000"
    
    def test_code_property_none_when_no_tiers(self, mock_usa_client):
        """Test code property returns None when no tier data."""
        data = {
            "id": 862,
            "office_agency_name": "Office Name"
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.code is None
    
    def test_abbreviation_property_prefers_toptier(self, mock_usa_client):
        """Test abbreviation property prefers toptier over subtier."""
        data = {
            "id": 862,
            "toptier_agency": {
                "name": "NASA",
                "abbreviation": "NASA-TOP"
            },
            "subtier_agency": {
                "name": "NASA",
                "abbreviation": "NASA-SUB"
            }
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.abbreviation == "NASA-TOP"
    
    def test_abbreviation_property_falls_back_to_subtier(self, mock_usa_client):
        """Test abbreviation property falls back to subtier when no toptier."""
        data = {
            "id": 862,
            "subtier_agency": {
                "name": "NASA",
                "abbreviation": "NASA-SUB"
            }
        }
        agency = Agency(data, mock_usa_client)
        
        assert agency.abbreviation == "NASA-SUB"


class TestAgencyTierClass:
    """Test AgencyTier helper class."""
    
    def test_agency_tier_initialization(self):
        """Test AgencyTier initialization."""
        data = {
            "name": "National Aeronautics and Space Administration",
            "code": "080",
            "abbreviation": "NASA",
            "slug": "national-aeronautics-and-space-administration"
        }
        tier = AgencyTier(data)
        
        assert tier._data == data
        assert tier.name == "National Aeronautics and Space Administration"
        assert tier.code == "080"
        assert tier.abbreviation == "NASA"
        assert tier.slug == "national-aeronautics-and-space-administration"
    
    def test_agency_tier_properties_none(self):
        """Test AgencyTier properties when not present."""
        data = {}
        tier = AgencyTier(data)
        
        assert tier.name is None
        assert tier.code is None
        assert tier.abbreviation is None
        assert tier.slug is None
    
    def test_agency_tier_repr(self):
        """Test AgencyTier string representation."""
        data = {
            "name": "NASA",
            "code": "080"
        }
        tier = AgencyTier(data)
        
        repr_str = repr(tier)
        assert repr_str == "<AgencyTier 080: NASA>"
    
    def test_agency_tier_repr_with_missing_data(self):
        """Test AgencyTier string representation with missing data."""
        data = {"name": "NASA"}
        tier = AgencyTier(data)
        
        repr_str = repr(tier)
        assert repr_str == "<AgencyTier ?: NASA>"


class TestAgencyStringRepresentation:
    """Test Agency string representation."""
    
    def test_agency_repr_with_toptier(self, mock_usa_client):
        """Test Agency string representation with toptier data."""
        data = {
            "id": 862,
            "toptier_agency": {
                "name": "National Aeronautics and Space Administration",
                "code": "080"
            }
        }
        agency = Agency(data, mock_usa_client)
        
        repr_str = repr(agency)
        assert repr_str == "<Agency 080: National Aeronautics and Space Administration>"
    
    def test_agency_repr_with_subtier_only(self, mock_usa_client):
        """Test Agency string representation with subtier data only."""
        data = {
            "id": 862,
            "subtier_agency": {
                "name": "NASA",
                "code": "8000"
            }
        }
        agency = Agency(data, mock_usa_client)
        
        repr_str = repr(agency)
        assert repr_str == "<Agency 8000: NASA>"
    
    def test_agency_repr_with_office_name_only(self, mock_usa_client):
        """Test Agency string representation with office name only."""
        data = {
            "id": 862,
            "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER"
        }
        agency = Agency(data, mock_usa_client)
        
        repr_str = repr(agency)
        assert repr_str == "<Agency ?: NASA GODDARD SPACE FLIGHT CENTER>"
    
    def test_agency_repr_with_minimal_data(self, mock_usa_client):
        """Test Agency string representation with minimal data."""
        data = {"id": 862}
        agency = Agency(data, mock_usa_client)
        
        repr_str = repr(agency)
        assert repr_str == "<Agency ?: ?>"


class TestAgencyRealFixtureDataIntegration:
    """Test Agency with real fixture data."""
    
    def test_agency_with_contract_fixture_data(self, mock_usa_client):
        """Test Agency with real contract fixture agency data."""
        # This simulates the agency data structure from contract fixture
        agency_data = {
            "id": 862,
            "has_agency_page": True,
            "toptier_agency": {
                "name": "National Aeronautics and Space Administration",
                "code": "080",
                "abbreviation": "NASA",
                "slug": "national-aeronautics-and-space-administration"
            },
            "subtier_agency": {
                "name": "National Aeronautics and Space Administration",
                "code": "8000",
                "abbreviation": "NASA"
            },
            "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER"
        }
        
        agency = Agency(agency_data, mock_usa_client)
        
        # Test all properties work with real structure
        assert agency.id == 862
        assert agency.has_agency_page is True
        assert agency.name == "National Aeronautics and Space Administration"  # From toptier
        assert agency.code == "080"  # From toptier
        assert agency.abbreviation == "NASA"  # From toptier
        assert agency.office_agency_name == "NASA GODDARD SPACE FLIGHT CENTER"
        
        # Test tier objects
        assert isinstance(agency.toptier_agency, AgencyTier)
        assert isinstance(agency.subtier_agency, AgencyTier)
        assert agency.toptier_agency.slug == "national-aeronautics-and-space-administration"
        assert agency.subtier_agency.code == "8000"
    
    def test_agency_with_idv_fixture_data(self, mock_usa_client):
        """Test Agency with real IDV fixture agency data."""
        # This simulates the agency data structure from IDV fixture
        agency_data = {
            "id": 862,
            "has_agency_page": True,
            "toptier_agency": {
                "name": "National Aeronautics and Space Administration",
                "code": "080",
                "abbreviation": "NASA",
                "slug": "national-aeronautics-and-space-administration"
            },
            "subtier_agency": {
                "name": "National Aeronautics and Space Administration",
                "code": "8000",
                "abbreviation": "NASA"
            },
            "office_agency_name": "NASA JOHNSON SPACE CENTER"
        }
        
        agency = Agency(agency_data, mock_usa_client)
        
        # Test office name difference from contract fixture
        assert agency.office_agency_name == "NASA JOHNSON SPACE CENTER"
        # Other properties should be the same
        assert agency.id == 862
        assert agency.name == "National Aeronautics and Space Administration"
        assert agency.code == "080"