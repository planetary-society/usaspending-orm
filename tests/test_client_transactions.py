"""Tests for client transactions integration."""

from __future__ import annotations

import pytest

from usaspending.client import USASpending
from usaspending.config import Config


class TestClientTransactionsIntegration:
    """Test that transactions resource is properly integrated with client."""
    
    def test_client_has_transactions_property(self):
        """Test that USASpending client has transactions property."""
        config = Config(cache_backend="memory", rate_limit_calls=1000)
        client = USASpending(config)
        
        assert hasattr(client, 'transactions')
        assert client.transactions is not None
    
    def test_transactions_resource_type(self):
        """Test that transactions property returns TransactionsResource."""
        config = Config(cache_backend="memory", rate_limit_calls=1000)
        client = USASpending(config)
        
        transactions = client.transactions
        assert transactions.__class__.__name__ == "TransactionsResource"
    
    def test_transactions_for_award_integration(self):
        """Test the full integration chain: client.transactions.for_award()."""
        config = Config(cache_backend="memory", rate_limit_calls=1000)
        client = USASpending(config)
        
        query = client.transactions.for_award("CONT_AWD_123")
        
        assert query.__class__.__name__ == "TransactionsSearch"
        assert query._award_id == "CONT_AWD_123"
        assert query._client is client
    
    def test_transactions_resource_lazy_loading(self):
        """Test that transactions resource is lazy-loaded."""
        config = Config(cache_backend="memory", rate_limit_calls=1000)
        client = USASpending(config)
        
        # Should not exist initially
        assert "transactions" not in client._resources
        
        # Access should create it
        transactions = client.transactions
        assert "transactions" in client._resources
        assert client._resources["transactions"] is transactions
        
        # Second access should return same instance
        transactions2 = client.transactions
        assert transactions2 is transactions