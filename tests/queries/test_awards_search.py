"""Tests for the AwardsSearch query builder."""

from __future__ import annotations

import datetime
from unittest.mock import Mock

import pytest

from usaspending.client import USASpending
from usaspending.config import Config
from usaspending.exceptions import ValidationError, APIError
from usaspending.models import Award
from usaspending.queries.awards_search import AwardsSearch
from usaspending.queries.filters import (
    AgencyTier,
    AgencyType,
    AwardAmount,
    AwardDateType,
    Location,
    LocationScope,
    CONTRACT_CODES,
    IDV_CODES,
    LOAN_CODES,
    GRANT_CODES,
)


@pytest.fixture
def mock_client():
    """Create a mock USASpending client for testing.
    
    This fixture is kept for backward compatibility with tests that
    only need simple mocking of _make_request.
    """
    config = Config(
        cache_backend="memory",
        rate_limit_calls=1000,
    )
    client = USASpending(config)
    client._make_request = Mock()
    return client


@pytest.fixture
def awards_search(mock_client):
    """Create an AwardsSearch instance with a mock client."""
    return AwardsSearch(mock_client)


class TestAwardsSearchInitialization:
    """Test initialization and basic properties of AwardsSearch."""

    def test_initialization(self, mock_client):
        """Test that AwardsSearch initializes correctly."""
        search = AwardsSearch(mock_client)
        assert search._client == mock_client
        assert search._filter_objects == []
        assert search._page_size == 100
        assert search._max_pages is None

    def test_endpoint(self, awards_search):
        """Test that the correct endpoint is returned."""
        assert awards_search._endpoint() == "/v2/search/spending_by_award/"

    def test_clone_immutability(self, awards_search):
        """Test that _clone creates a new instance with copied attributes."""
        # Add some filters first
        awards_search._filter_objects.append(Mock())
        awards_search._page_size = 50
        
        # Clone the search
        cloned = awards_search._clone()
        
        # Verify it's a different instance
        assert cloned is not awards_search
        assert cloned._filter_objects is not awards_search._filter_objects
        
        # But has same content
        assert len(cloned._filter_objects) == len(awards_search._filter_objects)
        assert cloned._page_size == awards_search._page_size


