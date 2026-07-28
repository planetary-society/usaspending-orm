"""Tests for ClientSideQueryBuilder."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Callable

import pytest

from usaspending.queries.client_side_query_builder import ClientSideQueryBuilder
from usaspending.queries.filters import (
    KeywordsFilter,
    SimpleListFilter,
    SimpleStringFilter,
)


class DefCodesQuery(ClientSideQueryBuilder[dict[str, Any]]):
    """Client-side query for agency def_codes entries."""

    def __init__(
        self,
        items: Iterable[Any],
        transform: Callable[[Any], Any] | None = None,
        keyword_fields: Sequence[str] | None = None,
    ) -> None:
        """Initialize the def_codes query builder.

        Args:
            items (Iterable[Any]): Source items to query.
            transform (Optional[Callable[[Any], Any]]): Optional transformer.
            keyword_fields (Optional[Sequence[str]]): Fields used for keyword
                searches.
        """
        keyword_fields = keyword_fields or ["public_law"]
        super().__init__(
            items,
            transform=transform,
            keyword_fields=keyword_fields,
        )

    def disaster(self, value: str) -> DefCodesQuery:
        """Filter def_codes by disaster type.

        Args:
            value (str): Disaster type value.

        Returns:
            DefCodesQuery: Filtered query.
        """
        return self._add_filter_object(SimpleStringFilter(key="disaster", value=value))

    def codes(self, *codes: str) -> DefCodesQuery:
        """Filter def_codes by code values.

        Args:
            *codes (str): One or more def code values.

        Returns:
            DefCodesQuery: Filtered query.
        """
        return self._add_filter_object(SimpleListFilter(key="code", values=list(codes)))

    def public_law_contains(self, text: str) -> DefCodesQuery:
        """Filter def_codes by a substring in public_law.

        Args:
            text (str): Substring to match within public_law.

        Returns:
            DefCodesQuery: Filtered query.
        """
        return self._add_filter_object(KeywordsFilter(values=[text]))


@pytest.fixture
def def_codes_query(
    agency_fixture_data: dict[str, Any],
) -> DefCodesQuery:
    """Create a ClientSideQueryBuilder for agency def_codes."""
    def_codes = agency_fixture_data["def_codes"]
    return DefCodesQuery(def_codes)


def test_count_applies_filters(
    def_codes_query: DefCodesQuery,
    agency_fixture_data: dict[str, Any],
) -> None:
    """Ensure count reflects filters, and the bounds the caller set."""
    def_codes = agency_fixture_data["def_codes"]
    expected = sum(1 for item in def_codes if item.get("disaster") == "covid_19")

    filtered = def_codes_query.disaster("covid_19")
    assert filtered.count() == expected

    # max_pages(0) fetches nothing, and limit(1) would allow one row.
    assert filtered.limit(1).max_pages(0).count() == 0


def test_order_by_sorts_results(
    def_codes_query: DefCodesQuery,
    agency_fixture_data: dict[str, Any],
) -> None:
    """Ensure order_by sorts results as expected."""
    def_codes = agency_fixture_data["def_codes"]
    expected_codes = sorted(item["code"] for item in def_codes)

    results = def_codes_query.order_by("code", "asc").all()
    result_codes = [item["code"] for item in results]

    assert result_codes == expected_codes


def test_max_pages_limits_iteration(
    def_codes_query: DefCodesQuery,
    agency_fixture_data: dict[str, Any],
) -> None:
    """Ensure max_pages limits returned results."""
    total_items = len(agency_fixture_data["def_codes"])
    expected = min(total_items, 4)

    results = def_codes_query.page_size(2).max_pages(2).all()
    assert len(results) == expected


def test_filter_predicate(
    def_codes_query: DefCodesQuery,
    agency_fixture_data: dict[str, Any],
) -> None:
    """Ensure keyword filters are applied."""
    def_codes = agency_fixture_data["def_codes"]
    expected = sum(1 for item in def_codes if "emergency" in item.get("public_law", "").lower())

    filtered = def_codes_query.public_law_contains("Emergency")
    assert filtered.count() == expected


def test_getitem_respects_ordering(
    def_codes_query: DefCodesQuery,
    agency_fixture_data: dict[str, Any],
) -> None:
    """Ensure indexing respects ordering and filtering."""
    def_codes = agency_fixture_data["def_codes"]
    expected_codes = sorted(item["code"] for item in def_codes)

    ordered = def_codes_query.order_by("code", "asc")
    assert ordered[0]["code"] == expected_codes[0]
    assert ordered[-1]["code"] == expected_codes[-1]


def test_simple_list_filter(
    def_codes_query: DefCodesQuery,
    agency_fixture_data: dict[str, Any],
) -> None:
    """Ensure list-based filters match on code values."""
    def_codes = agency_fixture_data["def_codes"]
    codes = [def_codes[0]["code"], def_codes[1]["code"]]

    results = def_codes_query.codes(*codes).all()
    result_codes = {item["code"] for item in results}

    assert result_codes == set(codes)


class TestTruthinessOnInMemoryQueries:
    """These hold their rows, so counting beats reading a row through a clone."""

    def test_truthiness_does_not_re_request_the_level(self, mock_usa_client, load_fixture):
        """first() would fetch into a clone, leaving this query to fetch again.

        BaseQuery answers truthiness from one row, which is right for a paginated
        query. Here the rows are already held, so reading one through a narrowed
        clone caches the fetch on the clone and costs the caller a second request.
        """
        mock_usa_client.set_response(
            "/references/filter_tree/tas/", load_fixture("tas_federal_accounts.json")
        )
        query = mock_usa_client.tas.agencies

        assert bool(query) is True
        query.all()

        assert mock_usa_client.get_request_count("/references/filter_tree/tas/") == 1

    def test_truthiness_does_not_sort(self, mock_usa_client, load_fixture):
        """Ordering the whole collection to learn whether it has one row is waste."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/", load_fixture("tas_federal_accounts.json")
        )
        query = mock_usa_client.tas.agencies.order_by("name")
        sorted_calls = []
        original = type(query)._apply_ordering
        type(query)._apply_ordering = lambda self, items: (
            sorted_calls.append(1),
            original(self, items),
        )[1]
        try:
            assert bool(query) is True
        finally:
            type(query)._apply_ordering = original

        assert sorted_calls == []

    def test_an_empty_level_is_falsey(self, mock_usa_client):
        mock_usa_client.set_response("/references/filter_tree/tas/", {"results": []})

        assert not mock_usa_client.tas.agencies


