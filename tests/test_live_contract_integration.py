"""Live API contract tests without snapshots of unpredictable response values.

The offline suite verifies deterministic edge cases with recorded input
fixtures. This suite supplies current API responses to the same independent
field contracts. It checks that endpoints return usable models and that model
properties map the response they were built from; it never expects a particular
award, amount, date, count, ordering winner, or classification.
"""

from __future__ import annotations

import copy
from decimal import Decimal

import pytest

from tests.model_contracts import (
    AGENCY_FIELDS,
    AWARD_ACCOUNT_FIELDS,
    AWARD_FIELDS,
    FUNDING_FIELDS,
    PERIOD_FIELDS,
    RECIPIENT_FIELDS,
    SPENDING_FIELDS,
    SUBAWARD_FIELDS,
    TRANSACTION_FIELDS,
    compare_fields,
)
from usaspending.models.award_factory import create_award
from usaspending.models.base_model import BaseModel
from usaspending.models.period_of_performance import PeriodOfPerformance
from usaspending.models.recipient import Recipient

pytestmark = pytest.mark.integration

CHILD_BEARING_IDV = "CONT_IDV_NNK14MA75C_8000"
ANCHOR_FISCAL_YEAR = 2020


def assert_response_backed_model(obj: object) -> BaseModel:
    """Assert that an endpoint returned a model backed by a present response."""
    assert isinstance(obj, BaseModel)
    assert isinstance(obj.raw, dict)
    assert obj.raw
    return obj


@pytest.fixture(scope="module")
def anchor_values(load_fixture):
    """Load live-query anchors through the suite's shared fixture loader."""
    award_paths = {
        "contract": "awards/contract.json",
        "idv": "awards/idv.json",
        "grant": "awards/grant.json",
        "loan": "awards/loan.json",
    }
    awards = {
        name: load_fixture(path)["generated_unique_award_id"] for name, path in award_paths.items()
    }
    agency = load_fixture("agency.json")
    recipient = load_fixture("recipient_university.json")
    return {
        "awards": awards,
        "agency_name": agency["name"],
        "agency_code": agency["toptier_code"],
        "recipient_id": recipient["recipient_id"],
    }


@pytest.fixture(scope="module")
def award_anchors(client, anchor_values):
    """Fetch one recorded anchor ID per award subtype from the live API."""
    return {
        name: client.awards.find_by_generated_id(generated_id)
        for name, generated_id in anchor_values["awards"].items()
    }


@pytest.fixture(scope="module")
def contract(award_anchors):
    return award_anchors["contract"]


@pytest.fixture(scope="module")
def idv_with_children(client):
    return client.awards.find_by_generated_id(CHILD_BEARING_IDV)


@pytest.fixture(scope="module")
def agency(client, anchor_values):
    return client.agencies.find_by_toptier_code(anchor_values["agency_code"])


@pytest.fixture(scope="module")
def recipient(client, anchor_values):
    return client.recipients.find_by_recipient_id(anchor_values["recipient_id"])


@pytest.fixture(scope="module")
def search_first_result(client, anchor_values):
    query = (
        client.awards.search()
        .contracts()
        .fiscal_year(ANCHOR_FISCAL_YEAR)
        .agency(anchor_values["agency_name"])
        .order_by("Award Amount", "desc")
    )
    award = query.first()
    assert_response_backed_model(award)
    return award, copy.deepcopy(award.raw)


class TestLiveAwardContracts:
    """Award properties derive from whichever values the API currently sends."""

    @pytest.mark.parametrize("name", ["contract", "idv", "grant", "loan"])
    def test_award_and_period_map_their_response(self, award_anchors, name):
        award = assert_response_backed_model(award_anchors[name])
        award.fetch_all_details()

        compare_fields(name, award, AWARD_FIELDS)
        compare_fields(f"{name} period", award.period_of_performance, PERIOD_FIELDS)
        assert award.start_date == award.period_of_performance.start_date
        assert award.end_date == award.period_of_performance.end_date


class TestLiveRelatedModelContracts:
    """Standalone and award-related models remain usable without value pins."""

    def test_recipient_aggregates_map_the_response(self, recipient):
        assert_response_backed_model(recipient)
        before = set(recipient.raw)

        compare_fields("recipient", recipient, RECIPIENT_FIELDS)

        assert set(recipient.raw) == before

    def test_agency_counts_map_the_response(self, agency):
        assert_response_backed_model(agency)
        before = set(agency.raw)

        compare_fields("agency", agency, AGENCY_FIELDS)

        assert set(agency.raw) == before

    def test_agency_lists_pass_through_the_response(self, agency):
        assert agency.messages == agency.raw.get("messages", [])
        reported_codes = [entry["code"] for entry in agency.raw.get("def_codes", [])]
        assert [code.code for code in agency.def_codes] == reported_codes

    @pytest.mark.parametrize(
        "attribute",
        ["recipient", "awarding_agency", "place_of_performance", "period_of_performance"],
    )
    def test_award_relation_is_response_backed(self, contract, attribute):
        assert_response_backed_model(getattr(contract, attribute))