class TestFilterMethods:
    """Test all filter methods return new instances and apply filters correctly."""

    def test_with_keywords(self, awards_search):
        """Test the with_keywords filter method."""
        result = awards_search.with_keywords("NASA", "space", "research")
        
        # Should return new instance
        assert result is not awards_search
        assert len(result._filter_objects) == 1
        assert len(awards_search._filter_objects) == 0
        
        # Check filter content
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"keywords": ["NASA", "space", "research"]}

    def test_in_time_period(self, awards_search):
        """Test the in_time_period filter method."""
        start = datetime.date(2024, 1, 1)
        end = datetime.date(2024, 12, 31)
        
        result = awards_search.in_time_period(start, end, AwardDateType.ACTION_DATE)
        
        assert result is not awards_search
        assert len(result._filter_objects) == 1
        
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "time_period": [{
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "date_type": "action_date"
            }]
        }

    def test_for_fiscal_year(self, awards_search):
        """Test the for_fiscal_year filter method."""
        result = awards_search.for_fiscal_year(2024)
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        
        # FY2024 runs from Oct 1, 2023 to Sep 30, 2024
        assert filter_dict == {
            "time_period": [{
                "start_date": "2023-10-01",
                "end_date": "2024-09-30"
            }]
        }

    def test_with_place_of_performance_scope(self, awards_search):
        """Test the with_place_of_performance_scope filter method."""
        result = awards_search.with_place_of_performance_scope(LocationScope.DOMESTIC)
        
        assert len(result._filter_objects) == 1
        # The LocationScopeFilter stores the key as instance attribute
        filter_obj = result._filter_objects[0]
        assert filter_obj.key == "place_of_performance_scope"
        assert filter_obj.scope == LocationScope.DOMESTIC
        filter_dict = filter_obj.to_dict()
        assert filter_dict == {"place_of_performance_scope": "domestic"}

    def test_with_place_of_performance_locations(self, awards_search):
        """Test the with_place_of_performance_locations filter method."""
        loc1 = Location(country_code="USA", state_code="CA", city_name="Los Angeles")
        loc2 = Location(country_code="USA", state_code="TX")
        
        result = awards_search.with_place_of_performance_locations(loc1, loc2)
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "place_of_performance_locations": [
                {"country": "USA", "state": "CA", "city": "Los Angeles"},
                {"country": "USA", "state": "TX"}
            ]
        }

    def test_for_agency(self, awards_search):
        """Test the for_agency filter method."""
        result = awards_search.for_agency(
            "NASA",
            agency_type=AgencyType.AWARDING,
            tier=AgencyTier.TOPTIER
        )
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "agencies": [{
                "type": "awarding",
                "tier": "toptier",
                "name": "NASA"
            }]
        }

    def test_with_recipient_search_text(self, awards_search):
        """Test the with_recipient_search_text filter method."""
        result = awards_search.with_recipient_search_text("SpaceX", "123456789")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"recipient_search_text": ["SpaceX", "123456789"]}

    def test_with_recipient_scope(self, awards_search):
        """Test the with_recipient_scope filter method."""
        result = awards_search.with_recipient_scope(LocationScope.FOREIGN)
        
        assert len(result._filter_objects) == 1
        # The LocationScopeFilter stores the key as instance attribute
        filter_obj = result._filter_objects[0]
        assert filter_obj.key == "recipient_scope"
        assert filter_obj.scope == LocationScope.FOREIGN
        filter_dict = filter_obj.to_dict()
        assert filter_dict == {"recipient_scope": "foreign"}

    def test_with_recipient_locations(self, awards_search):
        """Test the with_recipient_locations filter method."""
        loc = Location(country_code="CAN", state_code="ON", city_name="Toronto")
        
        result = awards_search.with_recipient_locations(loc)
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "recipient_locations": [
                {"country": "CAN", "state": "ON", "city": "Toronto"}
            ]
        }

    def test_with_recipient_types(self, awards_search):
        """Test the with_recipient_types filter method."""
        result = awards_search.with_recipient_types("small_business", "minority_owned")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"recipient_type_names": ["small_business", "minority_owned"]}

    def test_with_award_types(self, awards_search):
        """Test the with_award_types filter method."""
        result = awards_search.with_award_types("A", "B", "C")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"award_type_codes": ["A", "B", "C"]}

    def test_with_award_ids(self, awards_search):
        """Test the with_award_ids filter method."""
        result = awards_search.with_award_ids("AWARD123", "AWARD456")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"award_ids": ["AWARD123", "AWARD456"]}

    def test_with_award_amounts(self, awards_search):
        """Test the with_award_amounts filter method."""
        amount1 = AwardAmount(lower_bound=1000000, upper_bound=5000000)
        amount2 = AwardAmount(lower_bound=10000000)
        
        result = awards_search.with_award_amounts(amount1, amount2)
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "award_amounts": [
                {"lower_bound": 1000000, "upper_bound": 5000000},
                {"lower_bound": 10000000}
            ]
        }

    def test_with_cfda_numbers(self, awards_search):
        """Test the with_cfda_numbers filter method."""
        result = awards_search.with_cfda_numbers("43.001", "43.002")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"program_numbers": ["43.001", "43.002"]}

    def test_with_naics_codes(self, awards_search):
        """Test the with_naics_codes filter method."""
        result = awards_search.with_naics_codes(
            require=["541511", "541512"],
            exclude=["541519"]
        )
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "naics_codes": {
                "require": [["541511"], ["541512"]],
                "exclude": [["541519"]]
            }
        }

    def test_with_psc_codes(self, awards_search):
        """Test the with_psc_codes filter method."""
        result = awards_search.with_psc_codes(
            require=[["R", "R4"], ["70"]],
            exclude=[["R", "R499"]]
        )
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "psc_codes": {
                "require": [["R", "R4"], ["70"]],
                "exclude": [["R", "R499"]]
            }
        }

    def test_with_contract_pricing_types(self, awards_search):
        """Test the with_contract_pricing_types filter method."""
        result = awards_search.with_contract_pricing_types("J", "K")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"contract_pricing_type_codes": ["J", "K"]}

    def test_with_set_aside_types(self, awards_search):
        """Test the with_set_aside_types filter method."""
        result = awards_search.with_set_aside_types("SBA", "8A")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"set_aside_type_codes": ["SBA", "8A"]}

    def test_with_extent_competed_types(self, awards_search):
        """Test the with_extent_competed_types filter method."""
        result = awards_search.with_extent_competed_types("A", "B")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"extent_competed_type_codes": ["A", "B"]}

    def test_with_tas_codes(self, awards_search):
        """Test the with_tas_codes filter method."""
        result = awards_search.with_tas_codes(
            require=[["080", "2022"], ["080", "2023"]],
            exclude=[["080", "2021"]]
        )
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "tas_codes": {
                "require": [["080", "2022"], ["080", "2023"]],
                "exclude": [["080", "2021"]]
            }
        }

    def test_with_treasury_account_components(self, awards_search):
        """Test the with_treasury_account_components filter method."""
        components = [
            {"aid": "080", "main": "0126"},
            {"aid": "080", "main": "0130"}
        ]
        
        result = awards_search.with_treasury_account_components(*components)
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {
            "treasury_account_components": [
                {"aid": "080", "main": "0126"},
                {"aid": "080", "main": "0130"}
            ]
        }

    def test_with_def_codes(self, awards_search):
        """Test the with_def_codes filter method."""
        result = awards_search.with_def_codes("L", "M", "N")
        
        assert len(result._filter_objects) == 1
        filter_dict = result._filter_objects[0].to_dict()
        assert filter_dict == {"def_codes": ["L", "M", "N"]}

    def test_method_chaining(self, awards_search):
        """Test that multiple filters can be chained together."""
        result = (awards_search
            .with_keywords("NASA")
            .for_fiscal_year(2024)
            .with_award_types("A", "B")
            .for_agency("NASA"))
        
        assert len(result._filter_objects) == 4
        assert result is not awards_search
        assert len(awards_search._filter_objects) == 0  # Original unchanged


