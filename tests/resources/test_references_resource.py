"""Tests for the USAspending reference-data resource."""

from dataclasses import asdict

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending.exceptions import APIError
from usaspending.models import Country, DefCode, State
from usaspending.models.agency import DefCode as LegacyDefCode
from usaspending.queries import CountriesQuery, DefCodesQuery, StatesQuery
from usaspending.resources import ReferencesResource


@pytest.fixture(
    params=[
        ("def_codes", DefCodesQuery, DefCode),
        ("countries", CountriesQuery, Country),
        ("states", StatesQuery, State),
    ],
    ids=["def_codes", "countries", "states"],
)
def reference_query(request, mock_usa_client, load_fixture):
    """Provide the same collection contract for each reference endpoint."""
    method_name, query_type, model_type = request.param
    response = load_fixture(f"{method_name}.json")
    endpoint = getattr(MockUSASpendingClient.Endpoints, method_name.upper())
    assert query_type.ENDPOINT == endpoint
    mock_usa_client.set_response(endpoint, response)
    return (
        getattr(mock_usa_client.references, method_name),
        query_type,
        model_type,
        response[query_type.RESULTS_KEY],
    )


def test_references_resource_is_lazy_and_cached(mock_usa_client):
    """The client creates one references resource on first access."""
    assert "references" not in mock_usa_client._resources

    first = mock_usa_client.references
    second = mock_usa_client.references

    assert first is second
    assert first.client is mock_usa_client
    assert mock_usa_client._resources == {"references": first}


def test_references_resource_public_exports_preserve_legacy_model_import(mock_usa_client):
    """The new resource and model export do not break the old deep import."""
    assert isinstance(mock_usa_client.references, ReferencesResource)
    assert DefCode is LegacyDefCode


def test_reference_query_requests_and_preserves_reference_data(mock_usa_client, reference_query):
    """Models preserve server fields, including special codes and leading zeros."""
    lookup, query_type, model_type, rows = reference_query

    records = lookup().all()

    assert all(isinstance(record, model_type) for record in records)
    assert [asdict(record) for record in records] == rows
    mock_usa_client.assert_called_with(query_type.ENDPOINT, "GET")


def test_def_codes_converts_optional_reference_fields(mock_usa_client):
    """DEFC records retain their list and optional-field behavior."""
    mock_usa_client.set_fixture_response(MockUSASpendingClient.Endpoints.DEF_CODES, "def_codes")

    codes = mock_usa_client.references.def_codes().all()

    assert codes[0].urls == ["https://www.congress.gov/example-a"]
    assert codes[1].disaster == "covid_19"
    assert codes[2].urls is None


@pytest.mark.parametrize("collection", [None, "invalid"])
def test_reference_query_returns_empty_for_a_non_list_collection(
    mock_usa_client, reference_query, collection
):
    """Malformed collection envelopes follow existing empty-list behavior."""
    lookup, query_type, _, _ = reference_query
    mock_usa_client.set_response(query_type.ENDPOINT, {query_type.RESULTS_KEY: collection})

    assert lookup().all() == []


def test_reference_query_returns_empty_for_a_missing_collection(mock_usa_client, reference_query):
    lookup, query_type, _, _ = reference_query
    mock_usa_client.set_response(query_type.ENDPOINT, {})

    assert lookup().all() == []


def test_reference_query_skips_non_dictionary_rows(mock_usa_client, reference_query):
    """A malformed row does not prevent valid reference rows from loading."""
    lookup, query_type, _, rows = reference_query
    mock_usa_client.set_response(
        query_type.ENDPOINT, {query_type.RESULTS_KEY: [None, "invalid", rows[0]]}
    )

    assert [asdict(record) for record in lookup()] == [rows[0]]


def test_reference_query_is_lazy_until_evaluated(mock_usa_client, reference_query):
    """Building the query, or filtering it, makes no request."""
    lookup, query_type, _, rows = reference_query
    mock_usa_client.forbid_requests()

    assert isinstance(lookup().code(rows[0]["code"]).description("text"), query_type)


def test_reference_query_filters_one_fetched_list(mock_usa_client, reference_query):
    """Filters and repeated reads reuse a query's single request."""
    lookup, query_type, _, rows = reference_query
    target = rows[1]
    query = lookup()

    assert len(query) == len(rows)
    assert [record.code for record in query.code(target["code"])] == [target["code"]]
    assert [record.code for record in query.codes(rows[0]["code"], target["code"])] == [
        rows[0]["code"],
        target["code"],
    ]
    description = target[query.KEYWORD_FIELDS[0]].lower()
    assert [record.code for record in query.description(description)] == [target["code"]]
    assert len(query.all()) == len(rows)
    assert mock_usa_client.get_request_count(query_type.ENDPOINT) == 1


def test_reference_query_instances_fetch_independently(mock_usa_client, reference_query):
    """Each method call returns a fresh query and uses the client's caching policy."""
    lookup, query_type, _, _ = reference_query
    first = lookup()
    second = lookup()

    assert first is not second
    assert first.all() is not second.all()
    assert mock_usa_client.get_request_count(query_type.ENDPOINT) == 2


def test_reference_query_propagates_api_errors(mock_usa_client, reference_query):
    """Reference lookup failures retain the client's normal exception type."""
    lookup, query_type, _, _ = reference_query
    mock_usa_client.set_error_response(query_type.ENDPOINT, 400, detail="Reference lookup failed")

    with pytest.raises(APIError, match="Reference lookup failed"):
        lookup().all()
