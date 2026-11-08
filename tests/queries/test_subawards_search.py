"""Tests for SubAwardsSearch query builder."""

from __future__ import annotations

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending.exceptions import ValidationError
from usaspending.models.subaward import SubAward
from usaspending.queries.subawards_search import SubAwardsSearch
from usaspending.utils.textcase import titlecase_name


class TestSubAwardsSearch:
    """Test SubAwardsSearch query builder functionality."""

    @pytest.fixture
    def subawards_response(self, load_fixture):
        """Load subawards fixture data."""
        return load_fixture("awards/search_results_subawards.json")

    def test_subawards_search_initialization(self, mock_usa_client):
        """Test SubAwardsSearch can be initialized."""
        search = SubAwardsSearch(mock_usa_client)
        assert search._client is mock_usa_client
        assert "award_unique_id" not in search.to_filters_payload()

    def test_build_payload_includes_subawards_flag(self, mock_usa_client):
        """Test that payload always includes subawards=true."""
        search = SubAwardsSearch(mock_usa_client).award_type_codes("A", "B", "C")

        payload = search._build_payload(page=1)

        assert payload["subawards"] is True
        assert payload["spending_level"] == "subawards"
        assert "filters" in payload
        assert payload["filters"]["award_type_codes"] == ["A", "B", "C"]

    def test_build_payload_with_award_filter(self, mock_usa_client):
        """Test that payload includes award_unique_id when filtering by award."""
        search = (
            SubAwardsSearch(mock_usa_client)
            .award_type_codes("A", "B", "C")
            .award_id("CONT_AWD_123_456")
        )

        payload = search._build_payload(page=1)

        assert payload["filters"]["award_unique_id"] == "CONT_AWD_123_456"
        assert payload["subawards"] is True
        assert payload["spending_level"] == "subawards"

    def test_transform_result_returns_subaward(self, mock_usa_client, subawards_response):
        """Test that transform_result returns SubAward instances."""

        search = SubAwardsSearch(mock_usa_client)

        subaward_data = subawards_response["results"][0]
        result = search._transform_result(subaward_data)

        assert isinstance(result, SubAward)
        assert result.id == subaward_data["internal_id"]
        expected_name = titlecase_name(subaward_data["Sub-Awardee Name"])
        assert result.sub_awardee_name == expected_name

    def test_get_fields_for_contract_subawards(self, mock_usa_client):
        """Test field selection for contract subawards."""
        search = SubAwardsSearch(mock_usa_client).award_type_codes("A", "B", "C", "D")

        fields = search._get_fields()

        # Should return contract subaward fields
        assert "NAICS" in fields
        assert "PSC" in fields
        assert "Assistance Listing" not in fields

    def test_get_fields_for_grant_subawards(self, mock_usa_client):
        """Test field selection for grant subawards."""
        search = SubAwardsSearch(mock_usa_client).award_type_codes("02", "03", "04", "05")

        fields = search._get_fields()

        # Should return grant subaward fields
        assert "Assistance Listing" in fields
        assert "NAICS" not in fields
        assert "PSC" not in fields

    def test_get_fields_for_mixed_award_types(self, mock_usa_client):
        """Test field selection when mixing contract and grant types returns union."""
        # This should normally raise an error in AwardsSearch validation,
        # but if it gets through, we return all fields
        search = SubAwardsSearch(mock_usa_client)
        search._filter_objects = []  # Clear filters to bypass validation

        # Manually set both contract and grant codes
        from usaspending.queries.filters import SimpleListFilter

        search._filter_objects.append(SimpleListFilter(key="award_type_codes", values=["A", "02"]))

        fields = search._get_fields()

        # Should return union of both field sets
        assert "NAICS" in fields
        assert "PSC" in fields
        assert "Assistance Listing" in fields

    def test_for_award_method(self, mock_usa_client):
        """Test for_award method sets award_id."""
        search = SubAwardsSearch(mock_usa_client).award_id("CONT_AWD_123")

        assert search.to_filters_payload()["award_unique_id"] == "CONT_AWD_123"

    def test_for_award_strips_whitespace(self, mock_usa_client):
        """Test for_award strips whitespace from award_id."""
        search = SubAwardsSearch(mock_usa_client).award_id("  CONT_AWD_123  ")

        assert search.to_filters_payload()["award_unique_id"] == "CONT_AWD_123"

    def test_for_award_empty_raises_error(self, mock_usa_client):
        """Test for_award with empty string raises ValidationError."""
        with pytest.raises(ValidationError, match="award_id cannot be empty"):
            SubAwardsSearch(mock_usa_client).award_id("")

    def test_count_with_award_id(self, mock_usa_client):
        """A scoped count needs no award-type filter and still uses the search scope."""
        endpoint = MockUSASpendingClient.Endpoints.AWARD_COUNT
        mock_usa_client.set_response(endpoint, {"results": {"subcontracts": 7, "subgrants": 0}})

        search = SubAwardsSearch(mock_usa_client).award_id("CONT_AWD_123")
        count = search.count()

        assert count == 7
        mock_usa_client.assert_called_with(
            endpoint=endpoint,
            method="POST",
            json={
                "filters": {"award_unique_id": "CONT_AWD_123"},
                "subawards": True,
                "spending_level": "subawards",
            },
        )

    def test_count_without_award_id(self, mock_usa_client):
        """An unscoped count reads the count endpoint rather than fetching every row."""
        search = SubAwardsSearch(mock_usa_client).award_type_codes("A", "B")
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            {"results": {"subcontracts": 5, "subgrants": 0}},
        )

        assert search.count() == 5
        assert mock_usa_client.get_request_count() == 1
        assert mock_usa_client.get_request_count(MockUSASpendingClient.Endpoints.AWARD_SEARCH) == 0

    def test_filtered_count_and_search_share_scope(self, mock_usa_client):
        query = (
            SubAwardsSearch(mock_usa_client).contracts().award_id("CONT_AWD_123").fiscal_year(2024)
        )
        expected_filters = {
            "award_type_codes": ["A", "B", "C", "D"],
            "award_unique_id": "CONT_AWD_123",
            "time_period": [{"start_date": "2023-10-01", "end_date": "2024-09-30"}],
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            {"results": {"subcontracts": 1, "subgrants": 0}},
        )
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH, [{"internal_id": 1}]
        )

        assert query.to_filters_payload() == expected_filters
        assert query._build_payload(1)["filters"] == expected_filters
        assert query.count() == len(query.all()) == 1
        mock_usa_client.assert_called_with(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            method="POST",
            json={
                "filters": expected_filters,
                "subawards": True,
                "spending_level": "subawards",
            },
        )

    @pytest.mark.parametrize(
        ("counts", "expected"),
        [({"subcontracts": 7, "subgrants": 3}, 10), ({"subgrants": 3}, 3), ({}, 0)],
    )
    def test_count_sums_subaward_buckets(self, mock_usa_client, counts, expected):
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, {"results": counts}
        )
        query = SubAwardsSearch(mock_usa_client).award_id("CONT_AWD_123")

        assert query.count_awards_by_type() == counts
        assert query.count() == expected

    @pytest.mark.parametrize(
        ("limit", "max_pages", "expected", "requests"),
        [(3, 2, 3, 1), (100, 2, 20, 1), (0, 2, 0, 0), (100, 0, 0, 0)],
    )
    def test_count_respects_bounds(self, mock_usa_client, limit, max_pages, expected, requests):
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            {"results": {"subcontracts": 50, "subgrants": 0}},
        )
        query = (
            SubAwardsSearch(mock_usa_client)
            .contracts()
            .page_size(10)
            .limit(limit)
            .max_pages(max_pages)
        )

        assert query.count() == expected
        assert mock_usa_client.get_request_count() == requests

    def test_unscoped_count_still_requires_award_types(self, mock_usa_client):
        mock_usa_client.forbid_requests()
        with pytest.raises(ValidationError, match="award_type_codes"):
            SubAwardsSearch(mock_usa_client).count()

    def test_repeated_award_id_replaces_scope_without_mutating_parent(self, mock_usa_client):
        original = SubAwardsSearch(mock_usa_client).contracts().award_id("CONT_AWD_A")
        replaced = original.award_id("CONT_AWD_B").fiscal_year(2024)

        assert original.to_filters_payload()["award_unique_id"] == "CONT_AWD_A"
        assert replaced.to_filters_payload()["award_unique_id"] == "CONT_AWD_B"
        assert replaced._build_payload(1)["filters"] == replaced.to_filters_payload()

    def test_query_chaining(self, mock_usa_client):
        """Test that SubAwardsSearch supports query chaining."""
        search = (
            SubAwardsSearch(mock_usa_client)
            .award_type_codes("A", "B", "C")
            .award_id("CONT_AWD_123")
            .limit(50)
            .page_size(25)
        )

        assert search.to_filters_payload()["award_unique_id"] == "CONT_AWD_123"
        assert search._total_limit == 50
        assert search._page_size == 25

    def test_inherits_award_search_filters(self, mock_usa_client):
        """Test that SubAwardsSearch inherits filter methods from AwardsSearch."""
        search = SubAwardsSearch(mock_usa_client)

        # Should have all AwardsSearch filter methods
        assert hasattr(search, "keywords")
        assert hasattr(search, "time_period")
        assert hasattr(search, "agency")
        assert hasattr(search, "award_type_codes")
        assert hasattr(search, "place_of_performance_scope")
        assert hasattr(search, "place_of_performance_locations")
        assert hasattr(search, "recipient_locations")
        assert hasattr(search, "award_amounts")

    def test_object_classes_not_supported(self, mock_usa_client):
        """Test that object_classes raises ValidationError for subaward searches."""
        with pytest.raises(ValidationError, match="not supported for subaward"):
            SubAwardsSearch(mock_usa_client).object_classes("10")

    def test_immutability(self, mock_usa_client):
        """Test that SubAwardsSearch maintains immutability."""
        search1 = SubAwardsSearch(mock_usa_client).award_type_codes("A", "B")
        search2 = search1.award_id("CONT_AWD_123")
        search3 = search2.limit(10)

        # Each should be a different instance
        assert search1 is not search2
        assert search2 is not search3

        # Original should not be modified
        assert "award_unique_id" not in search1.to_filters_payload()
        assert search2.to_filters_payload()["award_unique_id"] == "CONT_AWD_123"
        assert search1._total_limit is None
        assert search3._total_limit == 10
