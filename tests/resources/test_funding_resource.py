"""Tests for FundingResource functionality."""

from __future__ import annotations

import pytest

from usaspending.resources.funding_resource import FundingResource


class TestFundingResource:
    """Test FundingResource functionality."""

    def test_for_award_creates_query_builder(self, mock_usa_client):
        """Test that for_award creates a FundingSearch query builder."""
        resource = FundingResource(mock_usa_client)

        query = resource.award_id("CONT_AWD_123")

        # Should return a FundingSearch instance
        assert query.__class__.__name__ == "FundingSearch"
        assert query._award_id == "CONT_AWD_123"
        assert query._client is mock_usa_client

    def test_for_award_with_empty_id_raises_error(self, mock_usa_client):
        """Test that for_award with empty award_id raises ValidationError."""
        from usaspending.exceptions import ValidationError

        resource = FundingResource(mock_usa_client)

        with pytest.raises(ValidationError, match="award_id cannot be empty"):
            resource.award_id("")

    def test_for_award_strips_whitespace(self, mock_usa_client):
        """Test that for_award strips whitespace from award_id."""
        resource = FundingResource(mock_usa_client)

        query = resource.award_id("  CONT_AWD_123  ")

        assert query._award_id == "CONT_AWD_123"

    def test_funding_query_has_required_methods(self, mock_usa_client):
        """Test that the returned query builder has expected methods."""
        resource = FundingResource(mock_usa_client)

        query = resource.award_id("CONT_AWD_123")

        # Should have inherited QueryBuilder methods
        assert hasattr(query, "limit")
        assert hasattr(query, "page_size")
        assert hasattr(query, "max_pages")
        assert hasattr(query, "count")
        assert hasattr(query, "all")
        assert hasattr(query, "first")
        assert hasattr(query, "__iter__")

        # Should have FundingSearch-specific methods
        assert hasattr(query, "for_award")
        assert hasattr(query, "order_by")

    def test_funding_query_chaining(self, mock_usa_client):
        """Test that query builder methods can be chained."""
        resource = FundingResource(mock_usa_client)

        query = (
            resource.award_id("CONT_AWD_123")
            .order_by("fiscal_date", "asc")
            .limit(10)
            .page_size(25)
        )

        assert query._award_id == "CONT_AWD_123"
        assert query._sort_field == "reporting_fiscal_date"
        assert query._sort_order == "asc"
        assert query._total_limit == 10
        assert query._page_size == 25

    def test_resource_has_client_reference(self, mock_usa_client):
        """Test that resource maintains reference to client."""
        resource = FundingResource(mock_usa_client)

        assert resource._client is mock_usa_client
        assert resource.client is mock_usa_client
