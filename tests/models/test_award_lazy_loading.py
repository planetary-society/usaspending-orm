"""
Tests for Award property behavior when initialized from search results.

This file tests that Award objects initialized from a search result (which has
a flat structure and a subset of fields) can correctly populate their properties
without triggering a full API fetch for details, and that a fetch is only
triggered when a property not present in the search result is accessed.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from tests.utils import assert_decimal_equal
from usaspending.models import Award, Location, PeriodOfPerformance, Recipient


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
        assert_decimal_equal(award.award_amount, search_result["Award Amount"])
        assert_decimal_equal(award.total_obligation, search_result["Award Amount"])
        assert award.recipient_uei == search_result["Recipient UEI"]
        assert_decimal_equal(award.total_outlay, search_result["Total Outlays"])

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

    def test_recipient_stub_no_recipient_level_fetch(self, award_from_search, search_results_data):
        """Test that accessing pre-loaded fields on the Recipient stub does not trigger
        a Recipient-level fetch (i.e., no call to /recipient/{id}/ endpoint).

        This catches an N+1 query bug: the Award search result contains recipient data
        in flat fields (e.g. 'Recipient Name', 'Recipient UEI'), and those should be
        accessible on the Recipient stub without triggering a separate API call.
        """
        award = award_from_search
        search_result = search_results_data[0]

        # Access recipient - this constructs the stub from flat search fields
        recipient = award.recipient
        assert recipient is not None

        # Mock _fetch_details on the Recipient stub AFTER construction
        recipient._fetch_details = Mock(return_value=None)

        # Access pre-loaded fields -- none should trigger a recipient-level fetch
        assert recipient.name is not None
        assert recipient.recipient_id is not None
        assert recipient.uei == search_result.get("Recipient UEI")

        # Location was directly assigned from "Recipient Location" dict
        loc = recipient.location
        assert isinstance(loc, Location)
        assert loc.state_code is not None

        # Verify no Recipient-level fetch was triggered
        recipient._fetch_details.assert_not_called()

        # Also verify no Award-level fetch was triggered
        award._fetch_details.assert_not_called()

    def test_recipient_stub_null_fields_no_fetch(self, award_from_search, search_results_data):
        """Test that accessing pre-loaded fields with None values on the Recipient stub
        does not trigger a Recipient-level fetch.

        The search result may include fields with null values (e.g., DUNS number is
        deprecated and typically null). When these null values are mapped into the
        Recipient stub, accessing them should return None without triggering a fetch
        to /recipient/{id}/, since the data IS present -- it is just legitimately null.
        """
        award = award_from_search
        search_result = search_results_data[0]

        recipient = award.recipient
        assert recipient is not None

        # Mock _fetch_details on the Recipient stub
        recipient._fetch_details = Mock(return_value=None)

        # DUNS is null in the search result fixture and mapped to recipient_unique_id
        assert search_result.get("Recipient DUNS Number") is None
        # Accessing duns should return None without triggering a fetch
        assert recipient.duns is None

        # Verify no fetch was triggered for a legitimately null pre-loaded field
        recipient._fetch_details.assert_not_called()

    def test_lazy_load_triggers_fetch(self, award_from_search, detail_fixture_data):
        """Test that accessing a property not in search results triggers a fetch."""
        award = award_from_search
        # Replace the mock to return the detailed fixture data
        award._fetch_details = Mock(return_value=detail_fixture_data)

        # This property is not in the search results, so it should trigger a fetch
        assert award.subaward_count == detail_fixture_data["subaward_count"]

        award._fetch_details.assert_called_once()

        # Accessing another lazy-loaded property should not trigger another fetch
        assert_decimal_equal(
            award.total_subaward_amount, detail_fixture_data["total_subaward_amount"]
        )
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


class TestFetchAllDetails:
    """Test the fetch_all_details() method for eager loading."""

    @pytest.fixture
    def award_with_mock_fetch(self, mock_usa_client, search_results_contracts_data):
        """Create an Award with a mocked _fetch_details method."""
        award = Award(search_results_contracts_data[0], mock_usa_client)
        award._fetch_details = Mock(return_value={"extra": "data"})
        return award

    def test_fetch_all_details_calls_ensure_details(self, award_with_mock_fetch):
        """Test that fetch_all_details() triggers lazy loading."""
        assert not award_with_mock_fetch._details_fetched

        award_with_mock_fetch.fetch_all_details()

        assert award_with_mock_fetch._details_fetched
        award_with_mock_fetch._fetch_details.assert_called_once()

    def test_fetch_all_details_idempotent(self, award_with_mock_fetch):
        """Test that calling fetch_all_details() multiple times is safe."""
        award_with_mock_fetch.fetch_all_details()
        award_with_mock_fetch.fetch_all_details()
        award_with_mock_fetch.fetch_all_details()

        # Should only fetch once
        award_with_mock_fetch._fetch_details.assert_called_once()

    def test_fetch_all_details_updates_data(self, mock_usa_client, search_results_contracts_data):
        """Test that fetch_all_details() updates model data."""
        award = Award(search_results_contracts_data[0], mock_usa_client)
        award._fetch_details = Mock(return_value={"new_field": "new_value"})

        initial_keys = set(award._data.keys())
        award.fetch_all_details()

        assert "new_field" in award._data
        assert award._data["new_field"] == "new_value"
        # Original keys should still be present
        assert all(key in award._data for key in initial_keys)
