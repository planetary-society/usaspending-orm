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
    """Ensure count reflects filters but ignores limits."""
    def_codes = agency_fixture_data["def_codes"]
    expected = sum(1 for item in def_codes if item.get("disaster") == "covid_19")

    filtered = def_codes_query.disaster("covid_19").limit(1).max_pages(0)
    assert filtered.count() == expected


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
