"""Response-derived model contracts checked against recorded input fixtures.

The tables in ``tests/model_contracts.py`` say which raw key each property reads.
This module runs them against values loaded through pytest's shared
``load_fixture`` factory, so no expected output value is duplicated here.
"""

from __future__ import annotations

import pytest

from tests.model_contracts import (
    AGENCY_FIELDS,
    AWARD_ACCOUNT_FIELDS,
    AWARD_FIELDS,
    FUNDING_FIELDS,
    PERIOD_FIELDS,
    RECIPIENT_FIELDS,
    SUBAWARD_FIELDS,
    TRANSACTION_FIELDS,
    FieldContract,
    compare_fields,
)
from usaspending.models.agency import Agency
from usaspending.models.award_account import AwardAccount
from usaspending.models.award_factory import create_award
from usaspending.models.funding import Funding
from usaspending.models.recipient import Recipient
from usaspending.models.subaward import SubAward
from usaspending.models.transaction import Transaction

DETAIL_FIXTURES = ("contract", "idv", "grant", "loan")
SEARCH_FIXTURES = (
    "search_results_contracts",
    "search_results_grants",
    "search_results_idvs",
)


@pytest.fixture
def settled_award(mock_usa_client, load_fixture):
    """Build an award from a shared fixture and forbid later requests."""

    def _build(fixture_name: str):
        data = load_fixture(f"awards/{fixture_name}.json")
        mock_usa_client.set_response(f"/awards/{data['generated_unique_award_id']}/", data)
        award = create_award(data, mock_usa_client)
        award.fetch_all_details()
        mock_usa_client.forbid_requests()
        return award

    return _build


class TestRecordedAwardResponses:
    """Both detail and search-shaped awards map their own fixture values."""

    @pytest.mark.parametrize("fixture_name", DETAIL_FIXTURES)
    def test_money_and_counts_map_the_payload(self, settled_award, fixture_name):
        pinned = compare_fields(fixture_name, settled_award(fixture_name), AWARD_FIELDS)

        assert {"award_amount", "total_obligation", "subaward_count"} <= pinned

    @pytest.mark.parametrize("fixture_name", DETAIL_FIXTURES)
    def test_dates_map_the_payload(self, settled_award, fixture_name):
        award = settled_award(fixture_name)
        period = award.period_of_performance

        pinned = compare_fields(f"{fixture_name} period", period, PERIOD_FIELDS)

        assert "start_date" in pinned
        assert award.start_date == period.start_date
        assert award.end_date == period.end_date

    @pytest.mark.parametrize("fixture_name", SEARCH_FIXTURES)
    def test_search_rows_map_their_own_columns(self, fixture_name, mock_usa_client, load_fixture):
        rows = load_fixture(f"awards/{fixture_name}.json")["results"]
        mock_usa_client.forbid_requests()
        pinned: set[str] = set()

        for index, row in enumerate(rows):
            award = create_award(dict(row), mock_usa_client)
            label = f"{fixture_name}[{index}]"
            pinned |= compare_fields(label, award, AWARD_FIELDS, keys_present_only=True)
            pinned |= compare_fields(
                f"{label} period",
                award.period_of_performance,
                PERIOD_FIELDS,
                keys_present_only=True,
            )

        assert {"award_amount", "total_obligation", "total_outlay", "start_date"} <= pinned


class TestRecordedRelatedResponses:
    """Recipient and agency properties derive from their loaded fixtures."""

    def test_recipient_aggregates_map_the_payload(self, mock_usa_client, load_fixture):
        recipient = Recipient(load_fixture("recipient_university.json"), mock_usa_client)
        mock_usa_client.forbid_requests()

        pinned = compare_fields("recipient_university", recipient, RECIPIENT_FIELDS)

        assert "total_transactions" in pinned

    def test_agency_counts_map_the_payload(self, mock_usa_client, load_fixture):
        agency = Agency(load_fixture("agency.json"), mock_usa_client)
        mock_usa_client.forbid_requests()

        pinned = compare_fields("agency", agency, AGENCY_FIELDS)

        assert pinned == {field.prop for field in AGENCY_FIELDS}


class TestRecordedRelationResponses:
    """Relations that exposed the brittleness of the old live snapshots."""

    @pytest.mark.parametrize(
        "fixture_name",
        ["awards/transactions.json", "spending_by_transaction.json"],
    )
    def test_transactions_map_each_loaded_row(self, fixture_name, load_fixture):
        rows = load_fixture(fixture_name)["results"]

        for row in rows:
            transaction = Transaction(dict(row))
            compare_fields(fixture_name, transaction, TRANSACTION_FIELDS)
            assert transaction.amount == transaction.transaction_amount
            assert transaction.amt == transaction.transaction_amount
            assert transaction.mod == transaction.modification_number

    def test_award_accounts_map_loaded_rows(self, load_fixture, mock_usa_client):
        rows = load_fixture("awards/accounts.json")["results"]

        for row in rows:
            account = AwardAccount(dict(row), mock_usa_client)
            compare_fields("award account", account, AWARD_ACCOUNT_FIELDS)
            assert account.obligated_amount == account.total_transaction_obligated_amount

    def test_funding_maps_loaded_rows(self, load_fixture, mock_usa_client):
        rows = load_fixture("awards/award_funding_grant.json")["results"]

        for row in rows:
            funding = Funding(dict(row), mock_usa_client)
            compare_fields("funding", funding, FUNDING_FIELDS)

    def test_subawards_map_loaded_rows(self, load_fixture, mock_usa_client):
        rows = load_fixture("awards/search_results_subawards.json")["results"]

        for row in rows:
            compare_fields("subaward", SubAward(dict(row), mock_usa_client), SUBAWARD_FIELDS)

    def test_wrong_raw_key_fails_independent_verification(self, load_fixture):
        row = load_fixture("awards/transactions.json")["results"][0]
        assert row["id"] != row["type"]
        wrong_contract = (FieldContract("id", ("type",), str),)

        with pytest.raises(AssertionError, match="mapping defect"):
            compare_fields("wrong key", Transaction(dict(row)), wrong_contract)
