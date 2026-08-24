"""Every volatile property maps its own recorded payload, checked offline.

The tables in ``tests/volatile_fields.py`` say which raw key each moving figure
is meant to read. This module runs them against the recorded fixtures, so a
mapping regression fails in the unit suite at commit time rather than waiting for
someone to run the live golden master before a release. The integration suite
runs the same tables against today's responses, which is what catches a payload
shape these fixtures predate.

Every model here is built with a client that forbids requests once setup is done,
so a value can only have come from the payload the model was handed.
"""

from __future__ import annotations

import pytest

from tests.conftest import load_json_fixture
from tests.test_golden_master_integration import VOLATILE_PROPERTIES
from tests.volatile_fields import (
    AGENCY_FIELDS,
    AWARD_FIELDS,
    COVERED_PROPERTIES,
    PERIOD_FIELDS,
    RECIPIENT_FIELDS,
    compare_volatile,
)
from usaspending.models.agency import Agency
from usaspending.models.award_factory import create_award
from usaspending.models.recipient import Recipient

#: Recorded ``/awards/{id}/`` responses, one per subtype.
DETAIL_FIXTURES = ("contract", "idv", "grant", "loan")

#: Recorded ``spending_by_award`` pages, whose rows use the flat spellings.
SEARCH_FIXTURES = (
    "search_results_contracts",
    "search_results_grants",
    "search_results_idvs",
)

#: Volatile properties the tables deliberately do not cover, and why.
KNOWN_UNCOVERED = frozenset(
    {
        # Lists the API sends and the model forwards, not coerced scalars, so
        # there is no key-to-value mapping to restate. Each has its own
        # assertion in the golden master.
        "def_codes",
        "messages",
        # `Spending.total_outlays`. Both recorded spending snapshots pin it as
        # NoneType, so the existing type tag is already exact and a row here
        # would assert nothing the snapshot does not.
        "total_outlays",
        # Internal database IDs forwarded as-is from the API, not coerced
        # financial aggregates. No key-to-value mapping to verify.
        "award_internal_id",
        "generated_unique_award_id",
        # Funding model properties. The volatile_fields tables only cover
        # Award-level properties; these are not presently exercised there.
        "gross_outlay_amount",
        "reporting_fiscal_month",
        # AwardAccount model properties. Same reason as above.
        "obligated_amount",
        "total_transaction_obligated_amount",
    }
)

#: Properties the tables cover that the snapshots do not count as volatile.
#: A start date is set once and does not move, so a snapshot pins it exactly. It
#: is compared here anyway because it shares its key chain, and its precedence
#: rules, with `end_date`, which does move: checking one without the other would
#: leave `Base Obligation Date` unpinned.
ALSO_COVERED = frozenset({"start_date"})


@pytest.fixture
def settled_award(mock_usa_client):
    """Build an award from a recorded detail response, with fetching finished.

    A detail response carries no COVID-19 or Infrastructure keys, so the first
    read of one of those properties goes looking for them. That fetch is let
    happen here, answered with the same recorded payload, and requests are
    forbidden afterwards: the comparison then runs against a payload that can no
    longer change under it, and any further lazy load fails loudly.
    """

    def _build(fixture_name: str):
        data = load_json_fixture(f"awards/{fixture_name}.json")
        mock_usa_client.set_response(f"/awards/{data['generated_unique_award_id']}/", data)
        award = create_award(data, mock_usa_client)
        award.fetch_all_details()
        mock_usa_client.forbid_requests()
        return award

    return _build


class TestRecordedDetailResponses:
    """The nested spellings a ``/awards/{id}/`` response sends."""

    @pytest.mark.parametrize("fixture_name", DETAIL_FIXTURES)
    def test_money_and_counts_map_the_payload(self, settled_award, fixture_name):
        pinned = compare_volatile(fixture_name, settled_award(fixture_name), AWARD_FIELDS)

        # Named explicitly so a renamed property drops out of the table loudly
        # rather than leaving the comparison passing on an empty set.
        assert {"award_amount", "total_obligation", "subaward_count"} <= pinned

    @pytest.mark.parametrize("fixture_name", DETAIL_FIXTURES)
    def test_dates_map_the_payload(self, settled_award, fixture_name):
        award = settled_award(fixture_name)
        period = award.period_of_performance

        pinned = compare_volatile(f"{fixture_name} period", period, PERIOD_FIELDS)

        assert "start_date" in pinned
        # The award reads no date keys of its own; it delegates to the period.
        assert award.start_date == period.start_date
        assert award.end_date == period.end_date


class TestRecordedSearchRows:
    """The flat, title-cased spellings a ``spending_by_award`` row sends.

    Every row of every recorded page is checked, since the pages differ in which
    columns they carry: an Indefinite Delivery Vehicle row sends a null
    ``End Date``, an assistance row sends assistance columns a contract row has
    no counterpart for.
    """

    @pytest.mark.parametrize("fixture_name", SEARCH_FIXTURES)
    def test_rows_map_their_own_columns(self, fixture_name, mock_usa_client):
        rows = load_json_fixture(f"awards/{fixture_name}.json")["results"]
        mock_usa_client.forbid_requests()
        pinned: set[str] = set()

        for index, row in enumerate(rows):
            award = create_award(dict(row), mock_usa_client)
            label = f"{fixture_name}[{index}]"
            # Restricted to columns the row carries: reading one it does not,
            # such as `total_account_obligation`, would send the award for a
            # detail response, which the forbidding client turns into a failure.
            pinned |= compare_volatile(label, award, AWARD_FIELDS, keys_present_only=True)
            pinned |= compare_volatile(
                f"{label} period",
                award.period_of_performance,
                PERIOD_FIELDS,
                keys_present_only=True,
            )

        assert {"award_amount", "total_obligation", "total_outlay", "start_date"} <= pinned


class TestRecordedRelatedResponses:
    """Recipient and agency payloads, which report their own aggregates."""

    def test_recipient_aggregates_map_the_payload(self, mock_usa_client):
        recipient = Recipient(load_json_fixture("recipient_university.json"), mock_usa_client)
        mock_usa_client.forbid_requests()

        pinned = compare_volatile("recipient_university", recipient, RECIPIENT_FIELDS)

        assert "total_transactions" in pinned

    def test_agency_counts_map_the_payload(self, mock_usa_client):
        agency = Agency(load_json_fixture("agency.json"), mock_usa_client)
        mock_usa_client.forbid_requests()

        pinned = compare_volatile("agency", agency, AGENCY_FIELDS)

        assert pinned == {"fiscal_year", "subtier_agency_count"}


class TestTableCoverage:
    """The tables and the golden master's volatile list must name the same set.

    Without this, a volatile property added to the snapshot suite would be
    recorded as a type tag and never compared to anything, which is the gap these
    tables exist to close.
    """

    def test_every_volatile_property_is_covered_or_declared_uncovered(self):
        covered = (COVERED_PROPERTIES - ALSO_COVERED) | KNOWN_UNCOVERED

        assert covered == set(VOLATILE_PROPERTIES)

    def test_nothing_is_both_covered_and_declared_uncovered(self):
        assert not COVERED_PROPERTIES & KNOWN_UNCOVERED