class TestLiveQueryResultContracts:
    """Current first rows are checked against themselves rather than snapshots."""

    def test_award_search_row_maps_its_columns(self, search_first_result, client):
        row = search_first_result[1]
        award = create_award(copy.deepcopy(row), client)
        before = set(award.raw)

        compare_fields("award search", award, AWARD_FIELDS, keys_present_only=True)
        compare_fields(
            "award search period",
            award.period_of_performance,
            PERIOD_FIELDS,
            keys_present_only=True,
        )

        assert set(award.raw) == before
        assert set(award.period_of_performance.raw) <= set(PeriodOfPerformance._SEARCH_KEYS)
        assert set(award.recipient.raw) <= set(Recipient._SEARCH_KEYS)

    def test_subaward_search_row_maps_its_columns(self, client, anchor_values):
        query = (
            client.subawards.search()
            .contracts()
            .fiscal_year(ANCHOR_FISCAL_YEAR)
            .agency(anchor_values["agency_name"])
            .order_by("Sub-Award Amount", "desc")
        )
        subaward = assert_response_backed_model(query.first())

        compare_fields("subaward", subaward, SUBAWARD_FIELDS)

    @pytest.mark.parametrize(
        "relation,contracts",
        [
            ("transactions", TRANSACTION_FIELDS),
            ("accounts", AWARD_ACCOUNT_FIELDS),
            ("funding", FUNDING_FIELDS),
        ],
    )
    def test_award_relation_row_maps_its_columns(self, contract, relation, contracts):
        row = assert_response_backed_model(getattr(contract, relation).first())

        compare_fields(relation, row, contracts)

        if relation == "transactions":
            assert row.amount == row.transaction_amount
            assert row.amt == row.transaction_amount
            assert row.mod == row.modification_number
        elif relation == "accounts":
            assert row.obligated_amount == row.total_transaction_obligated_amount

    def test_idv_child_award_maps_its_columns(self, idv_with_children):
        child = assert_response_backed_model(idv_with_children.child_awards.first())
        compare_fields("idv child", child, AWARD_FIELDS, keys_present_only=True)

    @pytest.mark.parametrize("category", ["by_recipient", "by_state"])
    def test_spending_row_maps_its_columns(self, client, anchor_values, category):
        query = getattr(client.spending.search(), category)()
        rows = (
            query.fiscal_year(ANCHOR_FISCAL_YEAR)
            .agency(anchor_values["agency_name"])
            .limit(2)
            .all()
        )
        assert rows

        compare_fields(category, assert_response_backed_model(rows[0]), SPENDING_FIELDS)


class TestLiveQueryInvariants:
    """Counts and ordering are checked relationally, never against live totals."""

    def test_award_search_count_is_present(self, client, anchor_values):
        query = (
            client.awards.search()
            .contracts()
            .fiscal_year(ANCHOR_FISCAL_YEAR)
            .agency(anchor_values["agency_name"])
        )

        assert query.count() > 0

    @pytest.mark.parametrize("relation", ["transactions", "accounts", "funding"])
    def test_award_relation_count_is_present(self, contract, relation):
        assert getattr(contract, relation).count() > 0

    def test_spending_count_respects_requested_limit(self, client, anchor_values):
        requested_limit = 7
        query = (
            client.spending.search()
            .by_recipient()
            .fiscal_year(ANCHOR_FISCAL_YEAR)
            .agency(anchor_values["agency_name"])
            .limit(requested_limit)
        )

        count = query.count()
        assert count > 0
        assert count <= requested_limit

    def test_idv_child_awards_count_is_present(self, idv_with_children):
        assert idv_with_children.child_awards.count() > 0


class TestAgencyLazyAggregates:
    """Network-backed aggregate properties return their documented type."""

    @pytest.mark.parametrize(
        "name",
        [
            "contract_obligations",
            "grant_obligations",
            "idv_obligations",
            "loan_obligations",
            "direct_payment_obligations",
            "other_obligations",
            "total_obligations",
        ],
    )
    def test_obligation_is_decimal_or_absent(self, agency, name):
        value = getattr(agency, name)
        assert value is None or isinstance(value, Decimal)

    def test_subagencies_are_models(self, agency):
        subagencies = agency.subagencies
        assert isinstance(subagencies, list)
        assert all(isinstance(item, BaseModel) for item in subagencies)
