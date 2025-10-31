"""Tests for RecipientsSearch implementation."""

import pytest

from usaspending.queries.recipients_search import RecipientsSearch
from usaspending.models.recipient import Recipient
from tests.mocks.mock_client import MockUSASpendingClient


class TestRecipientsSearchInitialization:
    """Test RecipientsSearch initialization."""

    def test_init_with_client(self, mock_usa_client):
        """Test RecipientsSearch initialization with client."""
        search = RecipientsSearch(mock_usa_client)

        assert search._client is mock_usa_client
        assert search._endpoint == MockUSASpendingClient.Endpoints.RECIPIENT_SEARCH
        assert search._award_type == "all"
        assert search._sort_field == "amount"
        assert search._sort_direction == "desc"
        assert search._keyword is None

    def test_init_creates_querybuilder_properties(self, mock_usa_client):
        """Test that initialization properly inherits QueryBuilder properties."""
        search = RecipientsSearch(mock_usa_client)

        assert search._page_size == 100
        assert search._total_limit is None
        assert search._max_pages is None
        assert hasattr(search, "_filter_objects")


class TestRecipientsSearchPayloadBuilding:
    """Test RecipientsSearch payload construction."""

    @pytest.fixture
    def recipients_search(self, mock_usa_client):
        """Create a RecipientsSearch instance."""
        return RecipientsSearch(mock_usa_client)

    def test_build_payload_defaults(self, recipients_search):
        """Test default payload structure."""
        payload = recipients_search._build_payload(page=1)

        expected = {
            "page": 1,
            "limit": 100,
            "sort": "amount",
            "order": "desc",
            "award_type": "all",
        }
        assert payload == expected

    def test_build_payload_with_keyword(self, recipients_search):
        """Test payload with keyword filter."""
        search = recipients_search.keyword("california")
        payload = search._build_payload(page=1)

        assert payload["keyword"] == "california"
        assert payload["award_type"] == "all"

    def test_build_payload_with_award_type(self, recipients_search):
        """Test payload with award type filter."""
        search = recipients_search.award_type("contracts")
        payload = search._build_payload(page=1)

        assert payload["award_type"] == "contracts"
        assert "keyword" not in payload

    def test_build_payload_with_sorting(self, recipients_search):
        """Test payload with custom sorting."""
        search = recipients_search.order_by("name", "asc")
        payload = search._build_payload(page=1)

        assert payload["sort"] == "name"
        assert payload["order"] == "asc"

    def test_build_payload_with_all_filters(self, recipients_search):
        """Test payload with all filters applied."""
        search = (
            recipients_search.keyword("test corp")
            .award_type("grants")
            .order_by("duns", "asc")
        )
        payload = search._build_payload(page=1)

        expected = {
            "page": 1,
            "limit": 100,
            "sort": "duns",
            "order": "asc",
            "award_type": "grants",
            "keyword": "test corp",
        }
        assert payload == expected

    def test_build_payload_different_page(self, recipients_search):
        """Test payload with different page number."""
        payload = recipients_search._build_payload(page=3)
        assert payload["page"] == 3

    def test_build_payload_with_page_size_limit(self, recipients_search):
        """Test payload respects page size."""
        search = recipients_search.page_size(50)
        payload = search._build_payload(page=1)
        assert payload["limit"] == 50


class TestRecipientsSearchFluentInterface:
    """Test RecipientsSearch fluent interface and immutability."""

    @pytest.fixture
    def recipients_search(self, mock_usa_client):
        """Create a RecipientsSearch instance."""
        return RecipientsSearch(mock_usa_client)

    def test_with_keyword_immutability(self, recipients_search):
        """Test that with_keyword returns new instance."""
        original = recipients_search
        modified = recipients_search.keyword("test")

        assert original is not modified
        assert original._keyword is None
        assert modified._keyword == "test"

    def test_with_keyword_strips_whitespace(self, recipients_search):
        """Test that keyword whitespace is stripped."""
        search = recipients_search.keyword("  test keyword  ")
        assert search._keyword == "test keyword"

    def test_with_keyword_empty_string_sets_none(self, recipients_search):
        """Test that empty keyword is set to None."""
        search = recipients_search.keyword("")
        assert search._keyword is None

    def test_with_award_type_immutability(self, recipients_search):
        """Test that with_award_type returns new instance."""
        original = recipients_search
        modified = recipients_search.award_type("contracts")

        assert original is not modified
        assert original._award_type == "all"
        assert modified._award_type == "contracts"

    def test_order_by_immutability(self, recipients_search):
        """Test that order_by returns new instance."""
        original = recipients_search
        modified = recipients_search.order_by("name", "asc")

        assert original is not modified
        assert original._sort_field == "amount"
        assert original._sort_direction == "desc"
        assert modified._sort_field == "name"
        assert modified._sort_direction == "asc"

    def test_order_by_default_direction(self, recipients_search):
        """Test that order_by uses desc as default direction."""
        search = recipients_search.order_by("name")
        assert search._sort_field == "name"
        assert search._sort_direction == "desc"

    def test_method_chaining(self, recipients_search):
        """Test that methods can be chained together."""
        search = (
            recipients_search.keyword("california")
            .award_type("grants")
            .order_by("name", "asc")
        )

        assert search._keyword == "california"
        assert search._award_type == "grants"
        assert search._sort_field == "name"
        assert search._sort_direction == "asc"


