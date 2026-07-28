"""Tests for QueryBuilder list-like behavior (__len__ and __getitem__)."""

from __future__ import annotations

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending.queries.awards_search import AwardsSearch


@pytest.fixture
def three_awards(mock_usa_client):
    """A contracts search over three awards, with its count endpoint mocked."""
    mock_usa_client.mock_award_search(
        [{"generated_internal_id": f"CONT_AWD_{i}"} for i in range(3)]
    )
    return AwardsSearch(mock_usa_client).contracts()


@pytest.fixture
def awards_search(mock_usa_client):
    """Create an AwardsSearch instance with a mock client."""
    return AwardsSearch(mock_usa_client).award_type_codes("A")


class TestTruthiness:
    """`if query:` needs one row, not a count."""

    def test_truthiness_does_not_count(self, mock_usa_client, three_awards):
        """__len__ with no __bool__ made truthiness a count request.

        Worse on the builders with no count endpoint, where counting pages the
        whole result set to answer one bit.
        """
        assert bool(three_awards) is True
        assert mock_usa_client.get_request_count(MockUSASpendingClient.Endpoints.AWARD_COUNT) == 0

    def test_an_empty_query_is_falsey(self, mock_usa_client):
        mock_usa_client.mock_award_search([])
        query = AwardsSearch(mock_usa_client).contracts()

        assert bool(query) is False
        assert not query

    def test_truthiness_reads_one_page_not_all_of_them(self, mock_usa_client):
        """It asks for one row, so a large result set costs one page."""
        mock_usa_client.mock_award_search(
            [{"generated_internal_id": f"CONT_AWD_{i}"} for i in range(250)], page_size=100
        )
        query = AwardsSearch(mock_usa_client).contracts()

        assert bool(query) is True
        assert mock_usa_client.get_request_count() == 1


class TestFirstRespectsLimits:
    """first() must not contradict all() and len() on the same query."""

    def test_a_zero_limit_yields_no_first_row(self, three_awards):
        """first() called limit(1), overriding the caller's zero."""
        query = three_awards.limit(0)

        assert query.all() == []
        assert len(query) == 0
        assert query.first() is None
        assert not query

    def test_zero_max_pages_yields_no_first_row(self, three_awards):
        query = three_awards.max_pages(0)

        assert query.all() == []
        assert query.first() is None

    def test_a_positive_limit_still_yields_the_first_row(self, three_awards):
        assert three_awards.limit(2).first() is not None
        assert three_awards.first() is not None


class TestAllDoesNotCount:
    """all() must not spend a request on a count it throws away."""

    def test_all_does_not_request_a_count(self, mock_usa_client, three_awards):
        """`list(self)` asks for a length hint, which calls __len__ -> count().

        On a paginated query that is a request to the count endpoint whose answer
        is used only to size the list, so every all() cost one request more than
        the identical loop. Asserting on the count endpoint rather than on the
        total is what discriminates the fix from the bug: the mock pre-configures
        that endpoint, so the wasted request never failed a test.
        """
        returned = three_awards.all()

        assert [award.generated_unique_award_id for award in returned] == [
            f"CONT_AWD_{i}" for i in range(3)
        ]
        assert mock_usa_client.get_request_count(MockUSASpendingClient.Endpoints.AWARD_COUNT) == 0
        assert mock_usa_client.get_request_count() == 1


class TestLenMethod:
    """Test the __len__ method implementation."""

    def test_len_returns_count(self, awards_search, mock_usa_client):
        """Test that len() returns the same value as count()."""
        # Mock the count endpoint
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            {
                "results": {
                    "contracts": 42  # 42 contract awards
                }
            },
        )

        # Both should return the same value
        assert len(awards_search) == 42
        assert awards_search.count() == 42

        # Should have called the count endpoint twice
        assert mock_usa_client.get_request_count(MockUSASpendingClient.Endpoints.AWARD_COUNT) == 2

    def test_len_with_filters(self, awards_search, mock_usa_client):
        """Test that len() works with filtered queries."""
        # Mock the count endpoint
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 15}}
        )

        filtered_search = awards_search.agency("DOD")
        assert len(filtered_search) == 15


