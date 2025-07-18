"""Tests for TransactionsResource functionality."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from usaspending.resources.transactions_resource import TransactionsResource


class TestTransactionsResource:
    """Test TransactionsResource functionality."""
    
    def test_for_award_creates_query_builder(self, mock_client):
        """Test that for_award creates a TransactionsSearch query builder."""
        resource = TransactionsResource(mock_client)
        
        query = resource.for_award("CONT_AWD_123")
        
        # Should return a TransactionsSearch instance
        assert query.__class__.__name__ == "TransactionsSearch"
        assert query._award_id == "CONT_AWD_123"
        assert query._client is mock_client
    
    def test_for_award_with_empty_id_raises_error(self, mock_client):
        """Test that for_award with empty award_id raises ValidationError."""
        from usaspending.exceptions import ValidationError
        
        resource = TransactionsResource(mock_client)
        
        with pytest.raises(ValidationError, match="award_id cannot be empty"):
            resource.for_award("")
    
    def test_for_award_strips_whitespace(self, mock_client):
        """Test that for_award strips whitespace from award_id."""
        resource = TransactionsResource(mock_client)
        
        query = resource.for_award("  CONT_AWD_123  ")
        
        assert query._award_id == "CONT_AWD_123"
    
    def test_transactions_query_has_required_methods(self, mock_client):
        """Test that the returned query builder has expected methods."""
        resource = TransactionsResource(mock_client)
        
        query = resource.for_award("CONT_AWD_123")
        
        # Should have inherited QueryBuilder methods
        assert hasattr(query, 'limit')
        assert hasattr(query, 'page_size')
        assert hasattr(query, 'max_pages')
        assert hasattr(query, 'count')
        assert hasattr(query, 'all')
        assert hasattr(query, 'first')
        assert hasattr(query, '__iter__')
    
    def test_transactions_query_chaining(self, mock_client):
        """Test that query builder methods can be chained."""
        resource = TransactionsResource(mock_client)
        
        query = resource.for_award("CONT_AWD_123").limit(10).page_size(25)
        
        assert query._award_id == "CONT_AWD_123"
        assert query._total_limit == 10
        assert query._page_size == 25