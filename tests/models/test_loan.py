"""Tests for Loan model functionality."""

from __future__ import annotations


from usaspending.models.loan import Loan
from usaspending.models.award import Award


class TestLoanInitialization:
    """Test Loan model initialization."""
    
    def test_init_with_dict_data(self, mock_usa_client):
        """Test Loan initialization with dictionary data."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123", 
            "description": "Test Loan",
            "category": "loan",
            "type": "07"
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan._data["generated_unique_award_id"] == "ASST_NON_LOAN_123"
        assert loan._data["description"] == "Test Loan"
        assert loan._client is not None
        assert isinstance(loan, Loan)
        assert isinstance(loan, Award)  # Should inherit from Award
    
    def test_init_with_string_id(self, mock_usa_client):
        """Test Loan initialization with string award ID."""
        award_id = "ASST_NON_LOAN_123"
        loan = Loan(award_id, mock_usa_client)
        
        assert loan._data["generated_unique_award_id"] == "ASST_NON_LOAN_123"
        assert loan._client is not None


class TestLoanTypeFields:
    """Test Loan TYPE_FIELDS are properly defined."""
    
    def test_type_fields_defined(self):
        """Test that Loan has TYPE_FIELDS defined."""
        assert hasattr(Loan, 'TYPE_FIELDS')
        assert isinstance(Loan.TYPE_FIELDS, list)
        
        expected_fields = [
            "fain",
            "uri", 
            "total_subsidy_cost",
            "total_loan_value",
            "cfda_info",
            "cfda_number",
            "primary_cfda_info",
            "sai_number"
        ]
        
        for field in expected_fields:
            assert field in Loan.TYPE_FIELDS
    
    def test_search_fields_defined(self):
        """Test that Loan has SEARCH_FIELDS defined."""
        assert hasattr(Loan, 'SEARCH_FIELDS') 
        assert isinstance(Loan.SEARCH_FIELDS, list)
        
        # Should include base fields plus loan-specific fields
        loan_specific = [
            "Issued Date",
            "Loan Value",
            "Subsidy Cost", 
            "SAI Number",
            "CFDA Number",
            "Assistance Listings",
            "primary_assistance_listing"
        ]
        
        for field in loan_specific:
            assert field in Loan.SEARCH_FIELDS


class TestLoanSpecificProperties:
    """Test loan-specific properties."""
    
    def test_fain_property(self, mock_usa_client):
        """Test FAIN property."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "fain": "07123456789"
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.fain == "07123456789"
    
    def test_fain_property_none(self, mock_usa_client):
        """Test FAIN property when not present."""
        data = {"generated_unique_award_id": "ASST_NON_LOAN_123"}
        loan = Loan(data, mock_usa_client)
        
        assert loan.fain is None
    
    def test_uri_property(self, mock_usa_client):
        """Test URI property."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "uri": "LOAN123XYZ"
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.uri == "LOAN123XYZ"
    
    def test_uri_property_none(self, mock_usa_client):
        """Test URI property when not present."""
        data = {"generated_unique_award_id": "ASST_NON_LOAN_123"}
        loan = Loan(data, mock_usa_client)
        
        assert loan.uri is None
    
    def test_total_subsidy_cost(self, mock_usa_client):
        """Test total subsidy cost property."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "total_subsidy_cost": 12500.00
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.total_subsidy_cost == 12500.00
        assert isinstance(loan.total_subsidy_cost, float)
    
    def test_total_subsidy_cost_none(self, mock_usa_client):
        """Test total subsidy cost when not present."""
        data = {"generated_unique_award_id": "ASST_NON_LOAN_123"}
        loan = Loan(data, mock_usa_client)
        
        assert loan.total_subsidy_cost is None
    
    def test_total_loan_value(self, mock_usa_client):
        """Test total loan value property."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "total_loan_value": 250000.00
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.total_loan_value == 250000.00
        assert isinstance(loan.total_loan_value, float)
    
    def test_total_loan_value_none(self, mock_usa_client):
        """Test total loan value when not present."""
        data = {"generated_unique_award_id": "ASST_NON_LOAN_123"}
        loan = Loan(data, mock_usa_client)
        
        assert loan.total_loan_value is None
    
    def test_cfda_number(self, mock_usa_client):
        """Test CFDA number property."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "cfda_number": "59.008"
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.cfda_number == "59.008"
    
    def test_cfda_number_search_results(self, mock_usa_client):
        """Test CFDA number from search results format."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "CFDA Number": "59.008"
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.cfda_number == "59.008"
    
    def test_cfda_info_property(self, mock_usa_client):
        """Test CFDA info array property."""
        cfda_data = [
            {
                "cfda_number": "59.008",
                "cfda_title": "Disaster Assistance Loans",
                "cfda_popular_name": "Disaster Loans"
            }
        ]
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "cfda_info": cfda_data
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.cfda_info == cfda_data
        assert len(loan.cfda_info) == 1
        assert loan.cfda_info[0]["cfda_number"] == "59.008"
    
    def test_cfda_info_search_results(self, mock_usa_client):
        """Test CFDA info from search results format."""
        cfda_data = [
            {
                "cfda_number": "59.008",
                "cfda_program_title": "Disaster Assistance Loans"
            }
        ]
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "Assistance Listings": cfda_data
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.cfda_info == cfda_data
        assert len(loan.cfda_info) == 1
        assert loan.cfda_info[0]["cfda_number"] == "59.008"
    
    def test_cfda_info_empty_default(self, mock_usa_client):
        """Test CFDA info defaults to empty list."""
        data = {"generated_unique_award_id": "ASST_NON_LOAN_123"}
        loan = Loan(data, mock_usa_client)
        
        assert loan.cfda_info == []
    
    def test_primary_cfda_info(self, mock_usa_client):
        """Test primary CFDA info property."""
        primary_data = {
            "cfda_number": "59.008",
            "cfda_program_title": "Disaster Assistance Loans"
        }
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "primary_cfda_info": primary_data
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.primary_cfda_info == primary_data
        assert loan.primary_cfda_info["cfda_number"] == "59.008"
    
    def test_primary_cfda_info_search_results(self, mock_usa_client):
        """Test primary CFDA info from search results format."""
        primary_data = {
            "cfda_number": "59.008",
            "cfda_program_title": "Disaster Assistance Loans"
        }
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "primary_assistance_listing": primary_data
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.primary_cfda_info == primary_data
    
    def test_sai_number(self, mock_usa_client):
        """Test SAI number property."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "sai_number": "SAI123456"
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.sai_number == "SAI123456"
    
    def test_sai_number_search_results(self, mock_usa_client):
        """Test SAI number from search results format."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "SAI Number": "SAI123456"
        }
        loan = Loan(data, mock_usa_client)
        
        assert loan.sai_number == "SAI123456"


class TestLoanWithRealFixtureData:
    """Test Loan model with real fixture data."""
    
    def test_loan_fixture_properties(self, mock_usa_client, loan_fixture_data):
        """Test Loan model with loan fixture data."""
        loan = Loan(loan_fixture_data, mock_usa_client)
        
        # Test basic properties
        assert loan.id == loan_fixture_data["id"]
        assert loan.fain == loan_fixture_data["fain"]
        assert loan.uri is None
        assert loan.category == loan_fixture_data["category"]
        assert loan.type == loan_fixture_data["type"]
        
        # Test loan-specific properties
        assert loan.total_subsidy_cost == loan_fixture_data["total_subsidy_cost"]
        assert loan.total_loan_value == loan_fixture_data["total_loan_value"]
        
        # Test CFDA info
        assert len(loan.cfda_info) == len(loan_fixture_data["cfda_info"])
        assert loan.cfda_info[0]["cfda_number"] == loan_fixture_data["cfda_info"][0]["cfda_number"]
        assert loan.cfda_info[0]["cfda_title"] == loan_fixture_data["cfda_info"][0]["cfda_title"]
        
        # Test that total_obligation is still accessible (inherited from Award)
        assert loan.total_obligation == loan_fixture_data["total_obligation"]