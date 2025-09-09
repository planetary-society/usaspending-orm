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
from usaspending.exceptions import ValidationError, HTTPError
from tests.mocks.mock_client import MockUSASpendingClient
from tests.utils import assert_decimal_equal


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
        endpoint = MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(
            award_id=award_id
        )
        mock_usa_client.set_fixture_response(endpoint, self.FIXTURE_PATH)
        award = self.AWARD_MODEL(
            {"generated_unique_award_id": award_id}, mock_usa_client
        )

        assert award.description.lower() == fixture_data["description"].lower()
        assert mock_usa_client.get_request_count(endpoint) == 1
        _ = award.description
        assert mock_usa_client.get_request_count(endpoint) == 1

    def test_properties_from_fixture(self, mock_usa_client, fixture_data):
        """Test various properties using fixture data."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        assert award.id == fixture_data["id"]
        assert (
            award.generated_unique_award_id == fixture_data["generated_unique_award_id"]
        )
        assert award.description.lower() == fixture_data["description"].lower()
        assert_decimal_equal(award.total_obligation, fixture_data["total_obligation"])

    def test_period_of_performance(self, mock_usa_client, fixture_data):
        """Test period_of_performance creation from fixture data."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        pop = award.period_of_performance
        assert pop.raw == fixture_data["period_of_performance"]
        expected_start_date = datetime.fromisoformat(
            fixture_data["period_of_performance"]["start_date"]
        )
        assert pop.start_date == expected_start_date

    def test_recipient_property(self, mock_usa_client, fixture_data):
        """Test that the recipient property is correctly instantiated and cached."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        recipient = award.recipient
        assert isinstance(recipient, Recipient)
        assert (
            recipient.name.lower()
            == fixture_data["recipient"]["recipient_name"].lower()
        )
        assert award.recipient is recipient

    def test_agency_properties(self, mock_usa_client, fixture_data):
        """Test funding and awarding agency properties."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        funding_agency = award.funding_agency
        if "funding_agency" in fixture_data and fixture_data["funding_agency"]:
            assert isinstance(funding_agency, Agency)
            assert (
                funding_agency.name
                == fixture_data["funding_agency"]["toptier_agency"]["name"]
            )
        else:
            assert funding_agency is None

        awarding_agency = award.awarding_agency
        if "awarding_agency" in fixture_data and fixture_data["awarding_agency"]:
            assert isinstance(awarding_agency, Agency)
            assert (
                awarding_agency.name
                == fixture_data["awarding_agency"]["toptier_agency"]["name"]
            )
        else:
            assert awarding_agency is None

    def test_transactions_property(self, mock_usa_client, fixture_data):
        """Test that the transactions property returns a configured query builder."""
        award = self.AWARD_MODEL(fixture_data, mock_usa_client)
        award_id = fixture_data["generated_unique_award_id"]
        mock_usa_client.mock_transactions_for_award(award_id, transactions=[])

        results = award.transactions.limit(10).all()
        assert results == []
        last_request = mock_usa_client.get_last_request(
            MockUSASpendingClient.Endpoints.TRANSACTIONS
        )
        assert last_request["json"]["award_id"] == award_id
        assert last_request["json"]["limit"] == 10

    def test_fetch_details_raises_exception(self, mock_usa_client, fixture_data):
        """Test _fetch_details raises API exceptions if error."""
        award_id = fixture_data["generated_unique_award_id"]
        endpoint = MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(
            award_id=award_id
        )
        mock_usa_client.set_error_response(endpoint, 500)
        award = self.AWARD_MODEL(
            {"generated_unique_award_id": award_id}, mock_usa_client
        )
        with pytest.raises(HTTPError):
            award.description

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
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH, subaward_results
        )

        # Iterate over the subawards
        subawards_list = list(subawards_query)

        # Verify the results
        assert len(subawards_list) == 2
        assert all(isinstance(s, SubAward) for s in subawards_list)
        assert subawards_list[0].sub_award_id == "S1"

        # Verify the API call
        last_request = mock_usa_client.get_last_request(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH
        )
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

    def test_derived_award_identifier(self, mock_usa_client):
        """Test _derived_award_identifier extracts correct ID from generated_unique_award_id."""
        
        # Test valid IDs using real examples from fixture data
        test_cases = [
            # Contract Awards (CONT_AWD format)
            ("CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-", "80GSFC18C0008"),
            ("CONT_AWD_NAS1510000_8000_-NONE-_-NONE-", "NAS1510000"),
            ("CONT_AWD_80NM0018F0615_8000_80NM0018D0004_8000", "80NM0018F0615"),
            ("CONT_AWD_NNJ06TA25C_8000_-NONE-_-NONE-", "NNJ06TA25C"),
            ("CONT_AWD_NNM07AB03C_8000_-NONE-_-NONE-", "NNM07AB03C"),
            
            # Contract IDVs (CONT_IDV format)
            ("CONT_IDV_80JSC019C0012_8000", "80JSC019C0012"),
            ("CONT_IDV_NNJ09GA02B_8000", "NNJ09GA02B"),
            ("CONT_IDV_NNK10LB00B_8000", "NNK10LB00B"),
            
            # Assistance Non-Aggregated (ASST_NON format)
            ("ASST_NON_NNM11AA01A_080", "NNM11AA01A"),
            ("ASST_NON_P268K115150_091", "P268K115150"),
            ("ASST_NON_NNX16AO69A_080", "NNX16AO69A"),
            ("ASST_NON_NNX12AD05A_080", "NNX12AD05A"),
            
            # Assistance Aggregated (ASST_AGG format)
            ("ASST_AGG_1020FA_-NONE-", "1020FA"),
            ("ASST_AGG_15CA35050692501_1251", "15CA35050692501"),
        ]
        
        for generated_id, expected in test_cases:
            award = Award({"generated_unique_award_id": generated_id}, mock_usa_client)
            result = award._derived_award_identifier()
            assert result == expected, f"Expected {expected} from {generated_id}, got {result}"
        
        # Test -NONE- placeholders return None
        none_cases = [
            "CONT_IDV_-NONE-_8000",
            "CONT_AWD_-NONE-_8000_-NONE-_-NONE-",
            "ASST_NON_-NONE-_080",
            "ASST_AGG_-NONE-_1251",
        ]
        
        for generated_id in none_cases:
            award = Award({"generated_unique_award_id": generated_id}, mock_usa_client)
            assert award._derived_award_identifier() is None, f"Expected None from {generated_id}"
        
        # Test malformed IDs return None
        malformed_cases = [
            "",  # Empty string
            "CONT_AWD",  # Too few parts
            "CONT_AWD_12345",  # Still too few parts
            "INVALID_FORMAT_12345_8000",  # Invalid prefix
            "NOT_A_VALID_ID",  # Completely invalid
        ]
        
        for generated_id in malformed_cases:
            award = Award({"generated_unique_award_id": generated_id}, mock_usa_client)
            assert award._derived_award_identifier() is None, f"Expected None from malformed ID: {generated_id}"
        
        # Test empty identifier segment returns None
        award = Award({"generated_unique_award_id": "CONT_AWD__8000_-NONE-_-NONE-"}, mock_usa_client)
        assert award._derived_award_identifier() is None
        
        # Test missing generated_unique_award_id returns None
        award = Award({"description": "Test Award"}, mock_usa_client)
        assert award._derived_award_identifier() is None
