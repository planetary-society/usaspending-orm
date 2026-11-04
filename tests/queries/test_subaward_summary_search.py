"""Grouped summary filters, count routing and upstream pagination workaround."""

from unittest.mock import patch

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending import SubAwardSummary, SubAwardSummarySearch
from usaspending.exceptions import HTTPError, ValidationError
from usaspending.models.award_types import AWARD_CATEGORIES

SEARCH_ENDPOINT = MockUSASpendingClient.Endpoints.SUBAWARD_SUMMARY
COUNT_ENDPOINT = MockUSASpendingClient.Endpoints.AWARD_COUNT


@pytest.fixture
def query(mock_usa_client):
    return mock_usa_client.awards.subaward_summary()


@pytest.fixture
def rows(load_fixture):
    row = load_fixture("spending_by_subaward_grouped.json")["results"][0]
    return [{**row, "award_generated_internal_id": f"ASST_NON_{index}_080"} for index in range(5)]


def test_resource_returns_fresh_lazy_queries(query, mock_usa_client):
    mock_usa_client.forbid_requests()
    assert isinstance(query, SubAwardSummarySearch)
    assert query is not mock_usa_client.awards.subaward_summary()


def test_empty_filters_and_default_sort_are_sent(query):
    assert query._build_payload(1) == {
        "filters": {},
        "limit": 100,
        "page": 1,
        "sort": "award_generated_internal_id",
        "order": "desc",
    }


def test_filters_sort_and_bounds_survive_cloning(query):
    filtered = (
        query.contracts()
        .grants()
        .award_id("  ASST_NON_EXAMPLE_080  ")
        .fiscal_year(2024)
        .order_by("subaward_count", "asc")
        .page_size(3)
        .limit(5)
        .max_pages(2)
    )
    payload = filtered._clone()._build_payload(2)
    assert {"A", "D", "02", "05"} <= set(payload["filters"]["award_type_codes"])
    assert payload["filters"]["award_unique_id"] == "ASST_NON_EXAMPLE_080"
    assert payload["filters"]["time_period"] == [
        {"start_date": "2023-10-01", "end_date": "2024-09-30"}
    ]
    assert payload["page"] == 2
    assert payload["limit"] == 3
    assert (payload["sort"], payload["order"]) == ("subaward_count", "asc")
    assert filtered._clone()._max_pages == 2
    assert query._build_payload(1)["filters"] == {}
    assert query._sort_field == "award_generated_internal_id"


@pytest.mark.parametrize("codes", [(), ("invalid",)])
def test_invalid_award_type_selection(query, codes):
    with pytest.raises(ValidationError):
        query.award_type_codes(*codes)


@pytest.mark.parametrize("award_id", [None, "", "  "])
def test_invalid_generated_id(query, award_id):
    with pytest.raises(ValidationError, match="award_id"):
        query.award_id(award_id)


@pytest.mark.parametrize(
    "field",
    [
        "award_id",
        "award_generated_internal_id",
        "subaward_count",
        "subaward_obligation",
        "subaward_to_award_ratio",
    ],
)
def test_implemented_sort_fields(query, field):
    assert query.order_by(field)._build_payload(1)["sort"] == field


def test_unimplemented_sort_and_invalid_direction(query):
    with pytest.raises(ValidationError, match="Invalid sort field"):
        query.order_by("award_obligation")
    with pytest.raises(ValidationError, match="Invalid sort direction"):
        query.order_by("subaward_count", "sideways")


def test_unsupported_filters_fail_without_requests(query, mock_usa_client):
    mock_usa_client.forbid_requests()
    with pytest.raises(ValidationError, match="program_activities"):
        query.program_activities({"code": "0001"})
    with (
        pytest.warns(DeprecationWarning),
        pytest.raises(ValidationError, match="program_activities"),
    ):
        query.program_activity(1)


