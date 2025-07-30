"""Tests for Grant model functionality."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from usaspending.models.grant import Grant
from usaspending.models.award import Award
from usaspending.exceptions import ValidationError


class TestGrantInitialization:
    """Test Grant model initialization."""
    
    def test_init_with_dict_data(self, mock_usa_client):
        """Test Grant initialization with dictionary data."""
        data = {
            "generated_unique_award_id": "ASST_NON_123", 
            "description": "Test Grant",
            "category": "grant",
            "type": "05"
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant._data["generated_unique_award_id"] == "ASST_NON_123"
        assert grant._data["description"] == "Test Grant"
        assert grant._client is not None
        assert isinstance(grant, Grant)
        assert isinstance(grant, Award)  # Should inherit from Award
    
    def test_init_with_string_id(self, mock_usa_client):
        """Test Grant initialization with string award ID."""
        award_id = "ASST_NON_123"
        grant = Grant(award_id, mock_usa_client)
        
        assert grant._data["generated_unique_award_id"] == "ASST_NON_123"
        assert grant._client is not None


class TestGrantTypeFields:
    """Test Grant TYPE_FIELDS are properly defined."""
    
    def test_type_fields_defined(self):
        """Test that Grant has TYPE_FIELDS defined."""
        assert hasattr(Grant, 'TYPE_FIELDS')
        assert isinstance(Grant.TYPE_FIELDS, list)
        
        expected_fields = [
            "fain",
            "uri",
            "record_type",
            "cfda_info",
            "cfda_number",
            "primary_cfda_info",
            "sai_number",
            "funding_opportunity",
            "non_federal_funding",
            "total_funding",
            "transaction_obligated_amount"
        ]
        
        for field in expected_fields:
            assert field in Grant.TYPE_FIELDS
    
    def test_search_fields_defined(self):
        """Test that Grant has SEARCH_FIELDS defined."""
        assert hasattr(Grant, 'SEARCH_FIELDS') 
        assert isinstance(Grant.SEARCH_FIELDS, list)
        
        # Should include base fields plus grant-specific fields
        grant_specific = [
            "Start Date",
            "End Date",
            "Award Amount",
            "Total Outlays",
            "Award Type",
            "SAI Number", 
            "CFDA Number",
            "Assistance Listings",
            "primary_assistance_listing"
        ]
        
        for field in grant_specific:
            assert field in Grant.SEARCH_FIELDS


class TestGrantSpecificProperties:
    """Test grant-specific properties."""
    
    def test_fain_property(self, mock_usa_client):
        """Test FAIN property."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "fain": "NNM11AA01A"
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.fain == "NNM11AA01A"
    
    def test_fain_property_none(self, mock_usa_client):
        """Test FAIN property when not present."""
        data = {"generated_unique_award_id": "ASST_NON_123"}
        grant = Grant(data, mock_usa_client)
        
        assert grant.fain is None
    
    def test_uri_property(self, mock_usa_client):
        """Test URI property."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "uri": "ABC123XYZ"
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.uri == "ABC123XYZ"
    
    def test_uri_property_none(self, mock_usa_client):
        """Test URI property when not present."""
        data = {"generated_unique_award_id": "ASST_NON_123"}
        grant = Grant(data, mock_usa_client)
        
        assert grant.uri is None
    
    def test_record_type_property(self, mock_usa_client):
        """Test record type property."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "record_type": 2
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.record_type == 2
        assert isinstance(grant.record_type, int)
    
    def test_record_type_none(self, mock_usa_client):
        """Test record type when not present."""
        data = {"generated_unique_award_id": "ASST_NON_123"}
        grant = Grant(data, mock_usa_client)
        
        assert grant.record_type is None
    
    def test_cfda_number(self, mock_usa_client):
        """Test CFDA number property."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "cfda_number": "43.008"
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.cfda_number == "43.008"
    
    def test_cfda_number_search_results(self, mock_usa_client):
        """Test CFDA number from search results format."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "CFDA Number": "43.008"
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.cfda_number == "43.008"
    
    def test_cfda_info_property(self, mock_usa_client):
        """Test CFDA info array property."""
        cfda_data = [
            {
                "cfda_number": "43.008",
                "cfda_title": "Office of Stem Engagement (OSTEM)",
                "cfda_popular_name": "OSTEM"
            },
            {
                "cfda_number": "43.001",
                "cfda_title": "Science",
                "cfda_popular_name": "SMD"
            }
        ]
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "cfda_info": cfda_data
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.cfda_info == cfda_data
        assert len(grant.cfda_info) == 2
        assert grant.cfda_info[0]["cfda_number"] == "43.008"
    
    def test_cfda_info_search_results(self, mock_usa_client):
        """Test CFDA info from search results format."""
        cfda_data = [
            {
                "cfda_number": "43.008",
                "cfda_program_title": "Office of Stem Engagement (OSTEM)"
            }
        ]
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "Assistance Listings": cfda_data
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.cfda_info == cfda_data
        assert len(grant.cfda_info) == 1
        assert grant.cfda_info[0]["cfda_number"] == "43.008"
    
    def test_cfda_info_empty_default(self, mock_usa_client):
        """Test CFDA info defaults to empty list."""
        data = {"generated_unique_award_id": "ASST_NON_123"}
        grant = Grant(data, mock_usa_client)
        
        assert grant.cfda_info == []
    
    def test_primary_cfda_info(self, mock_usa_client):
        """Test primary CFDA info property."""
        primary_data = {
            "cfda_number": "43.008",
            "cfda_program_title": "Office of Stem Engagement (OSTEM)"
        }
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "primary_cfda_info": primary_data
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.primary_cfda_info == primary_data
        assert grant.primary_cfda_info["cfda_number"] == "43.008"
    
    def test_primary_cfda_info_search_results(self, mock_usa_client):
        """Test primary CFDA info from search results format."""
        primary_data = {
            "cfda_number": "43.008",
            "cfda_program_title": "Office of Stem Engagement (OSTEM)"
        }
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "primary_assistance_listing": primary_data
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.primary_cfda_info == primary_data
    
    def test_sai_number(self, mock_usa_client):
        """Test SAI number property."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "sai_number": "SAI EXEMPT"
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.sai_number == "SAI EXEMPT"
    
    def test_sai_number_search_results(self, mock_usa_client):
        """Test SAI number from search results format."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "SAI Number": "SAI EXEMPT"
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.sai_number == "SAI EXEMPT"