class TestPayloadBuilding:
    """Test payload construction and validation."""

    def test_build_payload_basic(self, awards_search):
        """Test basic payload building with required filters."""
        search = awards_search.with_award_types("A", "B")
        
        payload = search._build_payload(page=1)
        
        assert payload["filters"] == {"award_type_codes": ["A", "B"]}
        # Verify base fields are included
        assert "Award ID" in payload["fields"]
        assert "Recipient Name" in payload["fields"]
        assert "Awarding Agency" in payload["fields"]
        assert len(payload["fields"]) > 20  # Should have many base fields
        assert payload["limit"] == 100
        assert payload["page"] == 1

    def test_build_payload_multiple_filters(self, awards_search):
        """Test payload building with multiple filters."""
        search = (awards_search
            .with_award_types("A")
            .with_keywords("test")
            .for_fiscal_year(2024))
        
        payload = search._build_payload(page=2)
        
        assert "award_type_codes" in payload["filters"]
        assert "keywords" in payload["filters"]
        assert "time_period" in payload["filters"]
        assert payload["page"] == 2

    def test_build_payload_missing_required_filter(self, awards_search):
        """Test that missing award_type_codes raises ValidationError."""
        search = awards_search.with_keywords("test")
        
        with pytest.raises(ValidationError) as exc_info:
            search._build_payload(page=1)
        
        assert "award_type_codes" in str(exc_info.value)

    def test_build_payload_aggregates_agency_filters(self, awards_search):
        """Test that multiple agency filters are aggregated into a single list."""
        search = (awards_search
            .with_award_types("A")
            .for_agency("NASA", AgencyType.AWARDING)
            .for_agency("DOD", AgencyType.FUNDING))
        
        payload = search._build_payload(page=1)
        
        assert len(payload["filters"]["agencies"]) == 2
        assert payload["filters"]["agencies"][0]["name"] == "NASA"
        assert payload["filters"]["agencies"][1]["name"] == "DOD"

    def test_build_payload_custom_page_size(self, awards_search):
        """Test payload with custom page size."""
        search = awards_search.with_award_types("A").page_size(50)
        
        payload = search._build_payload(page=1)
        
        assert payload["limit"] == 50

    def test_contract_fields_included(self, awards_search):
        """Test that contract-specific fields are included for contract types."""
        search = awards_search.with_award_types("A", "B")
        
        fields = search._get_fields()
        
        # Check contract-specific fields are present
        assert "Start Date" in fields
        assert "End Date" in fields
        assert "Award Amount" in fields
        assert "Total Outlays" in fields
        assert "Contract Award Type" in fields
        assert "NAICS" in fields
        assert "PSC" in fields
    
    def test_idv_fields_included(self, awards_search):
        """Test that IDV-specific fields are included for IDV types."""
        search = awards_search.with_award_types("IDV_A", "IDV_B")
        
        fields = search._get_fields()
        
        # Check IDV-specific fields are present
        assert "Start Date" in fields
        assert "Award Amount" in fields
        assert "Total Outlays" in fields
        assert "Contract Award Type" in fields
        assert "Last Date to Order" in fields
        assert "NAICS" in fields
        assert "PSC" in fields
        # Should not have End Date (IDV-specific difference)
    
    def test_loan_fields_included(self, awards_search):
        """Test that loan-specific fields are included for loan types."""
        search = awards_search.with_award_types("07", "08")
        
        fields = search._get_fields()
        
        # Check loan-specific fields are present
        assert "Issued Date" in fields
        assert "Loan Value" in fields
        assert "Subsidy Cost" in fields
        assert "SAI Number" in fields
        assert "CFDA Number" in fields
        assert "Assistance Listings" in fields
        assert "primary_assistance_listing" in fields
    
    def test_assistance_fields_included(self, awards_search):
        """Test that assistance-specific fields are included for assistance types."""
        search = awards_search.with_award_types("02", "03", "04")
        
        fields = search._get_fields()
        
        # Check assistance-specific fields are present
        assert "Start Date" in fields
        assert "End Date" in fields
        assert "Award Amount" in fields
        assert "Total Outlays" in fields
        assert "Award Type" in fields
        assert "SAI Number" in fields
        assert "CFDA Number" in fields
        assert "Assistance Listings" in fields
        assert "primary_assistance_listing" in fields
    
    def test_mixed_award_types_fields_now_forbidden(self, awards_search):
        """Test that mixing award types from different categories is now forbidden."""
        # This should raise a ValidationError due to our new validation
        with pytest.raises(ValidationError, match="Cannot mix different award type categories"):
            awards_search.with_award_types("A", "07")  # Contract + Loan
    
    def test_no_award_types_base_fields_only(self, awards_search):
        """Test that only base fields are returned when no award types specified."""
        # Don't set award types, but access fields directly
        fields = awards_search._get_fields()
        
        # Should only have base fields
        assert "Award ID" in fields
        assert "Recipient Name" in fields
        assert "Awarding Agency" in fields
        
        # Should not have type-specific fields
        assert "Contract Award Type" not in fields
        assert "Loan Value" not in fields
        assert "Last Date to Order" not in fields


