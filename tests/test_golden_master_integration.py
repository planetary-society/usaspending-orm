"""Golden-master integration tests: prove the refactor preserves live behavior.

The unit suite runs against recorded fixtures, so it cannot show that a
refactor still produces the same values from real API responses. This suite
fetches a fixed set of live records, reads the public properties of each
resulting model, and snapshots the results to ``tests/fixtures/golden/``.
Re-running after a refactor diffs against those snapshots.

What gets compared, and why
---------------------------
The suite asserts *the library's* behavior, not the upstream API's content, so
it records values at the altitude the library is responsible for:

* **Scalars are pinned exactly.** Parsed dates, coerced Decimals, title-cased
  strings and resolved codes are the library's actual work, so a change there
  is a real regression.
* **Containers are pinned by type and emptiness only.** Dict- and
  object-valued properties are pass-throughs of upstream JSON; their contents
  are the API's business. Every scalar the library derives *from* them is
  already pinned individually, so nothing is lost, and an upstream field
  addition cannot produce a false failure.
* **``raw`` is not captured at all.** It mirrors the whole upstream response
  body, so snapshotting it would turn this suite into an assertion about the
  API's payload shape.
* **Volatile properties are recorded as a type tag** taken from the live
  object. Figures that move as data is ingested are free to change, while a
  type regression (``date`` becoming ``str``, ``Decimal`` becoming ``None``) is
  still caught. Deriving the tag at capture time rather than from the encoded
  snapshot is what makes that check real. A type tag alone would still pass a
  wrong-but-well-typed value, so ``TestSameResponseVolatileFields`` compares
  each of those values exactly against the response it came from, using the
  tables in ``tests/volatile_fields.py`` that the unit suite runs against the
  recorded fixtures. See that module for how the comparison stays drift-immune.
* **Network-backed properties are recorded as such, not read.** Reading them
  during a snapshot would cost roughly ten extra requests per Agency to
  re-confirm they are still Decimals; one focused test covers them instead.

The concrete class of every object is recorded too, which is what guards Award
subtype resolution, and properties that raise are recorded as their exception
type so "this raises NotImplementedError" is pinned as intentional.

Run with::

    uv run pytest -m integration tests/test_golden_master_integration.py

A missing snapshot fails rather than self-healing, so an absent baseline can
never look like a pass. To record or update baselines, opt in explicitly::

    USASPENDING_REGEN_GOLDEN=1 uv run pytest -m integration \\
        tests/test_golden_master_integration.py

Only a phase that intentionally changes behavior should produce a diff.
"""

from __future__ import annotations

import copy
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tests.snapshot_support import load_snapshot
from tests.volatile_fields import (
    AGENCY_FIELDS,
    AWARD_FIELDS,
    PERIOD_FIELDS,
    RECIPIENT_FIELDS,
    compare_volatile,
)
from usaspending.models.award_factory import create_award
from usaspending.models.base_model import BaseModel
from usaspending.models.period_of_performance import PeriodOfPerformance
from usaspending.models.recipient import Recipient
from usaspending.queries.base_query import BaseQuery

pytestmark = pytest.mark.integration

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
REGEN_ENV_VAR = "USASPENDING_REGEN_GOLDEN"

# Anchor records. These are specific live awards, which is the same convention
# tests/test_integration.py already uses.
CONTRACT_ID = "CONT_AWD_NAS1510000_8000_-NONE-_-NONE-"
# Chosen because it has child awards, so the IDVChildAwardsSearch path is real.
IDV_ID = "CONT_IDV_NNK14MA75C_8000"
GRANT_ID = "ASST_NON_NNG11HP16A_080"
LOAN_ID = "ASST_NON_P268K151065_091"
# A contract whose generated ID carries a parent IDV, to exercise parent_award.
CONTRACT_WITH_PARENT_ID = "CONT_AWD_NNS16AA07T_8000_NNS14AA17B_8000"
RECIPIENT_ID = "74bac010-0a24-8f82-8021-0fa16ab4bc6d-R"
AGENCY_TOPTIER_CODE = "080"