class TestGetItemMethod:
    """Test the __getitem__ method implementation."""

    def test_positive_index(self, awards_search, mock_usa_client):
        """Test accessing items by positive index."""
        # Mock count
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 250}}
        )

        # Mock the specific page that contains index 42
        # With page_size=100, index 42 is on page 1 (indices 0-99)
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            {
                "results": [{"Award ID": f"AWARD-{i}"} for i in range(100)],
                "page_metadata": {"hasNext": True},
            },
        )

        result = awards_search[42]
        assert result._data["Award ID"] == "AWARD-42"

        # Should have fetched only one page
        assert mock_usa_client.get_request_count(MockUSASpendingClient.Endpoints.AWARD_SEARCH) == 1

    def test_negative_index(self, awards_search, mock_usa_client):
        """Test accessing items by negative index."""
        # Mock count - total 250 items
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 250}}
        )

        # For index -1 (last item), that's index 249, which is on page 3
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            {
                "results": [{"Award ID": f"AWARD-{200 + i}"} for i in range(50)],  # Items 200-249
                "page_metadata": {"hasNext": False},
            },
        )

        result = awards_search[-1]
        assert result._data["Award ID"] == "AWARD-249"

    def test_index_out_of_bounds(self, awards_search, mock_usa_client):
        """Test that out-of-bounds indices raise IndexError."""
        # Mock count
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 10}}
        )

        with pytest.raises(IndexError) as exc_info:
            awards_search[10]  # Valid indices are 0-9
        assert "out of range" in str(exc_info.value)

        with pytest.raises(IndexError) as exc_info:
            awards_search[-11]  # Valid negative indices are -1 to -10
        assert "out of range" in str(exc_info.value)

    def test_slice_simple(self, awards_search, mock_usa_client):
        """Test simple slice operations."""
        # Mock count
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 250}}
        )

        # Request items [5:8] - all on page 1
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            {
                "results": [{"Award ID": f"AWARD-{i}"} for i in range(100)],
                "page_metadata": {"hasNext": True},
            },
        )

        results = awards_search[5:8]
        assert len(results) == 3
        assert results[0]._data["Award ID"] == "AWARD-5"
        assert results[1]._data["Award ID"] == "AWARD-6"
        assert results[2]._data["Award ID"] == "AWARD-7"

    def test_slice_across_pages(self, awards_search, mock_usa_client):
        """Test slice that spans multiple pages."""
        # Mock count
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 250}}
        )

        # Request items [95:105] - spans pages 1 and 2
        mock_usa_client.add_response_sequence(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            [
                {
                    "results": [{"Award ID": f"AWARD-{i}"} for i in range(100)],
                    "page_metadata": {"hasNext": True},
                },
                {
                    "results": [{"Award ID": f"AWARD-{100 + i}"} for i in range(100)],
                    "page_metadata": {"hasNext": True},
                },
            ],
        )

        results = awards_search[95:105]
        assert len(results) == 10
        assert results[0]._data["Award ID"] == "AWARD-95"
        assert results[-1]._data["Award ID"] == "AWARD-104"

        # Should have fetched two pages
        assert mock_usa_client.get_request_count(MockUSASpendingClient.Endpoints.AWARD_SEARCH) == 2

    def test_slice_with_step(self, awards_search, mock_usa_client):
        """Test slice with step parameter."""
        # Mock count
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 250}}
        )

        # For [0:10:2], we need to fetch items 0, 2, 4, 6, 8
        # All are on page 1
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            {
                "results": [{"Award ID": f"AWARD-{i}"} for i in range(100)],
                "page_metadata": {"hasNext": True},
            },
        )

        results = awards_search[0:10:2]
        assert len(results) == 5
        assert results[0]._data["Award ID"] == "AWARD-0"
        assert results[1]._data["Award ID"] == "AWARD-2"
        assert results[2]._data["Award ID"] == "AWARD-4"
        assert results[3]._data["Award ID"] == "AWARD-6"
        assert results[4]._data["Award ID"] == "AWARD-8"

    def test_slice_negative_indices(self, awards_search, mock_usa_client):
        """Test slice with negative indices."""
        # Mock count
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 100}}
        )

        # [-5:] means last 5 items (indices 95-99)
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            {
                "results": [{"Award ID": f"AWARD-{i}"} for i in range(100)],
                "page_metadata": {"hasNext": False},
            },
        )

        results = awards_search[-5:]
        assert len(results) == 5
        assert results[0]._data["Award ID"] == "AWARD-95"
        assert results[-1]._data["Award ID"] == "AWARD-99"

    def test_empty_slice(self, awards_search, mock_usa_client):
        """Test slice that returns empty list."""
        # Mock count
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 100}}
        )

        # Slice with start >= stop returns empty list
        results = awards_search[10:10]
        assert results == []

        results = awards_search[20:10]
        assert results == []

        # No API calls should be made for empty slices
        assert mock_usa_client.get_request_count(MockUSASpendingClient.Endpoints.AWARD_SEARCH) == 0

    def test_invalid_key_type(self, awards_search, mock_usa_client):
        """Test that invalid key types raise TypeError."""
        with pytest.raises(TypeError) as exc_info:
            awards_search["invalid"]
        assert "indices must be integers or slices" in str(exc_info.value)

        with pytest.raises(TypeError) as exc_info:
            awards_search[1.5]
        assert "indices must be integers or slices" in str(exc_info.value)