class TestAwardTypeHelperMethods:
    """Test the helper methods for award types."""
    
    def test_contracts_helper(self, awards_search):
        """Test the contracts() helper method."""
        search = awards_search.contracts()
        
        award_types = search._get_award_type_codes()
        assert award_types == CONTRACT_CODES
        
        # Should include contract-specific fields
        fields = search._get_fields()
        assert "Contract Award Type" in fields
        assert "NAICS" in fields
        assert "PSC" in fields
    
    def test_idvs_helper(self, awards_search):
        """Test the idvs() helper method."""
        search = awards_search.idvs()
        
        award_types = search._get_award_type_codes()
        assert award_types == IDV_CODES
        
        # Should include IDV-specific fields
        fields = search._get_fields()
        assert "Last Date to Order" in fields
        assert "Contract Award Type" in fields
        assert "NAICS" in fields
    
    def test_loans_helper(self, awards_search):
        """Test the loans() helper method."""
        search = awards_search.loans()
        
        award_types = search._get_award_type_codes()
        assert award_types == LOAN_CODES
        
        # Should include loan-specific fields
        fields = search._get_fields()
        assert "Loan Value" in fields
        assert "Subsidy Cost" in fields
        assert "CFDA Number" in fields
    
    def test_grants_helper(self, awards_search):
        """Test the grants() helper method."""
        search = awards_search.grants()
        
        award_types = search._get_award_type_codes()
        assert award_types == GRANT_CODES
        
        # Should include grant-specific fields
        fields = search._get_fields()
        assert "Award Type" in fields
        assert "CFDA Number" in fields
        assert "Assistance Listings" in fields