# Shared query scope for the search-backed snapshots.
ANCHOR_AGENCY = "National Aeronautics and Space Administration"
ANCHOR_FISCAL_YEAR = 2020

# `raw` (and its `to_dict` twin) mirrors the upstream response body. Capturing
# it would assert the API's shape rather than the library's behavior.
EXCLUDED_PROPERTIES = frozenset({"raw"})

# Properties that issue their own API request when read. Agency has ten, so
# snapshotting them would cost ~10 requests per Agency purely to re-record that
# they are still Decimals. TestAgencyLazyAggregates covers them once instead.
NETWORK_BACKED_PROPERTIES = frozenset(
    {
        "contract_obligations",
        "direct_payment_obligations",
        "grant_obligations",
        "idv_obligations",
        "latest_action_date",
        "loan_obligations",
        "obligations",
        "other_obligations",
        "subagencies",
        "total_obligations",
        "transaction_count",
    }
)

# Figures that legitimately move as the API ingests data, including money and
# dates on awards that are still active. Recorded as a live type tag.
VOLATILE_PROPERTIES = frozenset(
    {
        "award_amount",
        "base_and_all_options",
        "base_exercised_options",
        "covid19_obligations",
        "covid19_outlays",
        "def_codes",
        "end_date",
        "fiscal_year",
        "infrastructure_obligations",
        "infrastructure_outlays",
        "last_modified_date",
        "messages",
        "subaward_count",
        "subtier_agency_count",
        "total_account_obligation",
        "total_account_outlay",
        "total_funding",
        "total_loan_value",
        "total_obligation",
        "total_outlay",
        "total_outlays",
        "total_subaward_amount",
        "total_subsidy_cost",
        # Recipient-side aggregates, the same class of server-computed total as
        # the award-side ones above. Missed when this list was first written, and
        # they drift for the same reason: USASpending revises transactions, so
        # these fall as well as rise.
        "total_face_value_loan_amount",
        "total_face_value_loan_transactions",
        "total_transaction_amount",
        "total_transactions",
    }
)


def _is_scalar(value: object) -> bool:
    """Return True for values the library itself computes and we pin exactly."""
    return value is None or isinstance(value, (bool, int, float, str, Decimal, date, datetime))


def _encode_scalar(value: object) -> object:
    """Render a scalar in a stable, JSON-serializable form."""
    if isinstance(value, Decimal):
        return f"Decimal({value})"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _is_empty(value: object) -> bool:
    """Return True when a value carries no content."""
    if value is None:
        return True
    if isinstance(value, (str, list, tuple, set, dict)):
        return len(value) == 0
    return False


def _type_tag(value: object) -> dict[str, object]:
    """Describe a value by its live runtime type and emptiness.

    Taken from the real object before encoding, so a type regression is visible.
    """
    return {"__type__": type(value).__name__, "empty": _is_empty(value)}


def _snapshot_value(value: object) -> object:
    """Convert a property value into its recorded form.

    Scalars and lists of scalars are pinned exactly; models, query builders and
    containers are pinned by type only.

    Args:
        value: The value to record.

    Returns:
        object: A JSON-serializable representation.
    """
    if _is_scalar(value):
        return _encode_scalar(value)
    if isinstance(value, (BaseModel, BaseQuery)):
        return {"__type__": type(value).__name__}
    if isinstance(value, (list, tuple, set)):
        items = sorted(value, key=str) if isinstance(value, set) else list(value)
        if all(_is_scalar(item) for item in items):
            return [_encode_scalar(item) for item in items]
        return _type_tag(value)
    return _type_tag(value)


def _snapshot_object(obj: object) -> dict[str, object]:
    """Read an object's public properties and record the results.

    Args:
        obj: The model instance to introspect.

    Returns:
        dict[str, object]: The object's class name and per-property records.
    """
    properties: dict[str, object] = {}

    for name in sorted(name for name in dir(obj) if not name.startswith("_")):
        if name in EXCLUDED_PROPERTIES:
            continue

        if name in NETWORK_BACKED_PROPERTIES and hasattr(type(obj), name):
            properties[name] = {"__network_backed__": True}
            continue

        try:
            value = getattr(obj, name)
        except Exception as exc:
            # Recording which properties raise is part of the snapshot's value.
            properties[name] = {"__error__": type(exc).__name__}
            continue

        if callable(value):
            continue

        properties[name] = (
            _type_tag(value) if name in VOLATILE_PROPERTIES else _snapshot_value(value)
        )

    return {"class": type(obj).__name__, "properties": properties}


