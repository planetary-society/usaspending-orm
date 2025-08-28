"""Tests for AgenciesSearch query implementations."""

import pytest
from usaspending.queries.funding_agencies_search import FundingAgenciesSearch
from usaspending.queries.awarding_agencies_search import AwardingAgenciesSearch
from usaspending.exceptions import ValidationError
from usaspending.models.agency import Agency
from tests.mocks.mock_client import MockUSASpendingClient


# Test parameters for both search classes
SEARCH_CLASS_PARAMS = [
    pytest.param(
        FundingAgenciesSearch,
        MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE,
        "find_all_funding_agencies_by_name",
        id="funding_agencies"
    ),
    pytest.param(
        AwardingAgenciesSearch,
        MockUSASpendingClient.Endpoints.AWARDING_AGENCY_AUTOCOMPLETE,
        "find_all_awarding_agencies_by_name",
        id="awarding_agencies"
    ),
]


@pytest.mark.parametrize("search_class,endpoint,resource_method", SEARCH_CLASS_PARAMS)
class TestAgenciesSearchInitialization:
    """Test AgenciesSearch initialization for both subclasses."""
    
    def test_initialization(self, mock_usa_client, search_class, endpoint, resource_method):
        """Test that AgenciesSearch initializes correctly."""
        search = search_class(mock_usa_client)
        assert search._client is mock_usa_client
        assert search._search_text == ""
        assert search._limit == 100
        assert search._result_type is None


@pytest.mark.parametrize("search_class,endpoint,resource_method", SEARCH_CLASS_PARAMS)
class TestAgenciesSearchEndpoint:
    """Test AgenciesSearch endpoint for both subclasses."""
    
    def test_endpoint(self, mock_usa_client, search_class, endpoint, resource_method):
        """Test that endpoint is correct."""
        search = search_class(mock_usa_client)
        assert search._endpoint == endpoint