class TestAwardTypeValidation:
    """Test validation of award type categories."""
    
    def test_single_category_contracts_allowed(self, awards_search):
        """Test that multiple codes within contract category are allowed."""
        search = awards_search.with_award_types("A", "B", "C")
        
        # Should not raise an error
        award_types = search._get_award_type_codes()
        assert award_types == {"A", "B", "C"}
    
    def test_single_category_grants_allowed(self, awards_search):
        """Test that multiple codes within grant category are allowed."""
        search = awards_search.with_award_types("02", "03", "04")
        
        # Should not raise an error
        award_types = search._get_award_type_codes()
        assert award_types == {"02", "03", "04"}
    
    def test_mixing_contracts_and_loans_forbidden(self, awards_search):
        """Test that mixing contracts and loans raises ValidationError."""
        with pytest.raises(ValidationError, match="Cannot mix different award type categories"):
            awards_search.with_award_types("A", "07")
    
    def test_mixing_idvs_and_grants_forbidden(self, awards_search):
        """Test that mixing IDVs and grants raises ValidationError."""
        with pytest.raises(ValidationError, match="Cannot mix different award type categories"):
            awards_search.with_award_types("IDV_A", "02")
    
    def test_chaining_different_categories_forbidden(self, awards_search):
        """Test that chaining different categories is forbidden."""
        # First set contracts
        search = awards_search.contracts()
        
        # Then try to add loans - should fail
        with pytest.raises(ValidationError, match="Cannot mix different award type categories"):
            search.with_award_types("07")
    
    def test_helper_methods_cannot_be_mixed(self, awards_search):
        """Test that helper methods cannot be chained with different types."""
        # First use contracts
        search = awards_search.contracts()
        
        # Then try to add loans via helper - should fail
        with pytest.raises(ValidationError, match="Cannot mix different award type categories"):
            search.loans()
    
    def test_adding_same_category_allowed(self, awards_search):
        """Test that adding more codes from the same category is allowed."""
        # Start with some contracts
        search = awards_search.with_award_types("A", "B")
        
        # Add more contracts - should be allowed (validation should pass)
        search2 = search.with_award_types("C", "D")
        
        # The search should have two separate award_type_codes filters
        # When building the payload, they should be combined
        payload = search2._build_payload(page=1)
        combined_types = set(payload["filters"]["award_type_codes"])
        
        # Should have all four types combined
        assert combined_types == {"A", "B", "C", "D"}
    
    def test_contracts_helper_after_contracts_allowed(self, awards_search):
        """Test that using contracts() after setting contract codes is allowed."""
        # Start with some contract codes
        search = awards_search.with_award_types("A", "B")
        
        # Use contracts() helper - should work since same category
        search2 = search.contracts()
        
        # Should combine the original codes with all contract codes
        payload = search2._build_payload(page=1)
        combined_types = set(payload["filters"]["award_type_codes"])
        
        # Should have all contract codes (original A,B plus all from CONTRACT_CODES)
        assert combined_types == CONTRACT_CODES


class TestTransformResult:
    """Test result transformation."""

    def test_transform_result(self, mock_usa_client):
        """Test that _transform_result creates Award instances."""
        # Set up a single award
        award_data = {"Award ID": "123", "Recipient Name": "Test Corp"}
        mock_usa_client.mock_award_search([award_data])
        
        # Get the award through the query
        search = mock_usa_client.awards.search().with_award_types("A")
        award = search.first()
        
        assert isinstance(award, Award)
        assert award._data["Award ID"] == "123"
        assert award._data["Recipient Name"] == "Test Corp"


