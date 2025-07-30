"""Tests for Contract model functionality."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from usaspending.models.contract import Contract
from usaspending.models.award import Award
from usaspending.exceptions import ValidationError


class TestContractInitialization:
    """Test Contract model initialization."""
    
    def test_init_with_dict_data(self, mock_usa_client):
        """Test Contract initialization with dictionary data."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123", 
            "description": "Test Contract",
            "category": "contract",
            "type": "D"
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract._data["generated_unique_award_id"] == "CONT_AWD_123"
        assert contract._data["description"] == "Test Contract"
        assert contract._client is not None
        assert isinstance(contract, Contract)
        assert isinstance(contract, Award)  # Should inherit from Award
    
    def test_init_with_string_id(self, mock_usa_client):
        """Test Contract initialization with string award ID."""
        award_id = "CONT_AWD_123"
        contract = Contract(award_id, mock_usa_client)
        
        assert contract._data["generated_unique_award_id"] == "CONT_AWD_123"
        assert contract._client is not None


class TestContractTypeFields:
    """Test Contract TYPE_FIELDS are properly defined."""
    
    def test_type_fields_defined(self):
        """Test that Contract has TYPE_FIELDS defined."""
        assert hasattr(Contract, 'TYPE_FIELDS')
        assert isinstance(Contract.TYPE_FIELDS, list)
        
        expected_fields = [
            "piid",
            "base_exercised_options", 
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
            assert field in Contract.TYPE_FIELDS
    
    def test_search_fields_defined(self):
        """Test that Contract has SEARCH_FIELDS defined."""
        assert hasattr(Contract, 'SEARCH_FIELDS') 
        assert isinstance(Contract.SEARCH_FIELDS, list)
        
        # Should include base fields plus contract-specific fields
        contract_specific = [
            "Start Date",
            "End Date", 
            "Award Amount",
            "Total Outlays",
            "Contract Award Type",
            "NAICS",
            "PSC"
        ]
        
        for field in contract_specific:
            assert field in Contract.SEARCH_FIELDS


class TestContractSpecificProperties:
    """Test contract-specific properties."""
    
    def test_piid_property(self, mock_usa_client):
        """Test PIID property."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "piid": "80GSFC18C0008"
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.piid == "80GSFC18C0008"
    
    def test_piid_property_none(self, mock_usa_client):
        """Test PIID property when not present."""
        data = {"generated_unique_award_id": "CONT_AWD_123"}
        contract = Contract(data, mock_usa_client)
        
        assert contract.piid is None
    
    def test_base_exercised_options(self, mock_usa_client):
        """Test base exercised options property."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "base_exercised_options": 168657782.95
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.base_exercised_options == 168657782.95
        assert isinstance(contract.base_exercised_options, float)
    
    def test_base_and_all_options(self, mock_usa_client):
        """Test base and all options property."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123", 
            "base_and_all_options": 168657782.95
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.base_and_all_options == 168657782.95
        assert isinstance(contract.base_and_all_options, float)
    
    def test_contract_award_type(self, mock_usa_client):
        """Test contract award type property."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "contract_award_type": "DEFINITIVE CONTRACT"
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.contract_award_type == "DEFINITIVE CONTRACT"
    
    def test_contract_award_type_search_results(self, mock_usa_client):
        """Test contract award type property from search results."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "Contract Award Type": "DEFINITIVE CONTRACT"
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.contract_award_type == "DEFINITIVE CONTRACT"
    
    def test_naics_properties(self, mock_usa_client):
        """Test NAICS code and description properties."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "naics": {
                "code": "541713",
                "description": "RESEARCH AND DEVELOPMENT IN NANOTECHNOLOGY"
            }
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.naics_code == "541713"
        assert contract.naics_description == "RESEARCH AND DEVELOPMENT IN NANOTECHNOLOGY"
    
    def test_naics_properties_search_results(self, mock_usa_client):
        """Test NAICS properties from search results format."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "NAICS": {
                "code": "541713",
                "description": "RESEARCH AND DEVELOPMENT IN NANOTECHNOLOGY"
            }
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.naics_code == "541713"
        assert contract.naics_description == "RESEARCH AND DEVELOPMENT IN NANOTECHNOLOGY"
    
    def test_psc_properties(self, mock_usa_client):
        """Test PSC code and description properties."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "psc": {
                "code": "AR11",
                "description": "SPACE R&D SERVICES"
            }
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.psc_code == "AR11"
        assert contract.psc_description == "SPACE R&D SERVICES"
    
    def test_psc_properties_search_results(self, mock_usa_client):
        """Test PSC properties from search results format."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "PSC": {
                "code": "AR11",
                "description": "SPACE R&D SERVICES"
            }
        }
        contract = Contract(data, mock_usa_client)
        
        assert contract.psc_code == "AR11"
        assert contract.psc_description == "SPACE R&D SERVICES"


class TestContractCachedProperties:
    """Test contract cached properties."""
    
    def test_latest_transaction_contract_data(self, mock_usa_client):
        """Test latest transaction contract data property."""
        contract_data = {
            "solicitation_identifier": "NNH16ZDA005O",
            "type_of_contract_pricing": "S",
            "product_or_service_code": "AR11",
            "naics": "541713"
        }
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "latest_transaction_contract_data": contract_data
        }
        contract = Contract(data, mock_usa_client)
        
        result = contract.latest_transaction_contract_data
        assert result == contract_data
        assert result["solicitation_identifier"] == "NNH16ZDA005O"
        assert result["naics"] == "541713"
    
    def test_latest_transaction_contract_data_cached(self, mock_usa_client):
        """Test latest transaction contract data is cached."""
        contract_data = {"solicitation_identifier": "TEST123"}
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "latest_transaction_contract_data": contract_data
        }
        contract = Contract(data, mock_usa_client)
        
        result1 = contract.latest_transaction_contract_data
        result2 = contract.latest_transaction_contract_data
        
        assert result1 is result2  # Same instance (cached)
    
    def test_psc_hierarchy(self, mock_usa_client):
        """Test PSC hierarchy property."""
        psc_data = {
            "toptier_code": {
                "code": "A",
                "description": "RESEARCH AND DEVELOPMENT"
            },
            "base_code": {
                "code": "AR11",
                "description": "SPACE R&D SERVICES"
            }
        }
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "psc_hierarchy": psc_data
        }
        contract = Contract(data, mock_usa_client)
        
        result = contract.psc_hierarchy
        assert result == psc_data
        assert result["toptier_code"]["code"] == "A"
        assert result["base_code"]["code"] == "AR11"
    
    def test_naics_hierarchy(self, mock_usa_client):
        """Test NAICS hierarchy property."""
        naics_data = {
            "toptier_code": {
                "code": "54",
                "description": "Professional, Scientific, and Technical Services"
            },
            "base_code": {
                "code": "541713",
                "description": "Research and Development in Nanotechnology"
            }
        }
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "naics_hierarchy": naics_data
        }
        contract = Contract(data, mock_usa_client)
        
        result = contract.naics_hierarchy
        assert result == naics_data
        assert result["toptier_code"]["code"] == "54"
        assert result["base_code"]["code"] == "541713"


class TestContractWithRealFixtureData:
    """Test Contract model with real fixture data."""
    
    def test_contract_fixture_properties(self, mock_usa_client, contract_fixture_data):
        """Test Contract model with contract fixture data."""
        contract = Contract(contract_fixture_data, mock_usa_client)
        
        # Test basic properties
        assert contract.id == 111952974
        assert contract.piid == "80GSFC18C0008"
        assert contract.category == "contract"
        assert contract.type == "D"
        
        # Test contract-specific properties
        assert contract.base_exercised_options == 168657782.95
        assert contract.base_and_all_options == 168657782.95
        
        # Test classification data
        assert contract.latest_transaction_contract_data is not None
        assert contract.latest_transaction_contract_data["solicitation_identifier"] == "NNH16ZDA005O"
        
        # Test hierarchy data
        assert contract.psc_hierarchy is not None
        assert contract.psc_hierarchy["toptier_code"]["code"] == "A"
        assert contract.naics_hierarchy["base_code"]["code"] == "541713"