def _compare(name: str, current: dict[str, object], expected: dict[str, object]) -> None:
    """Assert a captured snapshot matches the recorded one.

    Volatility is already baked into the recorded form, so this is a plain
    comparison with no special cases.

    Args:
        name: Snapshot name, used in failure messages.
        current: Freshly captured snapshot.
        expected: Recorded snapshot.
    """
    assert current["class"] == expected["class"], (
        f"{name}: class changed from {expected['class']} to {current['class']}. "
        "This usually means award subtype resolution changed."
    )

    current_props = current["properties"]
    expected_props = expected["properties"]

    missing = sorted(set(expected_props) - set(current_props))
    added = sorted(set(current_props) - set(expected_props))
    assert not missing, f"{name}: properties disappeared: {missing}"
    assert not added, f"{name}: unexpected new properties: {added}"

    mismatches = {
        prop: {"expected": expected_value, "actual": current_props[prop]}
        for prop, expected_value in expected_props.items()
        if current_props[prop] != expected_value
    }

    assert mismatches == {}, (
        f"{name}: {len(mismatches)} property value(s) changed. If intentional, "
        f"regenerate with {REGEN_ENV_VAR}=1 and review the diff. {mismatches}"
    )


def _verify(name: str, obj: object) -> None:
    """Capture an object's snapshot and compare it against the golden record."""
    current = _snapshot_object(obj)
    expected = load_snapshot(GOLDEN_DIR / f"{name}.json", current, REGEN_ENV_VAR)
    _compare(name, current, expected)


@pytest.fixture(scope="module")
def award_anchors(client) -> dict[str, object]:
    """Fetch each anchor award once for the whole module.

    Snapshotting reads every public property, which triggers lazy loads, and
    many tests below reach through the same records. Fetching once keeps this
    suite to one request per anchor instead of one per test, which also keeps it
    clear of the integration rate limit.
    """
    return {
        "award_contract": client.awards.find_by_generated_id(CONTRACT_ID),
        "award_idv": client.awards.find_by_generated_id(IDV_ID),
        "award_grant": client.awards.find_by_generated_id(GRANT_ID),
        "award_loan": client.awards.find_by_generated_id(LOAN_ID),
    }


@pytest.fixture(scope="module")
def contract(award_anchors):
    """The anchor contract, shared by every test that reaches through it."""
    return award_anchors["award_contract"]


@pytest.fixture(scope="module")
def idv(award_anchors):
    """The anchor Indefinite Delivery Vehicle."""
    return award_anchors["award_idv"]


@pytest.fixture(scope="module")
def contract_with_parent(client):
    """A contract whose generated ID carries a parent IDV."""
    return client.awards.find_by_generated_id(CONTRACT_WITH_PARENT_ID)


@pytest.fixture(scope="module")
def agency(client):
    """The anchor agency, fetched through the finder."""
    return client.agencies.find_by_toptier_code(AGENCY_TOPTIER_CODE)


@pytest.fixture(scope="module")
def recipient(client):
    """The anchor recipient, shared by the snapshot and the field comparison."""
    return client.recipients.find_by_recipient_id(RECIPIENT_ID)


@pytest.fixture(scope="module")
def search_first_result(client):
    """The first row of the anchor search, and a copy of its untouched payload.

    One request serves both the snapshot, which reads the model and so pulls a
    detail response into it, and the same-response tests, which build their own
    awards from the copy taken before any property was read. Running the query
    twice would cost a second request to answer the same question.
    """
    query = (
        client.awards.search()
        .contracts()
        .fiscal_year(ANCHOR_FISCAL_YEAR)
        .agency(ANCHOR_AGENCY)
        .order_by("Award Amount", "desc")
    )
    award = query.first()
    return award, copy.deepcopy(award.raw)


