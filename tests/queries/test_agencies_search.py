"""Tests for AgenciesSearch query implementations."""

from typing import TypeVar

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending.exceptions import ValidationError
from usaspending.models.agency import Agency
from usaspending.models.subtier_agency import SubTierAgency
from usaspending.queries.agencies_search import AgenciesSearch
from usaspending.queries.awarding_agencies_search import AwardingAgenciesSearch
from usaspending.queries.funding_agencies_search import FundingAgenciesSearch

T = TypeVar("T", bound=AgenciesSearch)


# Test parameters for both search classes
SEARCH_CLASS_PARAMS = [
    pytest.param(
        FundingAgenciesSearch,
        MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE,
        "find_all_funding_agencies_by_name",
        id="funding_agencies",
    ),
    pytest.param(
        AwardingAgenciesSearch,
        MockUSASpendingClient.Endpoints.AWARDING_AGENCY_AUTOCOMPLETE,
        "find_all_awarding_agencies_by_name",
        id="awarding_agencies",
    ),
]


def init_search(search_class: type[T], mock_usa_client: MockUSASpendingClient) -> T:
    """Instantiate deprecated search classes with warning."""
    with pytest.warns(DeprecationWarning, match=f"{search_class.__name__} is deprecated"):
        return search_class(mock_usa_client)


@pytest.mark.parametrize("search_class,endpoint,resource_method", SEARCH_CLASS_PARAMS)
class TestAgenciesSearchInitialization:
    """Test AgenciesSearch initialization for both subclasses."""

    def test_initialization(self, mock_usa_client, search_class, endpoint, resource_method):
        """Test that AgenciesSearch initializes correctly."""
        search = init_search(search_class, mock_usa_client)
        assert search._client is mock_usa_client
        assert search._search_text == ""
        assert search._page_size == 100
        assert search._MAX_PAGE_SIZE == 500
        assert search._result_type is None


@pytest.mark.parametrize("search_class,endpoint,resource_method", SEARCH_CLASS_PARAMS)
class TestAgenciesSearchEndpoint:
    """Test AgenciesSearch endpoint for both subclasses."""

    def test_endpoint(self, mock_usa_client, search_class, endpoint, resource_method):
        """Test that endpoint is correct."""
        search = init_search(search_class, mock_usa_client)
        assert search._endpoint == endpoint


