"""Tests for SubAwardsResource functionality."""

from __future__ import annotations

import pytest

from usaspending.resources.subawards_resource import SubAwardsResource


class TestSubAwardsResource:
    """Test SubAwardsResource functionality."""

    def test_search_creates_query_builder(self, mock_usa_client):
        """Test that search creates a SubAwardsSearch query builder."""
        resource = SubAwardsResource(mock_usa_client)

        query = resource.search()

        # Should return a SubAwardsSearch instance
        assert query.__class__.__name__ == "SubAwardsSearch"
        assert query._client is mock_usa_client

    def test_for_award_creates_query_builder_with_award_id(self, mock_usa_client):
        """Test that for_award creates a SubAwardsSearch with award_id set."""
        resource = SubAwardsResource(mock_usa_client)

        query = resource.for_award("CONT_AWD_123")

        # Should return a SubAwardsSearch instance with award_id set
        assert query.__class__.__name__ == "SubAwardsSearch"
        assert query._award_id == "CONT_AWD_123"
        assert query._client is mock_usa_client

    def test_for_award_strips_whitespace(self, mock_usa_client):
        """Test that for_award strips whitespace from award_id."""
        resource = SubAwardsResource(mock_usa_client)

        query = resource.for_award("  CONT_AWD_123  ")

        assert query._award_id == "CONT_AWD_123"

    def test_for_award_with_empty_id_raises_error(self, mock_usa_client):
        """Test that for_award with empty award_id raises ValidationError."""
        from usaspending.exceptions import ValidationError

        resource = SubAwardsResource(mock_usa_client)

        with pytest.raises(ValidationError, match="award_id cannot be empty"):
            resource.for_award("")

    def test_subawards_query_has_required_methods(self, mock_usa_client):
        """Test that the returned query builder has expected methods."""
        resource = SubAwardsResource(mock_usa_client)

        query = resource.search()

        # Should have inherited QueryBuilder methods
        assert hasattr(query, "limit")
        assert hasattr(query, "page_size")
        assert hasattr(query, "max_pages")
        assert hasattr(query, "count")
        assert hasattr(query, "all")
        assert hasattr(query, "first")
        assert hasattr(query, "__iter__")

        # Should have AwardsSearch filter methods
        assert hasattr(query, "with_award_types")
        assert hasattr(query, "with_keywords")
        assert hasattr(query, "in_time_period")
        assert hasattr(query, "for_agency")

        # Should have SubAwardsSearch-specific methods
        assert hasattr(query, "for_award")

    def test_subawards_query_chaining(self, mock_usa_client):
        """Test that query builder methods can be chained."""
        resource = SubAwardsResource(mock_usa_client)

        query = (
            resource.search()
            .with_award_types("A", "B", "C")
            .for_award("CONT_AWD_123")
            .limit(10)
            .page_size(25)
        )

        assert query._award_id == "CONT_AWD_123"
        assert query._total_limit == 10
        assert query._page_size == 25

    def test_for_award_convenience_method(self, mock_usa_client):
        """Test that for_award is equivalent to search().for_award()."""
        resource = SubAwardsResource(mock_usa_client)

        # Using convenience method
        query1 = resource.for_award("CONT_AWD_123")

        # Using chained method
        query2 = resource.search().for_award("CONT_AWD_123")

        # Both should have the same award_id set
        assert query1._award_id == "CONT_AWD_123"
        assert query2._award_id == "CONT_AWD_123"
