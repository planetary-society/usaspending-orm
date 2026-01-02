"""Tests for RecipientQuery implementation."""

from __future__ import annotations

from typing import Any, Callable

import pytest
from tests.mocks import MockUSASpendingClient

from usaspending.exceptions import ValidationError
from usaspending.models.recipient import Recipient
from usaspending.queries.recipient_query import RecipientQuery


def set_recipient_fixture(
    mock_usa_client: MockUSASpendingClient,
    load_fixture: Callable[[str], dict[str, Any]],
    recipient_id: str,
) -> str:
    """Set a recipient fixture response for a specific recipient id.

    Args:
        mock_usa_client: Mock client used for request handling.
        load_fixture: Fixture loader function.
        recipient_id: Recipient id to inject into fixture data.

    Returns:
        The endpoint configured for the mock response.
    """
    endpoint = f"/recipient/{recipient_id}/"
    data = load_fixture("recipient_university.json")
    data["recipient_id"] = recipient_id
    mock_usa_client.set_response(endpoint, data)
    return endpoint


class TestRecipientQueryInitialization:
    """Test RecipientQuery initialization."""

    def test_init_with_client(self, mock_usa_client: MockUSASpendingClient) -> None:
        """Test RecipientQuery initialization with client."""
        query = RecipientQuery(mock_usa_client)

        assert query._client is mock_usa_client
        assert query._endpoint == "/recipient/"


class TestRecipientQueryValidation:
    """Test RecipientQuery input validation."""

    @pytest.fixture
    def recipient_query(self, mock_usa_client: MockUSASpendingClient) -> RecipientQuery:
        """Create a RecipientQuery instance."""
        return RecipientQuery(mock_usa_client)

    def test_find_by_id_empty_raises_validation_error(
        self, recipient_query: RecipientQuery
    ) -> None:
        """Test that empty recipient_id raises ValidationError."""
        with pytest.raises(ValidationError, match="recipient_id is required"):
            recipient_query.find_by_id("")

    def test_find_by_id_invalid_year_raises_validation_error(
        self, recipient_query: RecipientQuery
    ) -> None:
        """Test that invalid year raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid fiscal year"):
            recipient_query.find_by_id("abc123-R", year=2007)


class TestRecipientQueryExecution:
    """Test RecipientQuery execution and API calls."""

    @pytest.fixture
    def recipient_query(self, mock_usa_client: MockUSASpendingClient) -> RecipientQuery:
        """Create a RecipientQuery instance."""
        return RecipientQuery(mock_usa_client)

    def test_find_by_id_cleans_recipient_id_suffix(
        self,
        recipient_query: RecipientQuery,
        mock_usa_client: MockUSASpendingClient,
        load_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """Test that recipient_id list suffix is cleaned before request."""
        raw_id = "abc123-['C','R']"
        cleaned_id = "abc123-R"
        endpoint = set_recipient_fixture(mock_usa_client, load_fixture, cleaned_id)

        recipient = recipient_query.find_by_id(raw_id)

        assert isinstance(recipient, Recipient)
        assert recipient._client is mock_usa_client

        last_request = mock_usa_client.get_last_request()
        assert last_request["endpoint"] == endpoint

    def test_find_by_id_with_year_sets_params(
        self,
        recipient_query: RecipientQuery,
        mock_usa_client: MockUSASpendingClient,
        load_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """Test that year parameter is sent as a query param."""
        recipient_id = "abc123-R"
        endpoint = set_recipient_fixture(mock_usa_client, load_fixture, recipient_id)

        recipient = recipient_query.find_by_id(recipient_id, year=2024)

        assert isinstance(recipient, Recipient)
        last_request = mock_usa_client.get_last_request(endpoint)
        assert last_request["params"] == {"year": "2024"}

    def test_find_by_id_without_year_has_no_params(
        self,
        recipient_query: RecipientQuery,
        mock_usa_client: MockUSASpendingClient,
        load_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """Test that year is not persisted between calls."""
        recipient_id = "abc123-R"
        endpoint = set_recipient_fixture(mock_usa_client, load_fixture, recipient_id)

        recipient_query.find_by_id(recipient_id, year="latest")
        recipient_query.find_by_id(recipient_id)

        last_request = mock_usa_client.get_last_request(endpoint)
        assert last_request["params"] is None

    def test_find_by_id_with_latest_year(
        self,
        recipient_query: RecipientQuery,
        mock_usa_client: MockUSASpendingClient,
        load_fixture: Callable[[str], dict[str, Any]],
    ) -> None:
        """Test that latest year is passed through as a string param."""
        recipient_id = "abc123-R"
        endpoint = set_recipient_fixture(mock_usa_client, load_fixture, recipient_id)

        recipient_query.find_by_id(recipient_id, year="latest")

        last_request = mock_usa_client.get_last_request(endpoint)
        assert last_request["params"] == {"year": "latest"}