class TestPaginationAndIteration:
    """Test pagination functionality."""

    def test_iteration_single_page(self, mock_usa_client):
        """Test iteration with a single page of results."""
        # Set up mock response
        awards = [
            {"Award ID": "1", "Recipient Name": "Corp 1"},
            {"Award ID": "2", "Recipient Name": "Corp 2"}
        ]
        mock_usa_client.mock_award_search(awards)
        
        search = mock_usa_client.awards.search().with_award_types("A")
        results = list(search)
        
        assert len(results) == 2
        assert all(isinstance(r, Award) for r in results)
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 1

    def test_iteration_multiple_pages(self, mock_usa_client):
        """Test iteration with multiple pages."""
        # Create 250 awards that will be automatically paginated
        awards = [{"Award ID": f"{i}"} for i in range(1, 251)]
        mock_usa_client.mock_award_search(awards, page_size=100)
        
        search = mock_usa_client.awards.search().with_award_types("A")
        results = list(search)
        
        assert len(results) == 250
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 3

    def test_iteration_with_max_pages(self, mock_usa_client):
        """Test iteration respects max_pages limit."""
        # Create 300 awards but limit to 2 pages
        awards = [{"Award ID": f"{i}"} for i in range(300)]
        mock_usa_client.mock_award_search(awards, page_size=100)
        
        search = mock_usa_client.awards.search().with_award_types("A").max_pages(2)
        results = list(search)
        
        assert len(results) == 200
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 2

    def test_first_method(self, mock_usa_client):
        """Test the first() method returns only the first result."""
        awards = [
            {"Award ID": "1", "Recipient Name": "Corp 1"},
            {"Award ID": "2", "Recipient Name": "Corp 2"}
        ]
        mock_usa_client.mock_award_search(awards)
        
        search = mock_usa_client.awards.search().with_award_types("A")
        result = search.first()
        
        assert isinstance(result, Award)
        assert result._data["Award ID"] == "1"
        # Verify the request was made correctly
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 1

    def test_first_method_no_results(self, mock_usa_client):
        """Test first() returns None when no results."""
        mock_usa_client.mock_award_search([])  # Empty results
        
        search = mock_usa_client.awards.search().with_award_types("A")
        result = search.first()
        
        assert result is None

    def test_all_method(self, mock_usa_client):
        """Test the all() method returns all results as a list."""
        awards = [
            {"Award ID": "1"},
            {"Award ID": "2"},
            {"Award ID": "3"}
        ]
        mock_usa_client.mock_award_search(awards)
        
        search = mock_usa_client.awards.search().with_award_types("A")
        results = search.all()
        
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, Award) for r in results)

    def test_count_method_contracts(self, mock_usa_client):
        """Test the count() method for contract awards."""
        # Mock response with structured count format
        mock_usa_client.mock_award_count(
            contracts=3287,
            direct_payments=0,
            grants=7821,
            idvs=105,
            loans=0,
            other=0
        )
        
        search = mock_usa_client.awards.search().with_award_types("A")
        count = search.count()
        
        assert count == 3287
        
        # Verify the correct endpoint was called
        mock_usa_client.assert_called_with(
            endpoint="/v2/search/spending_by_award_count/",
            method="POST"
        )
    
    def test_count_method_grants(self, mock_usa_client):
        """Test the count() method for grant awards."""
        mock_usa_client.mock_award_count(
            contracts=3287,
            direct_payments=0,
            grants=7821,
            idvs=105,
            loans=0,
            other=0
        )
        
        search = mock_usa_client.awards.search().with_award_types("02", "03")
        count = search.count()
        
        assert count == 7821
    
    def test_count_method_idvs(self, mock_usa_client):
        """Test the count() method for IDV awards."""
        mock_usa_client.mock_award_count(
            contracts=3287,
            direct_payments=0,
            grants=7821,
            idvs=105,
            loans=0,
            other=0
        )
        
        search = mock_usa_client.awards.search().with_award_types("IDV_A")
        count = search.count()
        
        assert count == 105
    
    def test_count_method_loans(self, mock_usa_client):
        """Test the count() method for loan awards."""
        mock_usa_client.mock_award_count(
            contracts=3287,
            direct_payments=0,
            grants=7821,
            idvs=105,
            loans=42,
            other=0
        )
        
        search = mock_usa_client.awards.search().with_award_types("07")
        count = search.count()
        
        assert count == 42
    
    def test_count_method_direct_payments(self, mock_usa_client):
        """Test the count() method for direct payment awards."""
        mock_usa_client.mock_award_count(
            contracts=3287,
            direct_payments=123,
            grants=7821,
            idvs=105,
            loans=0,
            other=0
        )
        
        search = mock_usa_client.awards.search().with_award_types("06")
        count = search.count()
        
        assert count == 123
    
    def test_count_method_other(self, mock_usa_client):
        """Test the count() method for other assistance awards."""
        mock_usa_client.mock_award_count(
            contracts=3287,
            direct_payments=0,
            grants=7821,
            idvs=105,
            loans=0,
            other=89
        )
        
        search = mock_usa_client.awards.search().with_award_types("09")
        count = search.count()
        
        assert count == 89
    
    def test_count_method_convenience_methods(self, mock_usa_client):
        """Test the count() method with convenience methods."""
        mock_usa_client.mock_award_count(
            contracts=3287,
            direct_payments=123,
            grants=7821,
            idvs=105,
            loans=42,
            other=89
        )
        
        # Test each convenience method
        assert mock_usa_client.awards.search().contracts().count() == 3287
        assert mock_usa_client.awards.search().grants().count() == 7821
        assert mock_usa_client.awards.search().idvs().count() == 105
        assert mock_usa_client.awards.search().loans().count() == 42
        assert mock_usa_client.awards.search().direct_payments().count() == 123
        assert mock_usa_client.awards.search().other().count() == 89
        
        # Verify 6 calls were made (one for each convenience method)
        assert mock_usa_client.get_request_count("/v2/search/spending_by_award_count/") == 6
    
    def test_count_method_missing_category(self, mock_usa_client):
        """Test count() method when category is missing from response."""
        # Only provide some categories
        mock_usa_client.mock_award_count(
            contracts=3287,
            grants=7821
            # Missing other categories
        )
        
        search = mock_usa_client.awards.search().with_award_types("07")  # loans
        count = search.count()
        
        # Should return 0 when category is missing
        assert count == 0
    
    def test_count_method_requires_award_types(self, mock_usa_client):
        """Test that count() method requires award types to be set."""
        # Try to call count() without setting award types
        with pytest.raises(ValidationError) as exc_info:
            mock_usa_client.awards.search().count()
        
        assert "award_type_codes" in str(exc_info.value)
        assert "required" in str(exc_info.value)


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_api_error_propagation(self, mock_usa_client):
        """Test that API errors are propagated correctly."""
        # Set up error response
        mock_usa_client.set_error_response(
            "/v2/search/spending_by_award/",
            error_code=400,
            detail="Bad request"
        )
        
        search = mock_usa_client.awards.search().with_award_types("A")
        
        with pytest.raises(APIError):
            list(search)

    def test_empty_award_types_filter(self, awards_search):
        """Test that empty award types raises appropriate error."""
        # This should work but payload building should fail
        search = awards_search.with_award_types()  # No types provided
        
        # Filter should still be added, just empty
        assert len(search._filter_objects) == 1
        
        # But building payload should fail
        with pytest.raises(ValidationError):
            search._build_payload(1)


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    def test_nasa_contracts_fy2024(self, mock_usa_client):
        """Test a realistic query for NASA contracts in FY2024."""
        awards = [{
            "Award ID": "80NSSC24CA001",
            "Recipient Name": "SpaceX",
            "Award Amount": 2500000000,
            "Awarding Agency": "NASA"
        }]
        mock_usa_client.mock_award_search(awards)
        
        search = (mock_usa_client.awards.search()
            .with_award_types("A", "B", "C", "D")
            .for_agency("NASA", AgencyType.AWARDING)
            .for_fiscal_year(2024)
            .with_keywords("space", "launch"))
        
        results = list(search)
        
        # Verify the request was made with correct filters
        last_request = mock_usa_client.get_last_request("/v2/search/spending_by_award/")
        payload = last_request["json"]
        
        assert "award_type_codes" in payload["filters"]
        assert "agencies" in payload["filters"]
        assert "time_period" in payload["filters"]
        assert "keywords" in payload["filters"]
        
        assert len(results) == 1
        assert isinstance(results[0], Award)

    def test_small_business_grants(self, mock_usa_client):
        """Test query for small business grants with location filters."""
        mock_usa_client.mock_award_search([])  # Empty results
        
        ca_location = Location(country_code="USA", state_code="CA")
        
        search = (mock_usa_client.awards.search()
            .with_award_types("02", "03", "04", "05")  # Grant types
            .with_recipient_types("small_business")
            .with_recipient_locations(ca_location)
            .with_award_amounts(
                AwardAmount(lower_bound=100000, upper_bound=500000)
            ))
        
        _ = search.all()
        
        # Verify filters were applied using request tracking
        last_request = mock_usa_client.get_last_request("/v2/search/spending_by_award/")
        payload = last_request["json"]
        assert payload["filters"]["recipient_type_names"] == ["small_business"]
        assert payload["filters"]["recipient_locations"] == [{"country": "USA", "state": "CA"}]
        assert len(payload["filters"]["award_amounts"]) == 1