class TestAwardGoldenMasters:
    """Every Award subtype, captured end to end from the live API."""

    @pytest.mark.parametrize(
        "name",
        ["award_contract", "award_idv", "award_grant", "award_loan"],
    )
    def test_award_snapshot(self, award_anchors, name):
        _verify(name, award_anchors[name])

    def test_parent_award_snapshot(self, contract_with_parent):
        """parent_award is an untested path that the refactor must preserve."""
        parent = contract_with_parent.parent_award

        assert parent is not None, "Expected this contract to expose a parent award"
        _verify("award_parent_of_contract", parent)


class TestRelatedModelGoldenMasters:
    """Models reached through an award, plus the standalone resources."""

    def test_recipient_snapshot(self, recipient):
        _verify("recipient", recipient)

    def test_agency_snapshot(self, agency):
        _verify("agency", agency)

    @pytest.mark.parametrize(
        "name,attribute",
        [
            ("award_contract_recipient", "recipient"),
            ("award_contract_awarding_agency", "awarding_agency"),
            ("award_contract_place_of_performance", "place_of_performance"),
            ("award_contract_period_of_performance", "period_of_performance"),
        ],
    )
    def test_related_model_snapshot(self, contract, name, attribute):
        """Exercises the flat-versus-nested reconciliation in Award."""
        _verify(name, getattr(contract, attribute))


class TestAgencyLazyAggregates:
    """Cover the per-category obligation properties skipped during snapshots.

    Phase 3 replaces these six near-identical bodies with one shared helper, so
    they need coverage. Each issues its own request, which is why they are
    checked once here rather than on every Agency snapshot. Values move with
    each ingest, so only the type is asserted.
    """

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
    def test_obligation_is_decimal_or_none(self, agency, name):
        value = getattr(agency, name)

        assert value is None or isinstance(value, Decimal)

    def test_subagencies_are_models(self, agency):
        subagencies = agency.subagencies

        assert isinstance(subagencies, list)
        assert all(type(item).__name__ == "SubTierAgency" for item in subagencies)


class TestQueryResultGoldenMasters:
    """First result of each query path the refactor touches.

    Every search pins an explicit sort where the endpoint supports one, so
    ``first()`` is a defined record rather than whatever the server returns
    first. The spending-by-category endpoints rank by amount descending and
    take no sort parameter, so a fixed fiscal year and agency is enough.
    """

    def test_award_search_first_result(self, search_first_result):
        """Exercises AwardsSearch._transform_result and _get_fields."""
        award, _row = search_first_result
        _verify("search_contract_first_result", award)

    def test_subaward_search_first_result(self, client):
        query = (
            client.subawards.search()
            .contracts()
            .fiscal_year(ANCHOR_FISCAL_YEAR)
            .agency(ANCHOR_AGENCY)
            .order_by("Sub-Award Amount", "desc")
        )
        _verify("search_subaward_first_result", query.first())

    @pytest.mark.parametrize(
        "name,relation",
        [
            ("transaction_first_result", "transactions"),
            ("award_account_first_result", "accounts"),
            ("funding_first_result", "funding"),
        ],
    )
    def test_award_relation_first_result(self, contract, name, relation):
        _verify(name, getattr(contract, relation).first())

    def test_idv_child_award_first_result(self, idv):
        """Exercises IDVChildAwardsSearch._transform_result."""
        _verify("idv_child_award_first_result", idv.child_awards.first())

    @pytest.mark.parametrize(
        "name,category",
        [
            ("spending_by_recipient_first_result", "by_recipient"),
            ("spending_by_state_first_result", "by_state"),
        ],
    )
    def test_spending_first_result(self, client, name, category):
        """Snapshot the first row each spending category transforms.

        Takes the head of a two-row page rather than calling ``first()``, which
        requests ``limit=1``. The recipient category was once observed answering
        ``limit=1`` with zero results while ``limit=2`` returned two, and it has
        since stopped doing so, so treat that as upstream flakiness rather than a
        contract. This test exists to snapshot the transformed row, and asking for
        two rows keeps it off a single-row edge case the API has mishandled at
        least once.
        """
        query = getattr(client.spending.search(), category)()
        query = query.fiscal_year(ANCHOR_FISCAL_YEAR).agency(ANCHOR_AGENCY)
        rows = query.limit(2).all()
        _verify(name, rows[0] if rows else None)


