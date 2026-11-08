"""Relationships must preserve identifiers, laziness and their client's lifetime."""

from unittest.mock import Mock

import pytest

from tests.mocks import MockUSASpendingClient
from usaspending.exceptions import APIError
from usaspending.models.agency import Agency
from usaspending.models.award_account import AwardAccount
from usaspending.models.federal_account import FederalAccount
from usaspending.models.funding import Funding
from usaspending.models.subaward import SubAward


def crosswalk(*rows):
    return {"agencies": {"cfo_agencies": list(rows), "other_agencies": []}}


def parent_tree(code, parent="097"):
    return {"results": [{"id": parent, "children": [{"id": code}]}]}


@pytest.mark.parametrize("model_class", [Funding, AwardAccount])
def test_funding_agency_and_account_resolve_independently(mock_usa_client, model_class):
    data = {
        "federal_account": "021-1234",
        "funding_toptier_agency_id": 72,
        "funding_agency_id": 862,
        "funding_agency_name": "NASA",
        "awarding_toptier_agency_id": 99,
        "awarding_agency_name": "Other agency",
    }
    record = model_class(data, mock_usa_client)
    agency = record.funding_agency
    account = record.federal_account if model_class is Funding else record
    assert agency.name == "NASA"
    assert agency.agency_id == 862
    assert account.id == "021-1234"
    assert mock_usa_client.get_request_count() == 0

    mock_usa_client.set_response(
        "/bulk_download/list_agencies/",
        crosswalk(
            {"toptier_agency_id": 72, "toptier_code": "080"},
            {"toptier_agency_id": 99, "toptier_code": "012"},
        ),
    )
    mock_usa_client.set_response("/references/filter_tree/tas/", parent_tree("021-1234"))
    mock_usa_client.set_response("/agency/080/", {"mission": "Explore"})

    assert agency.code == "080"
    assert agency.mission == "Explore"
    if model_class is Funding:
        assert record.awarding_agency.code == "012"
    assert account.toptier_code == "097"
    assert mock_usa_client.get_request_count("/bulk_download/list_agencies/") == 2
    assert mock_usa_client.get_request_count("/references/filter_tree/tas/") == 1
    assert mock_usa_client.get_last_request()["params"] == {"filter": "021-1234", "depth": 1}
    tas_endpoint = "/references/filter_tree/tas/097/021-1234/"
    mock_usa_client.set_response(tas_endpoint, {"results": []})
    assert account.tas_codes.all() == []
    assert mock_usa_client.get_request_count(tas_endpoint) == 1


def test_crosswalk_combines_both_lists_and_invalidates_on_base_url(
    mock_usa_client, monkeypatch, client_config
):
    fetch = Mock(
        side_effect=[
            crosswalk({"toptier_agency_id": 72, "toptier_code": "080"}),
            crosswalk({"toptier_agency_id": 99, "toptier_code": "012"}),
            crosswalk({"toptier_agency_id": 72, "toptier_code": "070"}),
            crosswalk(),
        ]
    )
    monkeypatch.setattr(mock_usa_client, "_make_request", fetch)
    resource = mock_usa_client.agencies
    assert resource._toptier_code_for_id(72) == "080"
    assert resource._toptier_code_for_id("99") == "012"
    assert resource._toptier_code_for_id(404) is None
    assert fetch.call_count == 2
    assert [call.kwargs["json"]["type"] for call in fetch.call_args_list] == [
        "award_agencies",
        "account_agencies",
    ]

    client_config(base_url="https://example.test/api/v2/")
    assert resource._toptier_code_for_id(72) == "070"
    assert fetch.call_count == 4


def test_crosswalk_failure_does_not_cache_partial_results(mock_usa_client, monkeypatch):
    response = crosswalk({"toptier_agency_id": 72, "toptier_code": "080"})
    fetch = Mock(side_effect=[response, APIError("offline", 503), response, crosswalk()])
    monkeypatch.setattr(mock_usa_client, "_make_request", fetch)
    agency = Agency({"toptier_agency_id": 72}, mock_usa_client)
    with pytest.raises(APIError):
        _ = agency.code
    assert agency.code == "080"
    assert fetch.call_count == 4


def test_crosswalk_skips_malformed_rows(mock_usa_client, monkeypatch):
    response = crosswalk(
        {"toptier_agency_id": 1, "toptier_code": None},
        {"toptier_agency_id": 72, "toptier_code": "080"},
    )
    monkeypatch.setattr(mock_usa_client, "_make_request", Mock(side_effect=[response, crosswalk()]))
    resource = mock_usa_client.agencies
    assert resource._toptier_code_for_id(72) == "080"
    assert resource._toptier_code_for_id(1) is None


def test_unresolved_agency_never_requests_a_guessed_detail_url(mock_usa_client):
    mock_usa_client.set_response("/bulk_download/list_agencies/", crosswalk())
    agency = Agency({"toptier_agency_id": 72, "name": "NASA"}, mock_usa_client)
    assert agency.code is None
    assert agency.mission is None
    assert mock_usa_client.get_request_count() == 2


def test_crosswalk_miss_is_remembered_after_client_closes(mock_usa_client):
    mock_usa_client.set_response("/bulk_download/list_agencies/", crosswalk())
    agency = Agency({"toptier_agency_id": 72}, mock_usa_client)
    assert agency.code is None
    mock_usa_client.close()
    assert agency.code is None


