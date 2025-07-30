"""Tests for SpendingResource functionality."""

from __future__ import annotations

from usaspending.resources.spending_resource import SpendingResource
from usaspending.resources.base_resource import BaseResource
from usaspending.queries.spending_search import SpendingSearch


class TestSpendingResourceInitialization:
    """Test SpendingResource initialization."""
    
    def test_init(self, mock_usa_client):
        """Test SpendingResource initialization."""
        resource = SpendingResource(mock_usa_client)
        
        assert resource._client is mock_usa_client
        assert isinstance(resource, BaseResource)
    
    def test_client_property(self, mock_usa_client):
        """Test client property access."""
        resource = SpendingResource(mock_usa_client)
        
        assert resource.client is mock_usa_client


class TestSpendingResourceMethods:
    """Test SpendingResource methods."""
    
    def test_search_returns_spending_search(self, mock_usa_client):
        """Test that search() returns SpendingSearch instance."""
        resource = SpendingResource(mock_usa_client)
        
        search = resource.search()
        
        assert isinstance(search, SpendingSearch)
        assert search._client is mock_usa_client
    
    def test_search_creates_new_instance_each_time(self, mock_usa_client):
        """Test that search() creates new instances each time."""
        resource = SpendingResource(mock_usa_client)
        
        search1 = resource.search()
        search2 = resource.search()
        
        assert search1 is not search2
        assert isinstance(search1, SpendingSearch)
        assert isinstance(search2, SpendingSearch)