class TestRecipientsSearchCount:
    """Test RecipientsSearch count functionality."""

    @pytest.fixture
    def recipients_search(self, mock_usa_client):
        """Create a RecipientsSearch instance."""
        return RecipientsSearch(mock_usa_client)

    def test_count_calls_correct_endpoint(self, recipients_search, mock_usa_client):
        """Test that count() calls the count endpoint."""
        mock_usa_client.mock_recipient_count(1500)

        count = recipients_search.count()

        assert count == 1500
        # Verify the correct endpoint was called
        last_request = mock_usa_client.get_last_request()
        assert (
            last_request["endpoint"] == MockUSASpendingClient.Endpoints.RECIPIENT_COUNT
        )
        assert last_request["method"] == "POST"

    def test_count_payload_without_filters(self, recipients_search, mock_usa_client):
        """Test count payload with default filters."""
        mock_usa_client.mock_recipient_count(1000)

        recipients_search.count()

        last_request = mock_usa_client.get_last_request()
        expected_payload = {
            "award_type": "all",
        }
        assert last_request["json"] == expected_payload

    def test_count_payload_with_keyword(self, recipients_search, mock_usa_client):
        """Test count payload includes keyword filter."""
        mock_usa_client.mock_recipient_count(500)

        search = recipients_search.keyword("california")
        search.count()

        last_request = mock_usa_client.get_last_request()
        expected_payload = {
            "award_type": "all",
            "keyword": "california",
        }
        assert last_request["json"] == expected_payload

    def test_count_payload_with_award_type(self, recipients_search, mock_usa_client):
        """Test count payload includes award type filter."""
        mock_usa_client.mock_recipient_count(300)

        search = recipients_search.award_type("contracts")
        search.count()

        last_request = mock_usa_client.get_last_request()
        expected_payload = {
            "award_type": "contracts",
        }
        assert last_request["json"] == expected_payload

    def test_count_payload_with_all_filters(self, recipients_search, mock_usa_client):
        """Test count payload includes all applicable filters."""
        mock_usa_client.mock_recipient_count(100)

        search = recipients_search.keyword("test").award_type("grants")
        search.count()

        last_request = mock_usa_client.get_last_request()
        expected_payload = {
            "award_type": "grants",
            "keyword": "test",
        }
        assert last_request["json"] == expected_payload

    def test_count_returns_zero_for_empty_response(
        self, recipients_search, mock_usa_client
    ):
        """Test count returns 0 when API returns no count."""
        mock_usa_client.set_response("/recipient/count/", {})

        count = recipients_search.count()
        assert count == 0


class TestRecipientsSearchIteration:
    """Test RecipientsSearch iteration and pagination."""

    @pytest.fixture
    def recipients_search(self, mock_usa_client):
        """Create a RecipientsSearch instance."""
        return RecipientsSearch(mock_usa_client)

    def test_iteration_single_page(
        self, recipients_search, mock_usa_client, recipients_search_fixture_data
    ):
        """Test iteration over single page of results."""
        # Use fixture data for realistic testing
        fixture_results = recipients_search_fixture_data["results"][:2]
        mock_usa_client.mock_recipient_search(fixture_results)

        results = list(recipients_search)

        assert len(results) == 2
        for result in results:
            assert isinstance(result, Recipient)

        # Verify API call was made
        last_request = mock_usa_client.get_last_request(
            endpoint=MockUSASpendingClient.Endpoints.RECIPIENT_SEARCH
        )
        assert last_request is not None

    def test_iteration_creates_recipient_models(
        self, recipients_search, mock_usa_client
    ):
        """Test that iteration creates proper Recipient model instances."""
        test_data = [
            {
                "id": "test-1-P",
                "name": "Test Recipient 1",
                "duns": "123456789",
                "uei": "TEST123456789",
                "amount": 1000000.0,
                "recipient_level": "P",
            }
        ]
        mock_usa_client.mock_recipient_search(test_data)

        results = list(recipients_search)

        assert len(results) == 1
        recipient = results[0]
        assert isinstance(recipient, Recipient)
        assert recipient._client is mock_usa_client
        # Test that the model can access the raw data
        raw_data = recipient.raw
        assert raw_data["id"] == "test-1-P"
        assert raw_data["name"] == "Test Recipient 1"

    def test_transform_result_method(self, recipients_search):
        """Test that _transform_result creates Recipient instances."""
        test_data = {
            "id": "test-recipient",
            "name": "Test Recipient",
            "amount": 50000.0,
        }

        result = recipients_search._transform_result(test_data)

        assert isinstance(result, Recipient)
        assert result._client is recipients_search._client

    def test_len_calls_count(self, recipients_search, mock_usa_client):
        """Test that len() delegates to count()."""
        mock_usa_client.mock_recipient_count(150)

        length = len(recipients_search)

        assert length == 150
        # Verify count endpoint was called
        last_request = mock_usa_client.get_last_request()
        assert (
            last_request["endpoint"] == MockUSASpendingClient.Endpoints.RECIPIENT_COUNT
        )


