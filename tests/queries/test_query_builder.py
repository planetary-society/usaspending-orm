# tests/queries/test_query_builder.py
"""Tests for QueryBuilder base class functionality.

Tests cover:
- Default result limit enforcement from config
- Count caching to avoid redundant API calls
"""

from __future__ import annotations

from tests.mocks.mock_client import MockUSASpendingClient


class TestDefaultResultLimit:
    """Tests for config.default_result_limit enforcement in __iter__()."""

    def test_default_limit_applied_when_no_explicit_limit(
        self, mock_usa_client, client_config
    ):
        """Default limit from config should be applied when no explicit limit set."""
        client_config(default_result_limit=5)

        # Mock more items than the limit
        items = [{"Award ID": f"AWD-{i}"} for i in range(20)]
        mock_usa_client.mock_award_search(items, page_size=10)

        search = mock_usa_client.awards.search().contracts()
        results = list(search)

        assert len(results) == 5

    def test_explicit_limit_overrides_default(self, mock_usa_client, client_config):
        """Explicit limit() should override the default config limit."""
        client_config(default_result_limit=5)

        items = [{"Award ID": f"AWD-{i}"} for i in range(20)]
        mock_usa_client.mock_award_search(items, page_size=10)

        search = mock_usa_client.awards.search().contracts().limit(10)
        results = list(search)

        # Explicit limit of 10 should override default of 5
        assert len(results) == 10

    def test_no_default_limit_when_config_is_none(self, mock_usa_client, client_config):
        """When default_result_limit is None, all items should be returned."""
        client_config(default_result_limit=None)

        items = [{"Award ID": f"AWD-{i}"} for i in range(20)]
        mock_usa_client.mock_award_search(items, page_size=10)

        search = mock_usa_client.awards.search().contracts()
        results = list(search)

        # All 20 items should be returned
        assert len(results) == 20

    def test_default_limit_stops_pagination_early(self, mock_usa_client, client_config):
        """Default limit should stop pagination before fetching all pages."""
        client_config(default_result_limit=5)

        # 20 items with page_size=3 would normally require 7 pages
        items = [{"Award ID": f"AWD-{i}"} for i in range(20)]
        mock_usa_client.mock_award_search(items, page_size=3)

        search = mock_usa_client.awards.search().contracts()
        results = list(search)

        assert len(results) == 5

        # Should have fetched only 2 pages (3 + 3 = 6 items available, limited to 5)
        request_count = mock_usa_client.get_request_count(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH
        )
        assert request_count == 2


class TestCountCaching:
    """Tests for _get_cached_count() and count caching behavior.

    Note: The public count() method always calls the API.
    Caching is internal via _get_cached_count(), used by __getitem__.
    """

    def test_count_method_does_not_cache(self, mock_usa_client):
        """Calling count() directly always hits the API (no caching)."""
        mock_usa_client.mock_award_count(contracts=100)

        search = mock_usa_client.awards.search().contracts()

        # Call count twice - both should hit the API
        count1 = search.count()
        count2 = search.count()

        assert count1 == 100
        assert count2 == 100

        # Count endpoint should be called twice (no caching on direct count() calls)
        request_count = mock_usa_client.get_request_count(
            MockUSASpendingClient.Endpoints.AWARD_COUNT
        )
        assert request_count == 2

    def test_getitem_uses_cached_count(self, mock_usa_client):
        """Accessing items by index should cache and reuse count."""
        mock_usa_client.mock_award_count(contracts=50)
        items = [{"Award ID": f"AWD-{i}"} for i in range(50)]
        mock_usa_client.mock_award_search(items, page_size=10)

        search = mock_usa_client.awards.search().contracts()

        # Access multiple items by index
        _ = search[0]
        _ = search[1]
        _ = search[2]

        # Count should only be fetched once despite multiple index accesses
        request_count = mock_usa_client.get_request_count(
            MockUSASpendingClient.Endpoints.AWARD_COUNT
        )
        assert request_count == 1

    def test_slice_uses_cached_count(self, mock_usa_client):
        """Accessing slices should cache and reuse count."""
        mock_usa_client.mock_award_count(contracts=50)
        items = [{"Award ID": f"AWD-{i}"} for i in range(50)]
        mock_usa_client.mock_award_search(items, page_size=10)

        search = mock_usa_client.awards.search().contracts()

        # Access multiple slices
        _ = search[0:5]
        _ = search[5:10]

        # Count should only be fetched once despite multiple slice accesses
        request_count = mock_usa_client.get_request_count(
            MockUSASpendingClient.Endpoints.AWARD_COUNT
        )
        assert request_count == 1

    def test_cached_count_not_shared_between_clones(self, mock_usa_client):
        """Cloned queries should have independent count caches."""
        mock_usa_client.mock_award_count(contracts=100, grants=50)

        # Create two separate queries via cloning
        base_search = mock_usa_client.awards.search()
        contracts_search = base_search.contracts()
        grants_search = base_search.grants()

        # Each should make its own count request
        contracts_count = contracts_search.count()
        grants_count = grants_search.count()

        assert contracts_count == 100
        assert grants_count == 50

        # Count endpoint should be called twice (once per query)
        request_count = mock_usa_client.get_request_count(
            MockUSASpendingClient.Endpoints.AWARD_COUNT
        )
        assert request_count == 2