class TestSameResponseVolatileFields:
    """Volatile figures, compared exactly against the response that produced them.

    The snapshots above record a volatile property as a type tag, because its
    value moves between runs. That leaves a real gap: a money property reading
    the wrong key, or shifted by a cent, is still a Decimal and still passes, and
    so is an ``end_date`` parsed from the wrong column.

    ``tests/volatile_fields.py`` holds the tables and the comparison, which run
    against the recorded fixtures in the unit suite as well. What these tests add
    is today's payload: a response shape the fixtures predate, such as a column
    the API has started or stopped sending, is caught here and only here.

    Nothing in this class can fail on live data drift. Both sides of every
    comparison come from one payload -- the model's own ``raw``, which is
    literally the dict its properties read -- including a raw value that will not
    coerce, which is reported as a mismatch rather than raised.
    """

    @pytest.fixture(scope="module")
    def settled_anchors(self, award_anchors):
        """The anchor awards, with their detail fetch already latched.

        A money property whose key the payload lacks would otherwise trigger the
        fetch mid-comparison, and the expectation would then have been read from
        a payload one response older than the answer. Latching first makes
        ``raw`` final, so every comparison here is against one response.

        Free in a full run: an award detail response carries no COVID-19 or
        Infrastructure keys, so snapshotting has already gone looking for them
        and latched the flag. That saving is ordering-dependent, and this class
        does not rely on it -- running these tests alone simply pays for the
        fetch here instead.
        """
        for award in award_anchors.values():
            award.fetch_all_details()
        return award_anchors

    @pytest.mark.parametrize(
        "name",
        ["award_contract", "award_idv", "award_grant", "award_loan"],
    )
    def test_award_money_and_counts_match_their_payload(self, settled_anchors, name):
        pinned = compare_volatile(name, settled_anchors[name], AWARD_FIELDS)

        # Only properties that compared a real figure are reported, so this
        # cannot be satisfied by a run of None-equals-None.
        assert {"award_amount", "total_obligation", "subaward_count"} <= pinned

    @pytest.mark.parametrize(
        "name",
        ["award_contract", "award_idv", "award_grant", "award_loan"],
    )
    def test_award_dates_match_their_payload(self, settled_anchors, name):
        award = settled_anchors[name]
        period = award.period_of_performance

        pinned = compare_volatile(f"{name} period", period, PERIOD_FIELDS)

        assert "start_date" in pinned
        # The award reads no date keys of its own; it delegates to the period.
        assert award.start_date == period.start_date
        assert award.end_date == period.end_date

    def test_recipient_aggregates_match_their_payload(self, recipient):
        """The finder's own response carries all four aggregates.

        So no latching is needed, and the key set is asserted unchanged rather
        than fetched again: ``fetch_all_details()`` here would be a second GET
        for a payload already in hand.
        """
        before = set(recipient.raw)

        pinned = compare_volatile("recipient", recipient, RECIPIENT_FIELDS)

        assert "total_transactions" in pinned
        assert set(recipient.raw) == before, "The recipient lazy-loaded mid-comparison"

    def test_agency_counts_match_their_payload(self, agency):
        """The agency detail response likewise carries what is compared here."""
        before = set(agency.raw)

        pinned = compare_volatile("agency", agency, AGENCY_FIELDS)

        assert pinned == {"fiscal_year", "subtier_agency_count"}
        assert set(agency.raw) == before, "The agency lazy-loaded mid-comparison"

    def test_agency_messages_pass_through_unchanged(self, agency):
        """``messages`` is a list the API sends and the model forwards."""
        assert agency.messages == agency.raw.get("messages", [])

    def test_agency_def_codes_carry_the_reported_codes(self, agency):
        """Compares the codes only.

        Each entry is rebuilt as a ``DefCode``, whose remaining fields are pinned
        by ``tests/models/test_agency.py`` against a recorded response. What is
        checked here is that the live list is neither reordered nor dropped.
        """
        reported = [entry["code"] for entry in agency.raw.get("def_codes", [])]

        assert [code.code for code in agency.def_codes] == reported