class TestIndexingSeesTheSameCollectionAsIteration:
    """Indexing reads the limited collection, not the source behind it."""

    def test_full_slice_stops_at_the_limit(self, def_codes_query: DefCodesQuery) -> None:
        """A bare slice is the whole query, so limit(3) makes it three rows."""
        limited = def_codes_query.limit(3)

        assert len(limited[:]) == 3
        assert limited[:] == limited.all()

    def test_full_slice_stops_at_max_pages(self, def_codes_query: DefCodesQuery) -> None:
        """max_pages() caps indexing the same way limit() does."""
        capped = def_codes_query.page_size(2).max_pages(2)

        assert len(capped[:]) == 4
        assert capped[:] == capped.all()

    def test_index_past_the_limit_is_out_of_bounds(self, def_codes_query: DefCodesQuery) -> None:
        """Row six exists in the source but not in a query limited to three."""
        limited = def_codes_query.limit(3)

        with pytest.raises(IndexError):
            limited[5]

    def test_negative_index_counts_back_from_the_limit(
        self, def_codes_query: DefCodesQuery
    ) -> None:
        """The last row of a limited query is its third, not the source's last."""
        limited = def_codes_query.limit(3)

        assert limited[-1] == limited.all()[-1]

    def test_a_filter_tree_level_slices_the_same_way(self, mock_usa_client, load_fixture) -> None:
        """The subclass that fetches its rows honors the limit when indexed too."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/", load_fixture("tas_agencies.json")
        )
        limited = mock_usa_client.tas.agencies.limit(3)
        codes = [agency.code for agency in limited.all()]

        assert len(codes) == 3
        assert [agency.code for agency in limited[:]] == codes
