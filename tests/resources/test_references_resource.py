"""Tests for the USAspending reference-data resource."""

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending.exceptions import APIError
from usaspending.models import DefCode
from usaspending.models.agency import DefCode as LegacyDefCode
from usaspending.resources import ReferencesResource


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


def test_def_codes_requests_and_converts_reference_data(mock_usa_client):
    """The reference endpoint returns ordered model objects."""
    endpoint = MockUSASpendingClient.Endpoints.DEF_CODES
    mock_usa_client.set_fixture_response(endpoint, "def_codes")

    codes = mock_usa_client.references.def_codes()

    assert [code.code for code in codes] == ["A", "L", "Q"]
    assert all(isinstance(code, DefCode) for code in codes)
    assert codes[0].urls == ["https://www.congress.gov/example-a"]
    assert codes[1].disaster == "covid_19"
    assert codes[2].urls is None
    mock_usa_client.assert_called_with(endpoint, "GET")


@pytest.mark.parametrize("response", [{}, {"codes": None}, {"codes": "invalid"}])
def test_def_codes_returns_empty_for_a_missing_or_non_list_collection(mock_usa_client, response):
    """Malformed collection envelopes follow existing empty-list behavior."""
    endpoint = MockUSASpendingClient.Endpoints.DEF_CODES
    mock_usa_client.set_response(endpoint, response)

    assert mock_usa_client.references.def_codes() == []


def test_def_codes_skips_non_dictionary_rows(mock_usa_client):
    """A malformed row does not prevent valid reference rows from loading."""
    endpoint = MockUSASpendingClient.Endpoints.DEF_CODES
    mock_usa_client.set_response(
        endpoint,
        {
            "codes": [
                None,
                "invalid",
                {"code": "A", "public_law": "P.L. 1-1", "urls": []},
            ]
        },
    )

    codes = mock_usa_client.references.def_codes()

    assert [code.code for code in codes] == ["A"]
    assert codes[0].urls == []


def test_def_codes_uses_client_caching_policy_not_resource_memoization(mock_usa_client):
    """Each method call delegates to the client's configured request layer."""
    endpoint = MockUSASpendingClient.Endpoints.DEF_CODES
    mock_usa_client.set_fixture_response(endpoint, "def_codes")

    first = mock_usa_client.references.def_codes()
    second = mock_usa_client.references.def_codes()

    assert first is not second
    assert mock_usa_client.get_request_count(endpoint) == 2


def test_def_codes_propagates_api_errors(mock_usa_client):
    """Reference lookup failures retain the client's normal exception type."""
    endpoint = MockUSASpendingClient.Endpoints.DEF_CODES
    mock_usa_client.set_error_response(endpoint, 400, detail="Reference lookup failed")

    with pytest.raises(APIError, match="Reference lookup failed"):
        mock_usa_client.references.def_codes()