def test_tree_queries_defer_code_resolution_until_iteration(mock_usa_client):
    mock_usa_client.set_response("/bulk_download/list_agencies/", crosswalk())
    mock_usa_client.set_response("/references/filter_tree/tas/", parent_tree("021-1234"))
    agency = Agency({"toptier_agency_id": 72}, mock_usa_client)
    account = FederalAccount({"id": "021-1234"}, mock_usa_client)
    accounts, tas_codes = agency.federal_accounts, account.tas_codes
    assert mock_usa_client.get_request_count() == 0

    assert accounts.all() == []
    assert mock_usa_client.get_request_count("/bulk_download/list_agencies/") == 2
    mock_usa_client.set_response("/references/filter_tree/tas/097/021-1234/", {"results": []})
    assert tas_codes.all() == []
    assert mock_usa_client.get_request_count("/references/filter_tree/tas/") == 1
    assert mock_usa_client.get_request_count("/references/filter_tree/tas/097/021-1234/") == 1


def test_parent_lookup_requires_an_exact_account_match(mock_usa_client):
    mock_usa_client.set_response("/references/filter_tree/tas/", parent_tree("021-12340"))
    account = FederalAccount({"id": "021-1234"}, mock_usa_client)
    assert account.toptier_code is None
    assert account.tas_codes.all() == []
    assert mock_usa_client.get_request_count("/references/filter_tree/tas/") == 1
    assert mock_usa_client.get_request_count("/references/filter_tree/tas/021/021-1234/") == 0


def test_parent_lookup_is_shared_across_accounts(mock_usa_client):
    mock_usa_client.set_response("/references/filter_tree/tas/", parent_tree("021-1234"))
    first = FederalAccount({"id": "021-1234"}, mock_usa_client)
    second = FederalAccount({"id": "021-1234"}, mock_usa_client)
    assert first.toptier_code == second.toptier_code == "097"
    assert mock_usa_client.get_request_count("/references/filter_tree/tas/") == 1


def test_parent_lookup_retries_after_failure(mock_usa_client, monkeypatch):
    fetch = Mock(side_effect=[APIError("offline", 503), parent_tree("021-1234")])
    monkeypatch.setattr(mock_usa_client, "_make_request", fetch)
    account = FederalAccount({"id": "021-1234"}, mock_usa_client)
    with pytest.raises(APIError):
        _ = account.toptier_code
    assert account.toptier_code == "097"
    assert account.toptier_code == "097"
    assert fetch.call_count == 2


def test_explicit_account_parent_avoids_lookup(mock_usa_client):
    account = FederalAccount({"id": "021-1234", "ancestors": ["097"]}, mock_usa_client)
    mock_usa_client.forbid_requests()
    assert account.toptier_code == "097"
    assert account.tas_codes._toptier_code == "097"


def test_funding_relationships_reuse_their_data(mock_usa_client):
    mock_usa_client.set_response("/references/filter_tree/tas/", parent_tree("021-1234"))
    mock_usa_client.set_response(
        "/references/filter_tree/tas/097/021-1234/", {"results": [{"id": "021-X-1234-000"}]}
    )
    funding = Funding(
        {
            "federal_account": "021-1234",
            "funding_toptier_agency_id": 72,
            "awarding_toptier_agency_id": 99,
        },
        mock_usa_client,
    )
    assert funding.funding_agency is funding.funding_agency
    assert funding.awarding_agency is funding.awarding_agency
    assert funding.federal_account is funding.federal_account
    assert funding.federal_account.count == funding.federal_account.count == 1
    assert mock_usa_client.get_request_count() == 2


@pytest.mark.parametrize("recursive", [False, True])
@pytest.mark.parametrize("model_class", [Funding, AwardAccount])
def test_cached_relationships_follow_reattach(mock_usa_client, recursive, model_class):
    record = model_class(
        {
            "federal_account": "021-1234",
            "funding_toptier_agency_id": 72,
            "funding_agency_name": "NASA",
            "awarding_toptier_agency_id": 99,
        },
        mock_usa_client,
    )
    names = ["funding_agency"]
    if model_class is Funding:
        names += ["awarding_agency", "federal_account"]
    before = {name: getattr(record, name) for name in names}
    replacement = MockUSASpendingClient()
    mock_usa_client.close()
    record.reattach(replacement, recursive=recursive)
    for name in names:
        after = getattr(record, name)
        assert (after is before[name]) is recursive
        assert after._client is replacement
    assert replacement.get_request_count() == 0
    replacement.close()


def test_subrecipient_id_supports_lazy_details(mock_usa_client, load_fixture):
    row = load_fixture("awards/search_results_subawards.json")["results"][0]
    recipient_id = row["sub_award_recipient_id"]
    endpoint = f"/recipient/{recipient_id}/"
    mock_usa_client.set_response(endpoint, {"duns": "123456789", "total_transactions": 2})
    recipient = SubAward(row, mock_usa_client).recipient
    assert recipient.recipient_id == recipient_id
    assert mock_usa_client.get_request_count() == 0
    assert recipient.duns == "123456789"
    assert recipient.total_transactions == 2
    assert mock_usa_client.get_request_count(endpoint) == 1
