"""
Tests for Award property behavior when initialized from search results.

This file tests that Award objects initialized from a search result (which has
a flat structure and a subset of fields) can correctly populate their properties
without triggering a full API fetch for details, and that a fetch is only
triggered when a property not present in the search result is accessed.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from usaspending.models import Award, Recipient, Location, PeriodOfPerformance


class BaseTestAwardLazyLoading:
    """
    A mixin class for testing lazy loading from search results.
    Subclasses must provide SEARCH_RESULT_FIXTURE_NAME and DETAIL_FIXTURE_NAME.
    """
    AWARD_MODEL = Award  # These tests should work with the base Award model
    SEARCH_RESULT_FIXTURE_NAME = None
    DETAIL_FIXTURE_NAME = None

    @pytest.fixture
    def search_results_data(self, request):
        """Loads the search results fixture data for the specific award type."""
        if not self.SEARCH_RESULT_FIXTURE_NAME:
            pytest.skip("Test class not configured with SEARCH_RESULT_FIXTURE_NAME")
        return request.getfixturevalue(self.SEARCH_RESULT_FIXTURE_NAME)

    @pytest.fixture
    def detail_fixture_data(self, request):
        """Loads the detail fixture data for the specific award type."""
        if not self.DETAIL_FIXTURE_NAME:
            pytest.skip("Test class not configured with DETAIL_FIXTURE_NAME")
        return request.getfixturevalue(self.DETAIL_FIXTURE_NAME)

    @pytest.fixture
    def award_from_search(self, mock_usa_client, search_results_data):
        """Creates an Award object from the first search result."""
        award = self.AWARD_MODEL(search_results_data[0], mock_usa_client)
        # Mock _fetch_details to ensure it's not called unless we want it to be
        award._fetch_details = Mock(return_value=None)
        return award

    def test_basic_properties_no_fetch(self, award_from_search, search_results_data):
        """Test that basic properties work correctly without triggering a fetch."""
        award = award_from_search
        search_result = search_results_data[0]

        assert award.award_identifier == search_result["Award ID"]
        assert award.description.lower() == search_result["Description"].lower()
        assert award.award_amount == search_result["Award Amount"]
        assert award.total_obligation == search_result["Award Amount"]
        assert award.recipient_uei == search_result["Recipient UEI"]
        assert award.total_outlay == search_result["Total Outlays"]

        award._fetch_details.assert_not_called()

    def test_complex_properties_no_fetch(self, award_from_search):
        """Test that complex object properties are built from search results without fetching."""
        award = award_from_search

        # Recipient
        recipient = award.recipient
        assert isinstance(recipient, Recipient)
        assert isinstance(recipient.name, str)
        assert recipient.location is not None
        assert isinstance(recipient.location, Location)

        # Place of Performance
        pop = award.place_of_performance
        assert isinstance(pop, Location)

        # Period of Performance
        period = award.period_of_performance
        assert isinstance(period, PeriodOfPerformance)

        award._fetch_details.assert_not_called()

    def test_lazy_load_triggers_fetch(self, award_from_search, detail_fixture_data):
        """Test that accessing a property not in search results triggers a fetch."""
        award = award_from_search
        # Replace the mock to return the detailed fixture data
        award._fetch_details = Mock(return_value=detail_fixture_data)

        # This property is not in the search results, so it should trigger a fetch
        assert award.subaward_count == detail_fixture_data["subaward_count"]

        award._fetch_details.assert_called_once()

        # Accessing another lazy-loaded property should not trigger another fetch
        assert award.total_subaward_amount == detail_fixture_data["total_subaward_amount"]
        award._fetch_details.assert_called_once()


class TestContractLazyLoading(BaseTestAwardLazyLoading):
    """Tests lazy loading for Contract awards."""
    SEARCH_RESULT_FIXTURE_NAME = "search_results_contracts_data"
    DETAIL_FIXTURE_NAME = "contract_fixture_data"


class TestGrantLazyLoading(BaseTestAwardLazyLoading):
    """Tests lazy loading for Grant awards."""
    SEARCH_RESULT_FIXTURE_NAME = "search_results_grants_data"
    DETAIL_FIXTURE_NAME = "grant_fixture_data"


class TestIDVLazyLoading(BaseTestAwardLazyLoading):
    """Tests lazy loading for IDV awards."""
    SEARCH_RESULT_FIXTURE_NAME = "search_results_idvs_data"
    DETAIL_FIXTURE_NAME = "idv_fixture_data"
