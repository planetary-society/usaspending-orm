"""Tests for client transactions integration."""

from __future__ import annotations

class TestClientTransactionsIntegration:
    """Test that transactions resource is properly integrated with client."""
    
    def test_client_has_transactions_property(self, mock_usa_client):
        """Test that USASpending client has transactions property."""
        
        assert hasattr(mock_usa_client, 'transactions')
        assert mock_usa_client.transactions is not None
    
    def test_transactions_resource_type(self, mock_usa_client):
        transactions = mock_usa_client.transactions
        assert transactions.__class__.__name__ == "TransactionsResource"
    
    def test_transactions_for_award_integration(self, mock_usa_client):

        query = mock_usa_client.transactions.for_award("CONT_AWD_123")
        
        assert query.__class__.__name__ == "TransactionsSearch"
        assert query._award_id == "CONT_AWD_123"
        assert query._client is mock_usa_client
    
    def test_transactions_resource_lazy_loading(self, mock_usa_client):
        
        # Should not exist initially
        assert "transactions" not in mock_usa_client._resources
        
        # Access should create it
        transactions = mock_usa_client.transactions
        assert "transactions" in mock_usa_client._resources
        assert mock_usa_client._resources["transactions"] is transactions
        
        # Second access should return same instance
        transactions2 = mock_usa_client.transactions
        assert transactions2 is transactions