"""Tests for the AwardsSearch query builder."""

from __future__ import annotations

import datetime
from unittest.mock import Mock

import pytest

from usaspending.client import USASpending
from usaspending.config import Config
from usaspending.exceptions import ValidationError
from usaspending.models import Award
from usaspending.queries.awards_search import AwardsSearch
from usaspending.queries.filters import (
    AgencyTier,
    AgencyType,
    AwardAmount,
    AwardDateType,
    Location,
    LocationScope,
)


@pytest.fixture
def mock_client():
    """Create a mock USASpending client for testing."""
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
        assert search._limit == 100
        assert search._max_pages is None

    def test_endpoint(self, awards_search):
        """Test that the correct endpoint is returned."""
        assert awards_search._endpoint() == "/api/v2/search/spending_by_award/"

    def test_clone_immutability(self, awards_search):
        """Test that _clone creates a new instance with copied attributes."""
        # Add some filters first
        awards_search._filter_objects.append(Mock())
        awards_search._limit = 50
        
        # Clone the search
        cloned = awards_search._clone()
        
        # Verify it's a different instance
        assert cloned is not awards_search
        assert cloned._filter_objects is not awards_search._filter_objects
        
        # But has same content
        assert len(cloned._filter_objects) == len(awards_search._filter_objects)
        assert cloned._limit == awards_search._limit


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
        # Verify fields are included (checking just a few key ones)
        assert "Award ID" in payload["fields"]
        assert "Recipient Name" in payload["fields"]
        assert "Awarding Agency" in payload["fields"]
        assert len(payload["fields"]) > 6  # More fields than before
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

    def test_build_payload_custom_limit(self, awards_search):
        """Test payload with custom limit."""
        search = awards_search.with_award_types("A").limit(50)
        
        payload = search._build_payload(page=1)
        
        assert payload["limit"] == 50


class TestTransformResult:
    """Test result transformation."""

    def test_transform_result(self, awards_search, mock_client):
        """Test that _transform_result creates Award instances."""
        result_data = {"Award ID": "123", "Recipient Name": "Test Corp"}
        
        award = awards_search._transform_result(result_data)
        
        assert isinstance(award, Award)
        # Award stores data internally, we can't directly access _data


