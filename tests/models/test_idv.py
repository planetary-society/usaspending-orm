"""Tests for IDV model functionality."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from usaspending.models.idv import IDV
from usaspending.models.award import Award
from usaspending.models.location import Location
from usaspending.exceptions import ValidationError


class TestIDVInitialization:
    """Test IDV model initialization."""
    
    def test_init_with_dict_data(self, mock_usa_client):
        """Test IDV initialization with dictionary data."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123", 
            "description": "Test IDV",
            "category": "idv",
            "type": "IDV_B_B"
        }
        idv = IDV(data, mock_usa_client)
        
        assert idv._data["generated_unique_award_id"] == "CONT_IDV_123"
        assert idv._data["description"] == "Test IDV"
        assert idv._client is not None
        assert isinstance(idv, IDV)
        assert isinstance(idv, Award)  # Should inherit from Award
    
    def test_init_with_string_id(self, mock_usa_client):
        """Test IDV initialization with string award ID."""
        award_id = "CONT_IDV_123"
        idv = IDV(award_id, mock_usa_client)
        
        assert idv._data["generated_unique_award_id"] == "CONT_IDV_123"
        assert idv._client is not None


class TestIDVTypeFields:
    """Test IDV TYPE_FIELDS are properly defined."""
    
    def test_type_fields_defined(self):
        """Test that IDV has TYPE_FIELDS defined."""
        assert hasattr(IDV, 'TYPE_FIELDS')
        assert isinstance(IDV.TYPE_FIELDS, list)
        
        expected_fields = [
            "piid",
            "base_and_all_options",
            "contract_award_type",
            "naics_code",
            "naics_description", 
            "naics_hierarchy",
            "psc_code",
            "psc_description",
            "psc_hierarchy",
            "latest_transaction_contract_data"
        ]
        
        for field in expected_fields:
            assert field in IDV.TYPE_FIELDS
    
    def test_search_fields_defined(self):
        """Test that IDV has SEARCH_FIELDS defined."""
        assert hasattr(IDV, 'SEARCH_FIELDS') 
        assert isinstance(IDV.SEARCH_FIELDS, list)
        
        # Should include base fields plus IDV-specific fields
        idv_specific = [
            "Start Date",
            "Award Amount", 
            "Total Outlays",
            "Contract Award Type",
            "Last Date to Order",
            "NAICS",
            "PSC"
        ]
        
        for field in idv_specific:
            assert field in IDV.SEARCH_FIELDS


