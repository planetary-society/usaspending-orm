"""Tests for TransactionsSearch query builder."""

import pytest

from usaspending.models.transaction import Transaction
from usaspending.queries.transactions_search import TransactionsSearch


class TestTransactionsSearchIndexing:
    """Test TransactionsSearch indexing and slicing support."""

    @pytest.fixture
    def transactions_data(self):
        """Create sample transaction data."""
        return [
            {
                "id": f"id_{i}",
                "modification_number": str(i),
                "action_date": f"2024-01-{i+1:02d}",
                "federal_action_obligation": 1000.0 * i,
                "description": f"Transaction {i}"
            }
            for i in range(20)
        ]

    @pytest.fixture
    def setup_client(self, mock_usa_client, transactions_data):
        """Setup client with mocked transaction responses."""
        # Mock transactions endpoint - match page_size used in tests
        mock_usa_client.set_paginated_response(
            "/transactions/",
            transactions_data,
            page_size=5
        )
        
        # Mock count endpoint
        mock_usa_client.set_response(
            "/awards/count/transaction/CONT_AWD_123/",
            {"transactions": len(transactions_data)}
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
            .since("2024-01-11") # matches 2024-01-11 onwards (index 10+)
        )
        
        # After filter, index 0 is original index 10
        item = query[0]
        assert item.modification_number == "10"
        
        item = query[5]
        assert item.modification_number == "15"

    def test_getitem_slice_with_client_filters(self, setup_client, transactions_data):
        """Test slicing with client filters."""
        # Filter: Transactions before Jan 10th (indices 0-9)
        query = (
            TransactionsSearch(setup_client)
            .award_id("CONT_AWD_123")
            .until("2024-01-10")
        )
        
        # Slice first 5 filtered items
        items = query[0:5]
        
        assert len(items) == 5
        assert items[0].modification_number == "0"
        assert items[4].modification_number == "4"

    def test_getitem_out_of_bounds_with_filters(self, setup_client):
        """Test out of bounds access with filters."""
        query = (
            TransactionsSearch(setup_client)
            .award_id("CONT_AWD_123")
            .since("2099-01-01") # Matches nothing
        )
        
        with pytest.raises(IndexError):
            _ = query[0]