class TestGrantFinancialProperties:
    """Test grant-specific financial properties."""
    
    def test_non_federal_funding(self, mock_usa_client):
        """Test non-federal funding property."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "non_federal_funding": 50000.0
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.non_federal_funding == 50000.0
        assert isinstance(grant.non_federal_funding, float)
    
    def test_non_federal_funding_none(self, mock_usa_client):
        """Test non-federal funding when not present."""
        data = {"generated_unique_award_id": "ASST_NON_123"}
        grant = Grant(data, mock_usa_client)
        
        assert grant.non_federal_funding is None
    
    def test_total_funding(self, mock_usa_client):
        """Test total funding property."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "total_funding": 156725919.62
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.total_funding == 156725919.62
        assert isinstance(grant.total_funding, float)
    
    def test_transaction_obligated_amount(self, mock_usa_client):
        """Test transaction obligated amount property."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "transaction_obligated_amount": 83852595.67
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.transaction_obligated_amount == 83852595.67
        assert isinstance(grant.transaction_obligated_amount, float)


class TestGrantCachedProperties:
    """Test grant cached properties."""
    
    def test_funding_opportunity_property(self, mock_usa_client):
        """Test funding opportunity property."""
        opportunity_data = {
            "number": "NASA-12345",
            "goals": "Space research objectives"
        }
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "funding_opportunity": opportunity_data
        }
        grant = Grant(data, mock_usa_client)
        
        assert grant.funding_opportunity == opportunity_data
        assert grant.funding_opportunity["number"] == "NASA-12345"
    
    def test_funding_opportunity_none(self, mock_usa_client):
        """Test funding opportunity when not present."""
        data = {"generated_unique_award_id": "ASST_NON_123"}
        grant = Grant(data, mock_usa_client)
        
        assert grant.funding_opportunity is None


class TestGrantWithRealFixtureData:
    """Test Grant model with real fixture data."""
    
    def test_grant_fixture_properties(self, mock_usa_client, grant_fixture_data):
        """Test Grant model with grant fixture data."""
        grant = Grant(grant_fixture_data, mock_usa_client)
        
        # Test basic properties
        assert grant.id == grant_fixture_data["id"]
        assert grant.fain == grant_fixture_data["fain"]
        assert grant.uri == grant_fixture_data["uri"]
        assert grant.category == grant_fixture_data["category"]
        assert grant.type == grant_fixture_data["type"]
        
        # Test grant-specific properties
        assert grant.record_type == grant_fixture_data["record_type"]
        assert grant.non_federal_funding == grant_fixture_data["non_federal_funding"]
        assert grant.total_funding == grant_fixture_data["total_funding"]
        assert grant.transaction_obligated_amount == grant_fixture_data["transaction_obligated_amount"]
        
        # Test CFDA info
        assert len(grant.cfda_info) == len(grant_fixture_data["cfda_info"])
        assert grant.cfda_info[0]["cfda_number"] == grant_fixture_data["cfda_info"][0]["cfda_number"]
        assert grant.cfda_info[1]["cfda_number"] == grant_fixture_data["cfda_info"][1]["cfda_number"]
        
        # Test funding opportunity
        assert grant.funding_opportunity is not None
        assert "number" in grant.funding_opportunity
        assert "goals" in grant.funding_opportunity