class TestIntegration:
    """Test integration with existing QueryBuilder functionality."""

    def test_with_filters_and_indexing(self, awards_search, mock_usa_client):
        """Test that indexing works with filtered queries."""
        # Mock count for filtered query
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 50}}
        )

        # Mock results
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            {
                "results": [{"Award ID": f"DOD-AWARD-{i}"} for i in range(50)],
                "page_metadata": {"hasNext": False},
            },
        )

        filtered = awards_search.agency("DOD")

        # Test len()
        assert len(filtered) == 50

        # Test indexing
        item = filtered[10]
        assert item._data["Award ID"] == "DOD-AWARD-10"

        # Test slicing
        items = filtered[0:3]
        assert len(items) == 3
        assert items[0]._data["Award ID"] == "DOD-AWARD-0"

    def test_with_page_size(self, awards_search, mock_usa_client):
        """Test that custom page size is respected."""
        # Mock count
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": {"contracts": 100}}
        )

        # Set custom page size
        search = awards_search.page_size(20)

        # Mock response for page with 20 items
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            {
                "results": [{"Award ID": f"AWARD-{i}"} for i in range(20)],
                "page_metadata": {"hasNext": True},
            },
        )

        # Access item 15 (should be on page 1 with page_size=20)
        item = search[15]
        assert item._data["Award ID"] == "AWARD-15"

        # Check the request was made with correct page size
        last_request = mock_usa_client.get_last_request(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH
        )
        assert last_request["json"]["limit"] == 20


class TestLenRespectsLimits:
    """len() is count(), bounds and all.

    Which figure each bound produces is pinned once per counting mechanism in
    tests/queries/test_count_respects_limits.py. What is left here is the
    delegation itself, on the builder this file is about.
    """

    def test_len_is_the_count_under_bounds(self, awards_search, mock_usa_client):
        """The two cannot disagree, whether or not a bound is set."""
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            {"results": {"contracts": 250}},
        )
        assert len(awards_search) == awards_search.count() == 250

        limited = awards_search.limit(5).max_pages(2)
        assert len(limited) == limited.count() == 5


class TestGetItemRespectsLimits:
    """Test that __getitem__ bounds-checks against effective limits."""

    def test_index_beyond_limit_raises(self, awards_search, mock_usa_client):
        """Indexing beyond limit raises IndexError."""
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            {"results": {"contracts": 250}},
        )
        with pytest.raises(IndexError):
            awards_search.limit(5)[6]

    def test_negative_index_resolves_against_the_bounded_count(
        self, awards_search, mock_usa_client
    ):
        """limit(5)[-1] is the fifth row, not the 250th."""
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            {"results": {"contracts": 250}},
        )
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH,
            [{"Award ID": f"AWARD-{i}"} for i in range(100)],
        )
        # limit(5), index -1 => effective index 4
        result = awards_search.limit(5)[-1]
        assert result._data["Award ID"] == "AWARD-4"
