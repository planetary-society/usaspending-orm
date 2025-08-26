"""
This file contains shared test logic for Award models.
These classes are not meant to be run directly by pytest, but are
instead inherited by the concrete test classes in test_award_types.py.
"""

from __future__ import annotations

import pytest
from datetime import datetime
from usaspending.models import Award, Recipient
from usaspending.models.agency import Agency
from usaspending.models.subaward import SubAward
from usaspending.exceptions import ValidationError
from tests.mocks.mock_client import MockUSASpendingClient


class AwardTestingMixin:
    """
    A mixin class containing common tests for all award types.
    Subclasses must define AWARD_MODEL, FIXTURE_NAME, and FIXTURE_PATH.
    """

    AWARD_MODEL = None
    FIXTURE_NAME = None
    FIXTURE_PATH = None

    @pytest.fixture
    def fixture_data(self, request):
        """A fixture that dynamically loads the correct fixture data based on the test class."""
        if not self.FIXTURE_NAME:
            pytest.skip("Test class not configured with FIXTURE_NAME")
        return request.getfixturevalue(self.FIXTURE_NAME)

    # --- Initialization Tests ---

    def test_init_with_dict_data(self, mock_usa_client):
        """Test Award initialization with dictionary data."""
        data = {
            "generated_unique_award_id": "AWARD_123",
            "description": "Test Award",
        }
        award = self.AWARD_MODEL(data, mock_usa_client)
        assert award._data["generated_unique_award_id"] == "AWARD_123"
        assert isinstance(award, Award)
        assert isinstance(award, self.AWARD_MODEL)

    def test_init_with_string_id(self, mock_usa_client):
        """Test Award initialization with string award ID."""
        award = self.AWARD_MODEL("AWARD_123", mock_usa_client)
        assert award._data["generated_unique_award_id"] == "AWARD_123"

    def test_init_with_invalid_type_raises_error(self, mock_usa_client):
        """Test that Award initialization with invalid type raises ValidationError."""
        with pytest.raises(ValidationError):
            self.AWARD_MODEL(123, mock_usa_client)

    # --- Property and Method Tests with Fixtures ---

    def test_lazy_loading_fetches_details(self, mock_usa_client, fixture_data):
        """Test that lazy loading fetches details when a property is accessed."""
        award_id = fixture_data["generated_unique_award_id"]
        endpoint = MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(award_id=award_id)
        mock_usa_client.set_fixture_response(endpoint, self.FIXTURE_PATH)
        award = self.AWARD_MODEL({"generated_unique_award_id": award_id}, mock_usa_client)

        assert award.description.lower() == fixture_data["description"].lower()
        assert mock_usa_client.get_request_count(endpoint) == 1
        _ = award.description
        assert mock_usa_client.get_request_count(endpoint) == 1

    def test_properties_from_fixture(self, mock_usa_client, fixture_data):
        """Test various properties using fixture data."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        assert award.id == fixture_data["id"]
        assert award.generated_unique_award_id == fixture_data["generated_unique_award_id"]
        assert award.description.lower() == fixture_data["description"].lower()
        assert award.total_obligation == fixture_data["total_obligation"]

    def test_period_of_performance(self, mock_usa_client, fixture_data):
        """Test period_of_performance creation from fixture data."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        pop = award.period_of_performance
        assert pop.raw == fixture_data["period_of_performance"]
        expected_start_date = datetime.fromisoformat(fixture_data["period_of_performance"]["start_date"])
        assert pop.start_date == expected_start_date

    def test_recipient_property(self, mock_usa_client, fixture_data):
        """Test that the recipient property is correctly instantiated and cached."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        recipient = award.recipient
        assert isinstance(recipient, Recipient)
        assert recipient.name.lower() == fixture_data["recipient"]["recipient_name"].lower()
        assert award.recipient is recipient

    def test_agency_properties(self, mock_usa_client, fixture_data):
        """Test funding and awarding agency properties."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        funding_agency = award.funding_agency
        if "funding_agency" in fixture_data and fixture_data["funding_agency"]:
            assert isinstance(funding_agency, Agency)
            assert funding_agency.id == fixture_data["funding_agency"]["id"]
        else:
            assert funding_agency is None

        awarding_agency = award.awarding_agency
        if "awarding_agency" in fixture_data and fixture_data["awarding_agency"]:
            assert isinstance(awarding_agency, Agency)
            assert awarding_agency.id == fixture_data["awarding_agency"]["id"]
        else:
            assert awarding_agency is None

    def test_transactions_property(self, mock_usa_client, fixture_data):
        """Test that the transactions property returns a configured query builder."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        award_id = fixture_data["generated_unique_award_id"]
        mock_usa_client.mock_transactions_for_award(award_id, transactions=[])

        results = award.transactions.limit(10).all()
        assert results == []
        last_request = mock_usa_client.get_last_request(MockUSASpendingClient.Endpoints.TRANSACTIONS)
        assert last_request["json"]["award_id"] == award_id
        assert last_request["json"]["limit"] == 10

    def test_fetch_details_handles_api_exception(self, mock_usa_client, fixture_data):
        """Test _fetch_details handles API exceptions gracefully."""
        award_id = fixture_data["generated_unique_award_id"]
        endpoint = MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(award_id=award_id)
        mock_usa_client.set_error_response(endpoint, 500)
        award = self.AWARD_MODEL({"generated_unique_award_id": award_id}, mock_usa_client)
        assert award.description is None
        assert mock_usa_client.get_request_count(endpoint) == 1

    def test_subawards_property(self, mock_usa_client, fixture_data):
        """Test that the subawards property returns a query builder that can be iterated."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)

        try:
            subawards_query = award.subawards
        except NotImplementedError:
            pytest.skip(f"Subawards not implemented for {self.AWARD_MODEL.__name__}")

        award_id = fixture_data["generated_unique_award_id"]

        # Mock the API response for the subaward search
        subaward_results = [
            {"internal_id": "SUB1", "Sub-Award ID": "S1", "Sub-Award Amount": 100},
            {"internal_id": "SUB2", "Sub-Award ID": "S2", "Sub-Award Amount": 200},
        ]
        mock_usa_client.set_paginated_response(MockUSASpendingClient.Endpoints.AWARD_SEARCH, subaward_results)

        # Iterate over the subawards
        subawards_list = list(subawards_query)

        # Verify the results
        assert len(subawards_list) == 2
        assert all(isinstance(s, SubAward) for s in subawards_list)
        assert subawards_list[0].sub_award_id == "S1"

        # Verify the API call
        last_request = mock_usa_client.get_last_request(MockUSASpendingClient.Endpoints.AWARD_SEARCH)
        payload = last_request["json"]
        assert payload["filters"]["award_unique_id"] == award_id
        assert payload["subawards"] is True


class TestAwardGenericBehaviors:
    """Test generic Award behaviors that don't depend on award type."""

    def test_get_value_helper(self, mock_usa_client):
        """Test the get_value() helper method."""
        data = {"field1": "", "field2": None, "field3": "actual_value"}
        award = Award(data, mock_usa_client)
        assert award.get_value(["field1", "field2", "field3"]) == ""
        assert award.get_value(["field2", "field3"]) == "actual_value"

    def test_parent_award_property(self, mock_usa_client):
        """Test parent_award property returns an Award instance."""
        parent_data = {"generated_unique_award_id": "PARENT_123"}
        data = {"generated_unique_award_id": "CHILD_123", "parent_award": parent_data}
        award = Award(data, mock_usa_client)
        parent = award.parent_award
        assert isinstance(parent, Award)
        assert parent.generated_unique_award_id == "PARENT_123"
        assert award.parent_award is parent
