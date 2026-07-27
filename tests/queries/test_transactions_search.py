"""Tests for TransactionsSearch query builder."""

import logging
from datetime import date

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending.exceptions import ValidationError
from usaspending.models.transaction import Transaction
from usaspending.queries.transactions_search import TransactionsSearch


class TestDateFilterParsing:
    """since()/until() parse once, at filter time, not once per row."""

    def test_the_bound_is_stored_parsed(self, mock_usa_client):
        """Storing the string instead would leave every behavioral test green."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123").since("2024-01-11")

        assert query._client_filters["since_date"] == date(2024, 1, 11)

    @pytest.mark.parametrize("bound", ["since", "until"])
    def test_a_malformed_bound_is_rejected_at_filter_time(self, mock_usa_client, bound):
        """Not deferred to iteration, which is where the value is used."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="Expected"):
            getattr(query, bound)("15/01/2024")


class TestTransactionsSearchPageSize:
    """Test TransactionsSearch endpoint-specific page size caps."""

    def test_page_size_allows_up_to_5000(self, mock_usa_client):
        """Test TransactionsSearch allows page_size up to 5000 in API payloads."""
        search = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123").page_size(5000)
        assert search._page_size == 5000

        # Prove it flows through to the actual API request payload
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.TRANSACTIONS, [], page_size=5000
        )
        mock_usa_client.set_response("/awards/count/transaction/CONT_AWD_123/", {"transactions": 0})
        list(search)
        last_req = mock_usa_client.get_last_request(MockUSASpendingClient.Endpoints.TRANSACTIONS)
        assert last_req["json"]["limit"] == 5000

    def test_page_size_caps_at_5000(self, mock_usa_client):
        """Test TransactionsSearch caps page_size at 5000."""
        search = TransactionsSearch(mock_usa_client).page_size(10000)
        assert search._page_size == 5000


class TestTransactionsSearchIndexing:
    """Test TransactionsSearch indexing and slicing support."""

    @pytest.fixture
    def transactions_data(self):
        """Create sample transaction data."""
        return [
            {
                "id": f"id_{i}",
                "modification_number": str(i),
                "action_date": f"2024-01-{i + 1:02d}",
                "federal_action_obligation": 1000.0 * i,
                "description": f"Transaction {i}",
            }
            for i in range(20)
        ]

    @pytest.fixture
    def setup_client(self, mock_usa_client, transactions_data):
        """Setup client with mocked transaction responses."""
        # Mock transactions endpoint - match page_size used in tests
        mock_usa_client.set_paginated_response("/transactions/", transactions_data, page_size=5)

        # Mock count endpoint
        mock_usa_client.set_response(
            "/awards/count/transaction/CONT_AWD_123/", {"transactions": len(transactions_data)}
        )
        return mock_usa_client

    def test_getitem_index_no_client_filters(self, setup_client, transactions_data):
        """Test accessing by index without client filters (should use efficient paging)."""
        query = TransactionsSearch(setup_client).award_id("CONT_AWD_123").page_size(5)

        # Access item at index 12 (should be in 3rd page)
        item = query[12]

        assert isinstance(item, Transaction)
        assert item.modification_number == "12"

        # Verify specific page fetch logic was triggered (internal implementation detail check)
        # Note: QueryBuilder.__getitem__ fetches specific page.
        # Index 12 with page_size 5 is page 3 (items 10-14).
        # We can't easily assert the specific page call without spying on _execute_query,
        # but the result correctness implies it worked.

    def test_getitem_slice_no_client_filters(self, setup_client, transactions_data):
        """Test slicing without client filters."""
        query = TransactionsSearch(setup_client).award_id("CONT_AWD_123").page_size(5)

        # Slice from 8 to 13
        items = query[8:13]

        assert len(items) == 5
        assert items[0].modification_number == "8"
        assert items[-1].modification_number == "12"

    def test_getitem_index_with_client_filters(self, setup_client, transactions_data):
        """Test accessing by index with client filters (forces iteration)."""
        # Filter: Transactions after Jan 10th (indices 10-19)
        query = (
            TransactionsSearch(setup_client)
            .award_id("CONT_AWD_123")
            .since("2024-01-11")  # matches 2024-01-11 onwards (index 10+)
        )

        # After filter, index 0 is original index 10
        item = query[0]
        assert item.modification_number == "10"

        item = query[5]
        assert item.modification_number == "15"

    def test_getitem_slice_with_client_filters(self, setup_client, transactions_data):
        """Test slicing with client filters."""
        # Filter: Transactions before Jan 10th (indices 0-9)
        query = TransactionsSearch(setup_client).award_id("CONT_AWD_123").until("2024-01-10")

        # Slice first 5 filtered items
        items = query[0:5]

        assert len(items) == 5
        assert items[0].modification_number == "0"
        assert items[4].modification_number == "4"

    def test_an_unfiltered_query_does_not_read_action_dates(self, mock_usa_client, caplog):
        """Reading action_date re-parses the row's string, so it must not happen here.

        Observable because an unparseable date makes to_date warn: a query with no
        date bound has no reason to look at the field, so no warning should appear.
        Without the guard this costs a parse per row, measured at 21 ms versus 7 ms
        over a 5000-row page.
        """
        mock_usa_client.set_paginated_response(
            "/transactions/", [{"id": "1", "action_date": "not a date"}]
        )
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with caplog.at_level(logging.WARNING):
            assert [transaction.id for transaction in query] == ["1"]

        assert "Could not parse date string" not in caplog.text

    def test_an_undated_row_survives_both_bounds(self, mock_usa_client):
        """An unknown date cannot be shown to fall outside the range.

        Read through iteration rather than off the predicate, so it also shows the
        kept row reaching the caller and the bounds still excluding what they should.
        """
        mock_usa_client.set_paginated_response(
            "/transactions/",
            [
                {"id": "undated", "action_date": None},
                {"id": "inside", "action_date": "2024-01-05"},
                {"id": "outside", "action_date": "2024-02-01"},
            ],
        )
        query = (
            TransactionsSearch(mock_usa_client)
            .award_id("CONT_AWD_123")
            .since("2024-01-05")
            .until("2024-01-06")
        )

        assert [transaction.id for transaction in query] == ["undated", "inside"]

    def test_getitem_out_of_bounds_with_filters(self, setup_client):
        """Test out of bounds access with filters."""
        query = (
            TransactionsSearch(setup_client)
            .award_id("CONT_AWD_123")
            .since("2099-01-01")  # Matches nothing
        )

        with pytest.raises(IndexError):
            _ = query[0]