@pytest.mark.parametrize("mixed", [False, True])
def test_count_uses_one_request_and_identical_filters(query, mock_usa_client, mixed):
    if mixed:
        query = query.contracts().grants().award_id("ASST_NON_EXAMPLE_080")
    mock_usa_client.mock_award_count(
        contracts=50001, grants=2, idvs=3, loans=4, direct_payments=5, other=6
    )

    assert query.count() == 50021
    assert mock_usa_client.get_request_count() == 1
    # The count endpoint rejects empty filters, so an unfiltered count names every type.
    every_type = sorted(code for category in AWARD_CATEGORIES for code in category.codes)
    expected = query._build_payload(1)["filters"] if mixed else {"award_type_codes": every_type}
    mock_usa_client.assert_called_with(COUNT_ENDPOINT, "POST", json={"filters": expected})


def test_indexing_counts_once_without_walking_pages(query, mock_usa_client, rows):
    mock_usa_client.mock_award_count(contracts=60000)
    mock_usa_client.set_paginated_response(SEARCH_ENDPOINT, rows, page_size=2)
    query = query.page_size(2)

    assert query[0].award_generated_internal_id == rows[0]["award_generated_internal_id"]
    assert mock_usa_client.get_request_count(COUNT_ENDPOINT) == 1
    assert mock_usa_client.get_request_count(SEARCH_ENDPOINT) == 1
    assert query[1].award_generated_internal_id == rows[1]["award_generated_internal_id"]
    assert mock_usa_client.get_request_count(COUNT_ENDPOINT) == 1


@pytest.mark.parametrize("bound", ["limit", "max_pages"])
def test_zero_bounds_make_no_requests(query, mock_usa_client, bound):
    query = getattr(query, bound)(0)
    mock_usa_client.forbid_requests()

    assert query.count() == len(query) == 0
    assert query.all() == []
    assert not query
    assert query[:1] == []
    with pytest.raises(IndexError):
        query[0]


@pytest.mark.parametrize("row_count,requests", [(0, 1), (4, 3), (5, 3)])
def test_full_pages_continue_despite_false_metadata(
    query, mock_usa_client, rows, row_count, requests
):
    mock_usa_client.set_paginated_response(
        SEARCH_ENDPOINT, rows[:row_count], page_size=2, metadata={"hasNext": False}
    )

    result = query.page_size(2).all()

    assert [summary.raw for summary in result] == rows[:row_count]
    assert all(isinstance(summary, SubAwardSummary) for summary in result)
    assert mock_usa_client.get_request_count(SEARCH_ENDPOINT) == requests
    assert mock_usa_client.get_request_count(COUNT_ENDPOINT) == 0


def test_normalization_does_not_mutate_response(query, mock_usa_client, rows):
    response = {"results": rows[:2], "page_metadata": {"page": 1, "hasNext": False}}
    with patch.object(mock_usa_client, "_make_request", return_value=response):
        normalized = query.page_size(2)._execute_query(1)

    assert normalized["page_metadata"]["hasNext"] is True
    assert response["page_metadata"]["hasNext"] is False


@pytest.mark.parametrize("bound,expected", [("limit", 3), ("max_pages", 4)])
def test_collection_operations_share_bounds(query, mock_usa_client, rows, bound, expected):
    mock_usa_client.mock_award_count(grants=len(rows))
    mock_usa_client.set_paginated_response(
        SEARCH_ENDPOINT, rows, page_size=2, metadata={"hasNext": False}
    )
    query = query.page_size(2)
    query = query.limit(3) if bound == "limit" else query.max_pages(2)

    assert query.count() == len(query) == len(query.all()) == expected
    assert query[-1].raw == rows[expected - 1]
    assert [item.raw for item in query[1:]] == rows[1:expected]
    with pytest.raises(IndexError):
        query[expected]


def test_later_page_errors_propagate(query, mock_usa_client, rows):
    response = {"results": rows[:2], "page_metadata": {"hasNext": False}}
    error = HTTPError("search window exceeded", status_code=503)
    with patch.object(mock_usa_client, "_make_request", side_effect=[response, error]):
        iterator = iter(query.page_size(2))
        assert next(iterator).raw == rows[0]
        assert next(iterator).raw == rows[1]
        with pytest.raises(HTTPError, match="search window exceeded"):
            next(iterator)