@pytest.mark.parametrize("search_class,endpoint,resource_method", SEARCH_CLASS_PARAMS)
class TestAgenciesSearchExecution:
    """Test AgenciesSearch query execution for both subclasses."""
    
    def test_basic_search_all_types(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test searching returns all types when no filter applied."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        search = search_class(mock_usa_client).with_search_text("NASA")
        results = list(search)
        
        # Count expected total results from fixture
        fixture_results = agency_autocomplete_fixture["results"]
        expected_total = (
            len(fixture_results.get("toptier_agency", [])) +
            len(fixture_results.get("subtier_agency", [])) +
            len(fixture_results.get("office", []))
        )
        
        assert len(results) == expected_total
        assert all(isinstance(r, Agency) for r in results)
    
    def test_toptier_filter(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test filtering for toptier agencies only."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        search = search_class(mock_usa_client).with_search_text("NASA").toptier()
        results = list(search)
        
        # Use fixture data for assertions
        expected_toptier = agency_autocomplete_fixture["results"]["toptier_agency"]
        assert len(results) == len(expected_toptier)
        
        # Check first result matches fixture
        if expected_toptier:
            first_result = results[0]
            first_expected = expected_toptier[0]
            assert first_result.code == first_expected["code"]
            assert first_result.name == first_expected["name"]
            assert first_result.abbreviation == first_expected["abbreviation"]
    
    def test_subtier_filter(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test filtering for subtier agencies only."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        search = search_class(mock_usa_client).with_search_text("NASA").subtier()
        results = list(search)
        
        # Use fixture data for assertions
        expected_subtier = agency_autocomplete_fixture["results"]["subtier_agency"]
        assert len(results) == len(expected_subtier)
        
        # Verify agencies are extracted from subtier data
        if expected_subtier:
            first_result = results[0]
            first_expected_toptier = expected_subtier[0]["toptier_agency"]
            assert first_result.code == first_expected_toptier["code"]
            assert first_result.name == first_expected_toptier["name"]
    
    def test_office_filter(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test filtering for offices only."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        search = search_class(mock_usa_client).with_search_text("NASA").office()
        results = list(search)
        
        # Use fixture data for assertions
        expected_offices = agency_autocomplete_fixture["results"]["office"]
        assert len(results) == len(expected_offices)
        
        # Check unique agencies from offices
        if expected_offices:
            # Get unique toptier codes from offices
            unique_codes = set()
            for office in expected_offices:
                toptier = office.get("toptier_agency", {})
                unique_codes.add(toptier.get("code"))
            
            # Results should have agencies for each unique code
            result_codes = {r.code for r in results}
            # Note: We may have fewer results due to deduplication
            assert len(result_codes) <= len(unique_codes)
    
    def test_no_search_text_raises_error(self, mock_usa_client, search_class, endpoint, resource_method):
        """Test that missing search text raises ValidationError."""
        search = search_class(mock_usa_client)
        
        with pytest.raises(ValidationError, match="search_text is required"):
            list(search)
    
    def test_empty_results(self, mock_usa_client, search_class, endpoint, resource_method):
        """Test handling of empty results."""
        empty_response = {
            "results": {
                "toptier_agency": [],
                "subtier_agency": [],
                "office": []
            },
            "messages": []
        }
        
        mock_usa_client.set_response(endpoint, empty_response)
        
        search = search_class(mock_usa_client).with_search_text("ZZZZ")
        results = list(search)
        
        assert results == []
    
    def test_no_pagination(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test that pagination is not attempted (only page 1 is fetched)."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        search = search_class(mock_usa_client).with_search_text("NASA")
        results = list(search)
        
        # Should make at most a few API calls (may call count() and iterate)
        # The key is that we don't attempt to fetch page 2, 3, etc.
        assert mock_usa_client._request_counts[endpoint] <= 3  # Allow some flexibility
        
        # Verify we have results
        assert len(results) > 0
    
    def test_payload_construction(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test that payload is constructed correctly."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        search = search_class(mock_usa_client).with_search_text("NASA")
        list(search)  # Execute query
        
        # Check the request was made with correct payload
        mock_usa_client.assert_called_with(
            endpoint,
            "POST",
            json={
                "search_text": "NASA",
                "limit": 100
            }
        )
    
    def test_chaining_methods(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test method chaining returns new instances."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        search1 = search_class(mock_usa_client)
        search2 = search1.with_search_text("NASA")
        search3 = search2.toptier()
        
        # Each should be a different instance
        assert search1 is not search2
        assert search2 is not search3
        assert search1 is not search3
        
        # Original should be unchanged
        assert search1._search_text == ""
        assert search1._result_type is None
        
        # search2 should have search text
        assert search2._search_text == "NASA"
        assert search2._result_type is None
        
        # search3 should have both
        assert search3._search_text == "NASA"
        assert search3._result_type == "toptier"


@pytest.mark.parametrize("search_class,endpoint,resource_method", SEARCH_CLASS_PARAMS)
class TestAgenciesSearchResourceIntegration:
    """Test AgenciesSearch integration with AgencyResource for both subclasses."""
    
    def test_resource_method(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test that AgencyResource methods work."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        # Test through resource - get the method dynamically
        resource_func = getattr(mock_usa_client.agencies, resource_method)
        results = list(resource_func("NASA"))
        
        # Should get all results
        fixture_results = agency_autocomplete_fixture["results"]
        expected_total = (
            len(fixture_results.get("toptier_agency", [])) +
            len(fixture_results.get("subtier_agency", [])) +
            len(fixture_results.get("office", []))
        )
        
        assert len(results) == expected_total
        assert all(isinstance(r, Agency) for r in results)
    
    def test_resource_method_with_filters(self, mock_usa_client, agency_autocomplete_fixture, search_class, endpoint, resource_method):
        """Test that AgencyResource method supports chaining filters."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        
        # Test toptier filter
        resource_func = getattr(mock_usa_client.agencies, resource_method)
        toptier_results = list(resource_func("NASA").toptier())
        
        expected_toptier = agency_autocomplete_fixture["results"]["toptier_agency"]
        assert len(toptier_results) == len(expected_toptier)
        
        # Test subtier filter
        subtier_results = list(resource_func("NASA").subtier())
        
        expected_subtier = agency_autocomplete_fixture["results"]["subtier_agency"]
        assert len(subtier_results) == len(expected_subtier)


# Non-parametrized tests for class-specific behavior
class TestFundingAgenciesSearchSpecific:
    """Test FundingAgenciesSearch-specific behavior."""
    
    def test_class_type_consistency(self, mock_usa_client, agency_autocomplete_fixture):
        """Test that chained methods return correct class type."""
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE,
            agency_autocomplete_fixture
        )
        
        search1 = FundingAgenciesSearch(mock_usa_client)
        search2 = search1.with_search_text("NASA")
        search3 = search2.toptier()
        
        # All should be FundingAgenciesSearch instances
        assert isinstance(search1, FundingAgenciesSearch)
        assert isinstance(search2, FundingAgenciesSearch)
        assert isinstance(search3, FundingAgenciesSearch)
        
        # Should not be AwardingAgenciesSearch
        assert not isinstance(search1, AwardingAgenciesSearch)
        assert not isinstance(search2, AwardingAgenciesSearch)
        assert not isinstance(search3, AwardingAgenciesSearch)


class TestAwardingAgenciesSearchSpecific:
    """Test AwardingAgenciesSearch-specific behavior."""
    
    def test_class_type_consistency(self, mock_usa_client, agency_autocomplete_fixture):
        """Test that chained methods return correct class type."""
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARDING_AGENCY_AUTOCOMPLETE,
            agency_autocomplete_fixture
        )
        
        search1 = AwardingAgenciesSearch(mock_usa_client)
        search2 = search1.with_search_text("NASA")
        search3 = search2.toptier()
        
        # All should be AwardingAgenciesSearch instances
        assert isinstance(search1, AwardingAgenciesSearch)
        assert isinstance(search2, AwardingAgenciesSearch)
        assert isinstance(search3, AwardingAgenciesSearch)
        
        # Should not be FundingAgenciesSearch
        assert not isinstance(search1, FundingAgenciesSearch)
        assert not isinstance(search2, FundingAgenciesSearch)
        assert not isinstance(search3, FundingAgenciesSearch)