class TestPaginationAndIteration:
    """Test pagination functionality."""

    def test_iteration_single_page(self, awards_search, mock_client):
        """Test iteration with a single page of results."""
        # Set up mock response
        mock_response = {
            "results": [
                {"Award ID": "1", "Recipient Name": "Corp 1"},
                {"Award ID": "2", "Recipient Name": "Corp 2"}
            ],
            "page_metadata": {"hasNext": False}
        }
        mock_client._make_request.return_value = mock_response
        
        search = awards_search.with_award_types("A")
        results = list(search)
        
        assert len(results) == 2
        assert all(isinstance(r, Award) for r in results)
        assert mock_client._make_request.call_count == 1

    def test_iteration_multiple_pages(self, awards_search, mock_client):
        """Test iteration with multiple pages."""
        # Set up mock responses for 3 pages
        mock_client._make_request.side_effect = [
            {
                "results": [{"Award ID": f"{i}"} for i in range(1, 101)],
                "page_metadata": {"hasNext": True}
            },
            {
                "results": [{"Award ID": f"{i}"} for i in range(101, 201)],
                "page_metadata": {"hasNext": True}
            },
            {
                "results": [{"Award ID": f"{i}"} for i in range(201, 251)],
                "page_metadata": {"hasNext": False}
            }
        ]
        
        search = awards_search.with_award_types("A")
        results = list(search)
        
        assert len(results) == 250
        assert mock_client._make_request.call_count == 3

    def test_iteration_with_max_pages(self, awards_search, mock_client):
        """Test iteration respects max_pages limit."""
        # Set up responses that would return 3 pages
        mock_client._make_request.side_effect = [
            {
                "results": [{"Award ID": f"{i}"} for i in range(100)],
                "page_metadata": {"hasNext": True}
            },
            {
                "results": [{"Award ID": f"{i}"} for i in range(100)],
                "page_metadata": {"hasNext": True}
            },
            # This page should not be fetched
            {
                "results": [{"Award ID": f"{i}"} for i in range(100)],
                "page_metadata": {"hasNext": False}
            }
        ]
        
        search = awards_search.with_award_types("A").max_pages(2)
        results = list(search)
        
        assert len(results) == 200
        assert mock_client._make_request.call_count == 2

    def test_first_method(self, awards_search, mock_client):
        """Test the first() method returns only the first result."""
        mock_response = {
            "results": [
                {"Award ID": "1", "Recipient Name": "Corp 1"},
                {"Award ID": "2", "Recipient Name": "Corp 2"}
            ],
            "page_metadata": {"hasNext": False}
        }
        mock_client._make_request.return_value = mock_response
        
        search = awards_search.with_award_types("A")
        result = search.first()
        
        assert isinstance(result, Award)
        assert result._data["Award ID"] == "1"
        # Verify the request was made correctly
        assert mock_client._make_request.called

    def test_first_method_no_results(self, awards_search, mock_client):
        """Test first() returns None when no results."""
        mock_client._make_request.return_value = {
            "results": [],
            "page_metadata": {"hasNext": False}
        }
        
        search = awards_search.with_award_types("A")
        result = search.first()
        
        assert result is None

    def test_all_method(self, awards_search, mock_client):
        """Test the all() method returns all results as a list."""
        mock_response = {
            "results": [
                {"Award ID": "1"},
                {"Award ID": "2"},
                {"Award ID": "3"}
            ],
            "page_metadata": {"hasNext": False}
        }
        mock_client._make_request.return_value = mock_response
        
        search = awards_search.with_award_types("A")
        results = search.all()
        
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, Award) for r in results)

    def test_count_method(self, awards_search, mock_client):
        """Test the count() method."""
        # Mock response with total count in metadata
        mock_client._make_request.return_value = {
            "results": [{"Award ID": "1"}],
            "page_metadata": {"hasNext": False, "total": 150}
        }
        
        search = awards_search.with_award_types("A")
        count = search.count()
        
        assert count == 150


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_api_error_propagation(self, awards_search, mock_client):
        """Test that API errors are propagated correctly."""
        from usaspending.exceptions import APIError
        
        mock_client._make_request.side_effect = APIError("Bad request")
        
        search = awards_search.with_award_types("A")
        
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

    def test_nasa_contracts_fy2024(self, awards_search, mock_client):
        """Test a realistic query for NASA contracts in FY2024."""
        mock_response = {
            "results": [
                {
                    "Award ID": "80NSSC24CA001",
                    "Recipient Name": "SpaceX",
                    "Award Amount": 2500000000,
                    "Awarding Agency": "NASA"
                }
            ],
            "page_metadata": {"hasNext": False}
        }
        mock_client._make_request.return_value = mock_response
        
        search = (awards_search
            .with_award_types("A", "B", "C", "D")
            .for_agency("NASA", AgencyType.AWARDING)
            .for_fiscal_year(2024)
            .with_keywords("space", "launch"))
        
        results = list(search)
        
        # Verify the payload sent
        call_args = mock_client._make_request.call_args
        payload = call_args[1]["json"]
        
        assert "award_type_codes" in payload["filters"]
        assert "agencies" in payload["filters"]
        assert "time_period" in payload["filters"]
        assert "keywords" in payload["filters"]
        
        assert len(results) == 1
        assert len(results) == 1
        assert isinstance(results[0], Award)

    def test_small_business_grants(self, awards_search, mock_client):
        """Test query for small business grants with location filters."""
        mock_response = {
            "results": [],
            "page_metadata": {"hasNext": False}
        }
        mock_client._make_request.return_value = mock_response
        
        ca_location = Location(country_code="USA", state_code="CA")
        
        search = (awards_search
            .with_award_types("02", "03", "04", "05")  # Grant types
            .with_recipient_types("small_business")
            .with_recipient_locations(ca_location)
            .with_award_amounts(
                AwardAmount(lower_bound=100000, upper_bound=500000)
            ))
        
        _ = search.all()
        
        # Verify filters were applied
        payload = mock_client._make_request.call_args[1]["json"]
        assert payload["filters"]["recipient_type_names"] == ["small_business"]
        assert payload["filters"]["recipient_locations"] == [{"country": "USA", "state": "CA"}]
        assert len(payload["filters"]["award_amounts"]) == 1