@pytest.mark.parametrize("search_class,endpoint,resource_method", SEARCH_CLASS_PARAMS)
class TestAgenciesSearchExecution:
    """Test AgenciesSearch query execution for both subclasses."""

    def test_basic_search_all_types(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test searching returns all types when no filter applied."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        search = init_search(search_class, mock_usa_client).search_text("NASA")
        results = list(search)

        # Count expected total results from fixture
        fixture_results = agency_autocomplete_fixture["results"]
        expected_total = (
            len(fixture_results.get("toptier_agency", []))
            + len(fixture_results.get("subtier_agency", []))
            + len(fixture_results.get("office", []))
        )

        assert len(results) == expected_total

    def test_toptier_filter(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test filtering for toptier agencies only."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        search = init_search(search_class, mock_usa_client).search_text("NASA").toptier()
        results = list(search)

        # Use fixture data for assertions
        expected_toptier = agency_autocomplete_fixture["results"]["toptier_agency"]
        assert len(results) == len(expected_toptier)
        assert all(isinstance(r, Agency) for r in results)

        # Check first result matches fixture
        if expected_toptier:
            first_result = results[0]
            first_expected = expected_toptier[0]
            assert first_result.code == first_expected["code"]
            assert first_result.name == first_expected["name"]
            assert first_result.abbreviation == first_expected["abbreviation"]

    def test_subtier_filter(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test filtering for subtier agencies only."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        search = init_search(search_class, mock_usa_client).search_text("NASA").subtier()
        results = list(search)

        # Use fixture data for assertions
        expected_subtier = agency_autocomplete_fixture["results"]["subtier_agency"]
        assert len(results) == len(expected_subtier)
        assert all(isinstance(r, SubTierAgency) for r in results)

    def test_office_filter(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test filtering for offices only."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        search = init_search(search_class, mock_usa_client).search_text("NASA").office()
        results = list(search)

        # Use fixture data for assertions
        expected_offices = agency_autocomplete_fixture["results"]["office"]
        assert len(results) == len(expected_offices)
        assert all(isinstance(r, SubTierAgency) for r in results)

    def test_no_search_text_raises_error(
        self, mock_usa_client, search_class, endpoint, resource_method
    ):
        """Test that missing search text raises ValidationError."""
        search = init_search(search_class, mock_usa_client)

        with pytest.raises(ValidationError, match="search_text is required"):
            list(search)

    def test_empty_results(self, mock_usa_client, search_class, endpoint, resource_method):
        """Test handling of empty results."""
        empty_response = {
            "results": {"toptier_agency": [], "subtier_agency": [], "office": []},
            "messages": [],
        }

        mock_usa_client.set_response(endpoint, empty_response)

        search = init_search(search_class, mock_usa_client).search_text("ZZZZ")
        results = list(search)

        assert results == []

    def test_no_pagination(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test that pagination is not attempted (only page 1 is fetched)."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        search = init_search(search_class, mock_usa_client).search_text("NASA")
        results = list(search)

        # Should make at most a few API calls (may call count() and iterate)
        # The key is that we don't attempt to fetch page 2, 3, etc.
        assert mock_usa_client._request_counts[endpoint] <= 3  # Allow some flexibility

        # Verify we have results
        assert len(results) > 0

    def test_payload_construction(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test that payload is constructed correctly."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        search = init_search(search_class, mock_usa_client).search_text("NASA")
        list(search)  # Execute query

        # Check the request was made with correct payload
        mock_usa_client.assert_called_with(
            endpoint, "POST", json={"search_text": "NASA", "limit": 100}
        )

    def test_chaining_methods(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test method chaining returns new instances."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        search1 = init_search(search_class, mock_usa_client)
        search2 = search1.search_text("NASA")
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

    def test_resource_method(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test that AgencyResource methods work."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        # Test through resource - get the method dynamically
        resource_func = getattr(mock_usa_client.agencies, resource_method)
        with pytest.warns(DeprecationWarning, match=f"{resource_method} is deprecated"):
            search = resource_func("NASA")
        results = list(search)

        # Should get all results
        fixture_results = agency_autocomplete_fixture["results"]
        expected_total = (
            len(fixture_results.get("toptier_agency", []))
            + len(fixture_results.get("subtier_agency", []))
            + len(fixture_results.get("office", []))
        )

        assert len(results) == expected_total

    def test_resource_method_with_filters(
        self,
        mock_usa_client,
        agency_autocomplete_fixture,
        search_class,
        endpoint,
        resource_method,
    ):
        """Test that AgencyResource method supports chaining filters."""
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        # Test toptier filter
        resource_func = getattr(mock_usa_client.agencies, resource_method)
        with pytest.warns(DeprecationWarning, match=f"{resource_method} is deprecated"):
            search = resource_func("NASA")
        toptier_results = list(search.toptier())

        expected_toptier = agency_autocomplete_fixture["results"]["toptier_agency"]
        assert len(toptier_results) == len(expected_toptier)

        # Test subtier filter
        subtier_results = list(search.subtier())

        expected_subtier = agency_autocomplete_fixture["results"]["subtier_agency"]
        assert len(subtier_results) == len(expected_subtier)


class TestAgenciesSearchSizingAndCollectionBehavior:
    """Autocomplete maps one three-bucket response onto the shared query API."""

    @staticmethod
    def _six_result_response(agency_autocomplete_fixture):
        """Return two entries from each independently limited upstream bucket."""
        results = agency_autocomplete_fixture["results"]
        return {
            "results": {
                "toptier_agency": [results["toptier_agency"][0], results["toptier_agency"][0]],
                "subtier_agency": results["subtier_agency"][:2],
                "office": results["office"][:2],
            },
            "messages": [],
        }

    @pytest.mark.parametrize(
        ("size", "expected"),
        [(500, 500), (501, 500)],
    )
    def test_page_size_maps_to_the_upstream_limit(
        self, mock_usa_client, agency_autocomplete_fixture, size, expected
    ):
        """The endpoint accepts at most 500 entries per result bucket."""
        endpoint = MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)

        query = mock_usa_client.agencies.search().name("NASA").page_size(size)
        query.all()

        mock_usa_client.assert_called_with(
            endpoint,
            "POST",
            json={"search_text": "NASA", "limit": expected},
        )

    @pytest.mark.parametrize("limit_first", [True, False])
    def test_total_limit_lowers_request_size_in_either_chain_order(
        self, mock_usa_client, agency_autocomplete_fixture, limit_first
    ):
        """A total limit is narrower than the endpoint's per-bucket page size."""
        endpoint = MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE
        mock_usa_client.set_response(endpoint, agency_autocomplete_fixture)
        query = mock_usa_client.agencies.search().name("NASA")
        query = query.limit(3).page_size(500) if limit_first else query.page_size(500).limit(3)

        results = query.all()

        assert len(results) == 3
        mock_usa_client.assert_called_with(
            endpoint,
            "POST",
            json={"search_text": "NASA", "limit": 3},
        )

    def test_zero_limit_skips_the_request(self, mock_usa_client):
        """An empty client-side bound is resolved without HTTP."""
        mock_usa_client.forbid_requests()
        query = mock_usa_client.agencies.search().name("NASA").limit(0)

        assert query.all() == []
        assert query.count() == 0
        assert mock_usa_client._request_history == []

    def test_zero_max_pages_skips_the_single_response(self, mock_usa_client):
        """Disallowing every request makes all collection operations empty."""
        mock_usa_client.forbid_requests()
        query = mock_usa_client.agencies.search().name("NASA").max_pages(0)

        assert query.all() == []
        assert query.count() == 0
        with pytest.raises(IndexError):
            _ = query[0]
        assert mock_usa_client._request_history == []

    def test_one_allowed_request_returns_and_counts_all_buckets(
        self, mock_usa_client, agency_autocomplete_fixture
    ):
        """Positive max_pages limits requests, not flattened bucket rows."""
        endpoint = MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE
        mock_usa_client.set_response(
            endpoint,
            self._six_result_response(agency_autocomplete_fixture),
        )
        query = mock_usa_client.agencies.search().name("NASA").page_size(2).max_pages(1)

        assert len(query.all()) == 6
        assert query.count() == 6
        assert len(query) == 6

    def test_indexing_materializes_the_single_flattened_response(
        self, mock_usa_client, agency_autocomplete_fixture
    ):
        """Indices do not translate into nonexistent autocomplete pages."""
        endpoint = MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE
        mock_usa_client.set_response(
            endpoint,
            self._six_result_response(agency_autocomplete_fixture),
        )
        query = mock_usa_client.agencies.search().name("NASA").page_size(2)
        expected = query.all()

        assert query[2].raw == expected[2].raw
        assert query[-1].raw == expected[-1].raw
        assert [item.raw for item in query[1:5]] == [item.raw for item in expected[1:5]]

    def test_limit_keeps_all_collection_operations_consistent(
        self, mock_usa_client, agency_autocomplete_fixture
    ):
        """The flattened client limit applies to counts, indices, and slices."""
        endpoint = MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE
        mock_usa_client.set_response(
            endpoint,
            self._six_result_response(agency_autocomplete_fixture),
        )
        query = mock_usa_client.agencies.search().name("NASA").page_size(2).limit(4)

        assert len(query.all()) == query.count() == len(query) == 4
        assert query[3] is not None
        assert len(query[1:4]) == 3
        with pytest.raises(IndexError):
            _ = query[4]


# Non-parametrized tests for class-specific behavior
class TestFundingAgenciesSearchSpecific:
    """Test FundingAgenciesSearch-specific behavior."""

    def test_class_type_consistency(self, mock_usa_client, agency_autocomplete_fixture):
        """Test that chained methods return correct class type."""
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AGENCY_AUTOCOMPLETE,
            agency_autocomplete_fixture,
        )

        with pytest.warns(DeprecationWarning, match="FundingAgenciesSearch is deprecated"):
            search1 = FundingAgenciesSearch(mock_usa_client)
        search2 = search1.search_text("NASA")
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
            agency_autocomplete_fixture,
        )

        with pytest.warns(DeprecationWarning, match="AwardingAgenciesSearch is deprecated"):
            search1 = AwardingAgenciesSearch(mock_usa_client)
        search2 = search1.search_text("NASA")
        search3 = search2.toptier()

        # All should be AwardingAgenciesSearch instances
        assert isinstance(search1, AwardingAgenciesSearch)
        assert isinstance(search2, AwardingAgenciesSearch)
        assert isinstance(search3, AwardingAgenciesSearch)

        # Should not be FundingAgenciesSearch
        assert not isinstance(search1, FundingAgenciesSearch)
        assert not isinstance(search2, FundingAgenciesSearch)
        assert not isinstance(search3, FundingAgenciesSearch)
