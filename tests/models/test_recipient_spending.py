"""Tests for RecipientSpending model functionality."""

from __future__ import annotations

import pytest

from tests.utils import assert_decimal_equal
from usaspending.models import Recipient, RecipientSpending
from usaspending.queries.spending_search import SpendingSearch
from usaspending.utils.numbers import round_to_millions
from usaspending.utils.textcase import titlecase_name


@pytest.fixture
def spending_response(load_fixture):
    return load_fixture("spending_by_recipient.json")


class TestRecipientSpendingInitialization:
    """Test RecipientSpending model initialization."""

    def test_init_with_dict_data(self, mock_usa_client, spending_response):
        """Test RecipientSpending initialization with dictionary data."""
        first_result = spending_response["results"][0]

        # Add category field for initialization
        data = {**first_result, "category": "recipient"}
        recipient_spending = RecipientSpending(data, mock_usa_client)

        # Test using dynamic fixture values
        assert (
            recipient_spending._data["recipient_id"][:15] == first_result["recipient_id"][:15]
        )  # Clean recipient_id
        assert recipient_spending._data["uei"] == first_result["uei"]
        assert recipient_spending._data["name"] == first_result["name"]
        assert recipient_spending._data["code"] == first_result["code"]
        assert recipient_spending._client is not None
        assert isinstance(recipient_spending, RecipientSpending)
        assert isinstance(recipient_spending, Recipient)  # Should inherit from Spending


class TestRecipientSpendingProperties:
    """Test recipient spending properties."""

    def test_recipient_specific_properties(self, mock_usa_client, spending_response):
        """Test recipient-specific properties."""
        first_result = spending_response["results"][0]

        recipient_spending = RecipientSpending(first_result, mock_usa_client)

        # Test properties using fixture values
        assert recipient_spending.uei == first_result["uei"]
        assert recipient_spending.duns == first_result["code"]  # Should return code field
        assert recipient_spending.name == titlecase_name(first_result["name"])
        assert recipient_spending.amount == first_result["amount"]
        assert_decimal_equal(recipient_spending.total_outlays, first_result["total_outlays"])

    def test_properties_with_none_values(self, mock_usa_client):
        """Test properties when values are None."""
        data = {"recipient_id": None, "uei": None, "code": None}
        recipient_spending = RecipientSpending(data, mock_usa_client)

        assert recipient_spending.recipient_id is None
        assert recipient_spending.uei is None
        assert recipient_spending.duns is None

    def test_repr(self, mock_usa_client, spending_response):
        """Test string representation of RecipientSpending."""
        first_result = spending_response["results"][0]

        recipient_spending = RecipientSpending(first_result, mock_usa_client)

        repr_str = repr(recipient_spending)
        # Test using dynamic fixture values
        assert titlecase_name(first_result["name"]) in repr_str
        # Format the amount as it would appear in repr (with commas)
        expected_amount = round_to_millions(first_result["amount"])
        assert expected_amount in repr_str
        assert "RecipientSpending" in repr_str

    def test_repr_with_none_values(self, mock_usa_client):
        """Test string representation with None values."""
        data = {}
        recipient_spending = RecipientSpending(data, mock_usa_client)

        repr_str = repr(recipient_spending)
        assert "Unknown Recipient" in repr_str
        assert "0.00" in repr_str


class TestRecipientSpendingCount:
    """Test RecipientSpending count functionality via SpendingSearch."""

    def test_count_with_fixture_data(self, mock_usa_client, spending_response):
        """Test count functionality using fixture data."""
        # Modify the fixture to indicate no more pages to prevent infinite loop
        modified_fixture = spending_response.copy()
        modified_fixture["page_metadata"] = {
            "page": 1,
            "hasNext": False,  # Important: Set to False to stop pagination
            "hasPrevious": False,
        }

        # Set up mock to return the modified fixture data
        mock_usa_client.set_response(
            mock_usa_client.Endpoints.SPENDING_BY_RECIPIENT, modified_fixture
        )

        # Create a spending search for recipients
        search = SpendingSearch(mock_usa_client).by_recipient()
        count = search.count()

        # The expected count comes from the loaded response, not a recorded total.
        expected_count = len(spending_response["results"])
        assert count == expected_count

        # Verify the API was called once
        assert mock_usa_client.get_request_count() == 1

    def test_count_with_limit_using_fixture_data(self, mock_usa_client, spending_response):
        """Test count with limit using fixture data."""
        # Modify the fixture to indicate no more pages to prevent infinite loop
        modified_fixture = spending_response.copy()
        modified_fixture["page_metadata"] = {
            "page": 1,
            "hasNext": False,  # Important: Set to False to stop pagination
            "hasPrevious": False,
        }

        # Set up mock to return the modified fixture data
        mock_usa_client.set_response(
            mock_usa_client.Endpoints.SPENDING_BY_RECIPIENT, modified_fixture
        )

        # Create a spending search with a limit
        requested_limit = len(spending_response["results"]) // 2
        search = SpendingSearch(mock_usa_client).by_recipient().limit(requested_limit)
        count = search.count()

        assert count == requested_limit

        # Verify the API was called once
        assert mock_usa_client.get_request_count() == 1

    def test_recipient_model_creation_from_search_results(self, mock_usa_client, spending_response):
        """Test that search results create proper RecipientSpending models."""
        # Modify the fixture to indicate no more pages to prevent infinite loop
        modified_fixture = spending_response.copy()
        modified_fixture["page_metadata"] = {
            "page": 1,
            "hasNext": False,  # Important: Set to False to stop pagination
            "hasPrevious": False,
        }

        # Set up mock to return the modified fixture data
        mock_usa_client.set_response(
            mock_usa_client.Endpoints.SPENDING_BY_RECIPIENT, modified_fixture
        )

        # Create a spending search and get first few results
        requested_limit = 3
        search = SpendingSearch(mock_usa_client).by_recipient().limit(requested_limit)
        results = list(search)

        assert len(results) == requested_limit

        # Verify each result is a RecipientSpending model with correct data
        for i, recipient_spending in enumerate(results):
            fixture_result = spending_response["results"][i]

            assert isinstance(recipient_spending, RecipientSpending)
            assert recipient_spending.name == titlecase_name(fixture_result["name"])
            assert_decimal_equal(recipient_spending.amount, fixture_result["amount"])
            assert recipient_spending.uei == fixture_result["uei"]
            assert recipient_spending.duns == fixture_result["code"]