class TestSearchResultSameResponseFields:
    """The same comparison for a search result, which reads a different key set.

    A search row reports money as ``Award Amount`` and dates as ``Start Date``,
    and hands its recipient and period keys to the two ``_from_search_result``
    projections. The snapshots cannot cover any of that: reading every public
    property in sorted order reaches ``award_type_code``, whose key no row
    carries, long before ``recipient``, so a detail response is merged in and the
    nested spellings win. Everything here is read from the row and nothing else.
    """

    @staticmethod
    def _award(search_first_result, client):
        """Build an award from a private copy of the captured row.

        The row is copied per test because an award replaces its payload in place
        when a detail fetch fires, which is the effect this class exists to rule
        out.
        """
        return create_award(copy.deepcopy(search_first_result[1]), client)

    def test_the_row_answers_from_itself(self, search_first_result, client):
        """Money, dates and recipient all resolve from the row's own columns.

        The money comparison is restricted to columns the row carries: reading
        one it does not, such as ``total_account_obligation``, would send the
        award for a detail response. That none of the reads did so is what the
        two key-set assertions say, since a fetch merges its response in place.
        """
        row = search_first_result[1]
        award = self._award(search_first_result, client)
        recipient = award.recipient
        before = set(award.raw)

        compare_volatile("search row", award, AWARD_FIELDS, keys_present_only=True)
        compare_volatile("search row period", award.period_of_performance, PERIOD_FIELDS)
        # `name` is left out on purpose: it is title-cased on the way out, so
        # comparing it against the row would either restate the casing rules or
        # run the raw value through the same function under test. The snapshot
        # pins the cased value exactly, which is the right place for it.
        assert recipient.uei == row.get("Recipient UEI")
        assert recipient.location.state_code == row["Recipient Location"]["state_code"]
        # USASpending retired DUNS, so every recorded row sends it as null. The
        # key is present, which is why reading it costs no request.
        assert recipient.duns is None

        assert set(award.raw) == before, (
            "Reading the flat search keys pulled a detail response in. Every "
            "value read above was already on the row."
        )
        assert set(recipient.raw) <= set(Recipient._SEARCH_KEYS), (
            "The recipient fetched its own detail response rather than reading "
            "the flat keys the row carries."
        )

    def test_the_row_comparison_covers_the_flat_spellings(self, search_first_result, client):
        """Guards against a vacuous pass, and pins which projections ran.

        Each name is a column only a search row sends, so a comparison that
        quietly fell back to detail spellings would not report them.
        """
        award = self._award(search_first_result, client)

        money = compare_volatile("search row", award, AWARD_FIELDS, keys_present_only=True)
        dates = compare_volatile("search row period", award.period_of_performance, PERIOD_FIELDS)

        assert {"award_amount", "total_obligation", "total_outlay"} <= money
        assert {"start_date", "end_date"} <= dates
        assert set(award.period_of_performance.raw) <= set(PeriodOfPerformance._SEARCH_KEYS)
        assert set(award.recipient.raw) <= set(Recipient._SEARCH_KEYS)


class TestCountMechanisms:
    """Counts come from several different mechanisms; check each still works.

    Exact counts drift as data is ingested, so these assert a usable count
    rather than a pinned figure. What matters for the refactor is that each
    mechanism still returns a positive integer through its own code path.
    """

    def test_award_search_count(self, client):
        query = (
            client.awards.search().contracts().fiscal_year(ANCHOR_FISCAL_YEAR).agency(ANCHOR_AGENCY)
        )

        assert query.count() > 0

    @pytest.mark.parametrize("relation", ["transactions", "accounts", "funding"])
    def test_award_relation_count(self, contract, relation):
        assert getattr(contract, relation).count() > 0

    def test_spending_count_respects_limit(self, client):
        query = (
            client.spending.search()
            .by_recipient()
            .fiscal_year(ANCHOR_FISCAL_YEAR)
            .agency(ANCHOR_AGENCY)
            .limit(7)
        )

        assert query.count() == 7

    def test_idv_child_awards_count(self, idv):
        assert idv.child_awards.count() > 0