class TestRecipientsSearchIntegration:
    """Test RecipientsSearch integration with fixture data."""

    @pytest.fixture
    def recipients_search(self, mock_usa_client):
        """Create a RecipientsSearch instance."""
        return RecipientsSearch(mock_usa_client)

    def test_integration_with_fixture_data(
        self, recipients_search, mock_usa_client, recipients_search_fixture_data
    ):
        """Test integration using real fixture data."""
        fixture_results = recipients_search_fixture_data["results"]
        mock_usa_client.mock_recipient_search(fixture_results)

        results = list(recipients_search.limit(4))

        assert len(results) == 4

        # Test first result matches fixture data
        first_result = results[0]
        first_fixture = fixture_results[0]

        assert isinstance(first_result, Recipient)
        raw_data = first_result.raw
        assert raw_data["id"] == first_fixture["id"]
        assert raw_data["name"] == first_fixture["name"]
        assert raw_data["amount"] == first_fixture["amount"]

    def test_fixture_data_structure_validation(self, recipients_search_fixture_data):
        """Test that fixture data has expected structure."""
        assert "results" in recipients_search_fixture_data
        assert "page_metadata" in recipients_search_fixture_data

        results = recipients_search_fixture_data["results"]
        assert len(results) > 0

        # Test first result has required fields
        first_result = results[0]
        required_fields = ["id", "name", "amount", "recipient_level"]
        for field in required_fields:
            assert field in first_result

    def test_search_with_keyword_filter_integration(
        self, recipients_search, mock_usa_client, recipients_search_fixture_data
    ):
        """Test search with keyword filter using fixture data."""
        fixture_results = recipients_search_fixture_data["results"][:2]
        mock_usa_client.mock_recipient_search(fixture_results)

        search = recipients_search.keyword("california")
        results = list(search)

        assert len(results) == 2

        # Verify the API was called with correct payload
        last_request = mock_usa_client.get_last_request(
            endpoint=MockUSASpendingClient.Endpoints.RECIPIENT_SEARCH
        )
        assert last_request["json"]["keyword"] == "california"


class TestRecipientsSearchErrorHandling:
    """Test RecipientsSearch error handling."""

    @pytest.fixture
    def recipients_search(self, mock_usa_client):
        """Create a RecipientsSearch instance."""
        return RecipientsSearch(mock_usa_client)

    def test_api_error_during_search(self, recipients_search, mock_usa_client):
        """Test handling of API errors during search."""
        mock_usa_client.set_error_response(
            MockUSASpendingClient.Endpoints.RECIPIENT_SEARCH,
            400,
            detail="Invalid search parameters",
        )

        from usaspending.exceptions import APIError

        with pytest.raises(APIError, match="Invalid search parameters"):
            list(recipients_search)

    def test_http_error_during_search(self, recipients_search, mock_usa_client):
        """Test handling of HTTP errors during search."""
        mock_usa_client.set_error_response(
            MockUSASpendingClient.Endpoints.RECIPIENT_SEARCH,
            500,
            error_message="Internal server error",
        )

        from usaspending.exceptions import HTTPError

        with pytest.raises(HTTPError, match="Internal server error"):
            list(recipients_search)

    def test_api_error_during_count(self, recipients_search, mock_usa_client):
        """Test handling of API errors during count."""
        mock_usa_client.set_error_response(
            MockUSASpendingClient.Endpoints.RECIPIENT_COUNT,
            400,
            detail="Invalid count parameters",
        )

        from usaspending.exceptions import APIError

        with pytest.raises(APIError, match="Invalid count parameters"):
            recipients_search.count()

    def test_empty_response_handling(self, recipients_search, mock_usa_client):
        """Test handling of empty responses."""
        mock_usa_client.mock_recipient_search([])

        results = list(recipients_search)
        assert len(results) == 0
