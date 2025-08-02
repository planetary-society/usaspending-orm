"""Integration tests for spending functionality."""

from __future__ import annotations

from usaspending.client import USASpending
from usaspending.resources.spending_resource import SpendingResource
from usaspending.queries.spending_search import SpendingSearch


class TestSpendingIntegration:
    """Test spending integration with client."""

    def test_client_has_spending_property(self):
        """Test that USASpending client has spending property."""
        client = USASpending()

        assert hasattr(client, "spending")
        assert isinstance(client.spending, SpendingResource)

    def test_spending_search_method_chaining(self):
        """Test spending search method chaining."""
        client = USASpending()

        # Test recipient search chaining
        recipient_search = client.spending.search().by_recipient().for_agency("NASA")
        assert isinstance(recipient_search, SpendingSearch)
        assert recipient_search._category == "recipient"
        assert len(recipient_search._filter_objects) == 1

        # Test district search chaining
        district_search = (
            client.spending.search().by_district().spending_level("awards")
        )
        assert isinstance(district_search, SpendingSearch)
        assert district_search._category == "district"
        assert district_search._spending_level == "awards"

    def test_spending_search_complex_chaining(self):
        """Test complex spending search method chaining."""
        client = USASpending()

        search = (
            client.spending.search()
            .by_recipient()
            .for_agency("NASA")
            .for_fiscal_year(2024)
            .with_recipient_search_text("Lockheed")
            .spending_level("transactions")
            .limit(50)
        )

        assert isinstance(search, SpendingSearch)
        assert search._category == "recipient"
        assert search._spending_level == "transactions"
        assert search._total_limit == 50
        assert (
            len(search._filter_objects) == 3
        )  # agency, time period, recipient search text
