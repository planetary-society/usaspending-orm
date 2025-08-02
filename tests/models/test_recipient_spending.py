"""Tests for RecipientSpending model functionality."""

from __future__ import annotations

from usaspending.models import RecipientSpending, Spending, Recipient
from usaspending.queries.spending_search import SpendingSearch
from usaspending.utils.formatter import contracts_titlecase, round_to_millions
from tests.conftest import load_json_fixture


class TestRecipientSpendingInitialization:
    """Test RecipientSpending model initialization."""

    def test_init_with_dict_data(self, mock_usa_client):
        """Test RecipientSpending initialization with dictionary data."""
        # Load fixture data and use the first result
        fixture_data = load_json_fixture("spending_by_recipient.json")
        first_result = fixture_data["results"][0]

        # Add category field for initialization
        data = {**first_result, "category": "recipient"}
        recipient_spending = RecipientSpending(data, mock_usa_client)

        # Test using dynamic fixture values
        assert (
            recipient_spending._data["recipient_id"][:15]
            == first_result["recipient_id"][:15]
        )  # Clean recipient_id
        assert recipient_spending._data["uei"] == first_result["uei"]
        assert recipient_spending._data["name"] == first_result["name"]
        assert recipient_spending._data["code"] == first_result["code"]
        assert recipient_spending._client is not None
        assert isinstance(recipient_spending, RecipientSpending)
        assert isinstance(recipient_spending, Recipient)  # Should inherit from Spending


class TestRecipientSpendingProperties:
    """Test recipient spending properties."""

    def test_recipient_specific_properties(self, mock_usa_client):
        """Test recipient-specific properties."""
        # Load fixture data and use the first result
        fixture_data = load_json_fixture("spending_by_recipient.json")
        first_result = fixture_data["results"][0]

        recipient_spending = RecipientSpending(first_result, mock_usa_client)

        # Test properties using fixture values
        assert recipient_spending.uei == first_result["uei"]
        assert (
            recipient_spending.duns == first_result["code"]
        )  # Should return code field
        assert recipient_spending.name == contracts_titlecase(first_result["name"])
        assert recipient_spending.amount == first_result["amount"]

    def test_properties_with_none_values(self, mock_usa_client):
        """Test properties when values are None."""
        data = {"recipient_id": None, "uei": None, "code": None}
        recipient_spending = RecipientSpending(data, mock_usa_client)

        assert recipient_spending.recipient_id is None
        assert recipient_spending.uei is None
        assert recipient_spending.duns is None

    def test_repr(self, mock_usa_client):
        """Test string representation of RecipientSpending."""
        # Load fixture data and use the first result
        fixture_data = load_json_fixture("spending_by_recipient.json")
        first_result = fixture_data["results"][0]

        recipient_spending = RecipientSpending(first_result, mock_usa_client)

        repr_str = repr(recipient_spending)
        # Test using dynamic fixture values
        assert contracts_titlecase(first_result["name"]) in repr_str
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

    def test_count_with_fixture_data(self, mock_usa_client):
        """Test count functionality using fixture data."""
        # Load the fixture data
        fixture_data = load_json_fixture("spending_by_recipient.json")

        # Modify the fixture to indicate no more pages to prevent infinite loop
        modified_fixture = fixture_data.copy()
        modified_fixture["page_metadata"] = {
            "page": 1,
            "hasNext": False,  # Important: Set to False to stop pagination
            "hasPrevious": False,
        }

        # Set up mock to return the modified fixture data
        mock_usa_client.set_response(
            "/api/v2/search/spending_by_category/recipient/", modified_fixture
        )

        # Create a spending search for recipients
        search = SpendingSearch(mock_usa_client).by_recipient()
        count = search.count()

        # The fixture has 20 recipient results
        expected_count = len(fixture_data["results"])
        assert count == expected_count
        assert count == 20  # Verify actual fixture count

        # Verify the API was called once
        assert mock_usa_client.get_request_count() == 1

    def test_count_with_limit_using_fixture_data(self, mock_usa_client):
        """Test count with limit using fixture data."""
        # Load the fixture data
        fixture_data = load_json_fixture("spending_by_recipient.json")

        # Modify the fixture to indicate no more pages to prevent infinite loop
        modified_fixture = fixture_data.copy()
        modified_fixture["page_metadata"] = {
            "page": 1,
            "hasNext": False,  # Important: Set to False to stop pagination
            "hasPrevious": False,
        }

        # Set up mock to return the modified fixture data
        mock_usa_client.set_response(
            "/api/v2/search/spending_by_category/recipient/", modified_fixture
        )

        # Create a spending search with a limit
        search = SpendingSearch(mock_usa_client).by_recipient().limit(10)
        count = search.count()

        # Should return only 10, not the full 20 from fixture
        assert count == 10

        # Verify the API was called once
        assert mock_usa_client.get_request_count() == 1

    def test_recipient_model_creation_from_search_results(self, mock_usa_client):
        """Test that search results create proper RecipientSpending models."""
        # Load the fixture data
        fixture_data = load_json_fixture("spending_by_recipient.json")

        # Modify the fixture to indicate no more pages to prevent infinite loop
        modified_fixture = fixture_data.copy()
        modified_fixture["page_metadata"] = {
            "page": 1,
            "hasNext": False,  # Important: Set to False to stop pagination
            "hasPrevious": False,
        }

        # Set up mock to return the modified fixture data
        mock_usa_client.set_response(
            "/api/v2/search/spending_by_category/recipient/", modified_fixture
        )

        # Create a spending search and get first few results
        search = SpendingSearch(mock_usa_client).by_recipient().limit(3)
        results = list(search)

        # Verify we got 3 results
        assert len(results) == 3

        # Verify each result is a RecipientSpending model with correct data
        for i, recipient_spending in enumerate(results):
            fixture_result = fixture_data["results"][i]

            assert isinstance(recipient_spending, RecipientSpending)
            assert recipient_spending.name == contracts_titlecase(
                fixture_result["name"]
            )
            assert recipient_spending.amount == fixture_result["amount"]
            assert recipient_spending.uei == fixture_result["uei"]
            assert recipient_spending.duns == fixture_result["code"]