class TestIDVSpecificProperties:
    """Test IDV-specific properties."""
    
    def test_piid_property(self, mock_usa_client):
        """Test PIID property."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "piid": "80JSC019C0012"
        }
        idv = IDV(data, mock_usa_client)
        
        assert idv.piid == "80JSC019C0012"
    
    def test_piid_property_none(self, mock_usa_client):
        """Test PIID property when not present."""
        data = {"generated_unique_award_id": "CONT_IDV_123"}
        idv = IDV(data, mock_usa_client)
        
        assert idv.piid is None
    
    def test_base_and_all_options(self, mock_usa_client):
        """Test base and all options property."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123", 
            "base_and_all_options": 10489314619.0
        }
        idv = IDV(data, mock_usa_client)
        
        assert idv.base_and_all_options == 10489314619.0
        assert isinstance(idv.base_and_all_options, float)
    
    def test_contract_award_type(self, mock_usa_client):
        """Test contract award type property."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "contract_award_type": "INDEFINITE DELIVERY / INDEFINITE QUANTITY"
        }
        idv = IDV(data, mock_usa_client)
        
        assert idv.contract_award_type == "INDEFINITE DELIVERY / INDEFINITE QUANTITY"
    
    def test_contract_award_type_search_results(self, mock_usa_client):
        """Test contract award type property from search results."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "Contract Award Type": "INDEFINITE DELIVERY / INDEFINITE QUANTITY"
        }
        idv = IDV(data, mock_usa_client)
        
        assert idv.contract_award_type == "INDEFINITE DELIVERY / INDEFINITE QUANTITY"
    
    def test_naics_properties(self, mock_usa_client):
        """Test NAICS code and description properties."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "naics": {
                "code": "541715",
                "description": "RESEARCH AND DEVELOPMENT IN THE PHYSICAL, ENGINEERING, AND LIFE SCIENCES"
            }
        }
        idv = IDV(data, mock_usa_client)
        
        assert idv.naics_code == "541715"
        assert idv.naics_description == "RESEARCH AND DEVELOPMENT IN THE PHYSICAL, ENGINEERING, AND LIFE SCIENCES"
    
    def test_naics_properties_search_results(self, mock_usa_client):
        """Test NAICS properties from search results format."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "NAICS": {
                "code": "541715",
                "description": "RESEARCH AND DEVELOPMENT IN THE PHYSICAL, ENGINEERING, AND LIFE SCIENCES"
            }
        }
        idv = IDV(data, mock_usa_client)
        
        assert idv.naics_code == "541715"
        assert idv.naics_description == "RESEARCH AND DEVELOPMENT IN THE PHYSICAL, ENGINEERING, AND LIFE SCIENCES"
    
    def test_psc_properties(self, mock_usa_client):
        """Test PSC code and description properties."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "psc": {
                "code": "1555",
                "description": "SPACE VEHICLES"
            }
        }
        idv = IDV(data, mock_usa_client)
        
        assert idv.psc_code == "1555"
        assert idv.psc_description == "SPACE VEHICLES"


class TestIDVCachedProperties:
    """Test IDV cached properties."""
    
    def test_latest_transaction_contract_data(self, mock_usa_client):
        """Test latest transaction contract data property."""
        contract_data = {
            "idv_type_description": "IDC",
            "type_of_idc_description": "INDEFINITE DELIVERY / INDEFINITE QUANTITY",
            "solicitation_identifier": "80JSC018R0014",
            "product_or_service_code": "1555",
            "naics": "541715"
        }
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "latest_transaction_contract_data": contract_data
        }
        idv = IDV(data, mock_usa_client)
        
        result = idv.latest_transaction_contract_data
        assert result == contract_data
        assert result["idv_type_description"] == "IDC"
        assert result["naics"] == "541715"
    
    def test_psc_hierarchy(self, mock_usa_client):
        """Test PSC hierarchy property."""
        psc_data = {
            "midtier_code": {
                "code": "15",
                "description": "AEROSPACE CRAFT AND STRUCTURAL COMPONENTS"
            },
            "base_code": {
                "code": "1555",
                "description": "SPACE VEHICLES"
            }
        }
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "psc_hierarchy": psc_data
        }
        idv = IDV(data, mock_usa_client)
        
        result = idv.psc_hierarchy
        assert result == psc_data
        assert result["midtier_code"]["code"] == "15"
        assert result["base_code"]["code"] == "1555"
    
    def test_naics_hierarchy(self, mock_usa_client):
        """Test NAICS hierarchy property."""
        naics_data = {
            "toptier_code": {
                "code": "54",
                "description": "Professional, Scientific, and Technical Services"
            },
            "base_code": {
                "code": "541715",
                "description": "Research and Development in the Physical, Engineering, and Life Sciences"
            }
        }
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "naics_hierarchy": naics_data
        }
        idv = IDV(data, mock_usa_client)
        
        result = idv.naics_hierarchy
        assert result == naics_data
        assert result["toptier_code"]["code"] == "54"
        assert result["base_code"]["code"] == "541715"


class TestIDVPlaceOfPerformance:
    """Test IDV place of performance behavior."""
    
    def test_place_of_performance_all_null(self, mock_usa_client):
        """Test that IDV with all null place of performance returns None."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "place_of_performance": {
                "location_country_code": None,
                "country_name": None,
                "county_code": None,
                "county_name": None,
                "city_name": None,
                "state_code": None,
                "state_name": None,
                "congressional_code": None,
                "zip4": None,
                "zip5": None,
                "address_line1": None,
                "address_line2": None,
                "address_line3": None,
                "foreign_province": None,
                "foreign_postal_code": None
            }
        }
        idv = IDV(data, mock_usa_client)
        
        # IDVs typically don't have place_of_performance
        assert idv.place_of_performance is None
    
    def test_place_of_performance_with_data(self, mock_usa_client):
        """Test IDV with actual place of performance data."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "place_of_performance": {
                "location_country_code": "USA",
                "country_name": "UNITED STATES",
                "state_code": "TX",
                "city_name": "HOUSTON"
            }
        }
        idv = IDV(data, mock_usa_client)
        
        location = idv.place_of_performance
        assert isinstance(location, Location)
        assert location.country_code == "USA"
        assert location.state_code == "TX"
    
    def test_place_of_performance_no_data(self, mock_usa_client):
        """Test IDV with no place of performance data."""
        data = {"generated_unique_award_id": "CONT_IDV_123"}
        idv = IDV(data, mock_usa_client)
        
        assert idv.place_of_performance is None


class TestIDVWithRealFixtureData:
    """Test IDV model with real fixture data."""
    
    def test_idv_fixture_properties(self, mock_usa_client, idv_fixture_data):
        """Test IDV model with IDV fixture data."""
        idv = IDV(idv_fixture_data, mock_usa_client)
        
        # Test basic properties
        assert idv.id == idv_fixture_data["id"]
        assert idv.piid == idv_fixture_data["piid"]
        assert idv.category == idv_fixture_data["category"]
        assert idv.type == idv_fixture_data["type"]
        
        # Test IDV-specific properties
        assert idv.base_and_all_options == idv_fixture_data["base_and_all_options"]
        assert idv.contract_award_type is None  # Not present in this fixture
        
        # Test classification data
        assert idv.latest_transaction_contract_data is not None
        assert idv.latest_transaction_contract_data["idv_type_description"] == idv_fixture_data["latest_transaction_contract_data"]["idv_type_description"]
        assert idv.latest_transaction_contract_data["solicitation_identifier"] == idv_fixture_data["latest_transaction_contract_data"]["solicitation_identifier"]
        
        # Test hierarchy data
        assert idv.psc_hierarchy is not None
        assert idv.psc_hierarchy["midtier_code"]["code"] == idv_fixture_data["psc_hierarchy"]["midtier_code"]["code"]
        assert idv.naics_hierarchy["base_code"]["code"] == idv_fixture_data["naics_hierarchy"]["base_code"]["code"]
        
        # Test that IDV has no place of performance (all values are null)
        assert idv.place_of_performance is None