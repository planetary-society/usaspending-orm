"""Offline pins for the flat, title-cased keys an award search result carries.

An award search row reports its recipient and its dates as flat, title-cased
columns where a detail response sends nested objects. ``Award`` hands its payload
to :meth:`Recipient._from_search_result` and
:meth:`PeriodOfPerformance._from_search_result`, which read those spellings
themselves.

The client here forbids requests, and that raise **is** the guard: a lazy load
fails at the read that caused it, naming the endpoint, so nothing below needs a
request-count assertion. What each test then asserts is the value, which is what
says the right key was read rather than merely that no fetch happened.

The two models' own key chains are pinned by ``test_recipient.py`` and
``test_period_of_performance.py``. What is left to this module is the part only
an ``Award`` can show: which payload it hands over, and which spelling wins when
it holds both.

Why this focused offline contract remains necessary
---------------------------------------------------
``tests/test_live_contract_integration.py`` checks response-backed field tables
against whatever the API currently returns. This module covers a narrower
behavior that must not depend on a live row: the exact flat keys used to build
recipient and period projections, their precedence over nested detail shapes,
and the promise that no lazy request is needed. Recorded inputs supply the shape;
expected values come from those inputs or from synthetic variables below.

Legitimate search-versus-detail differences
-------------------------------------------
A search row and a detail response are different upstream products, and several
fields genuinely differ between them. None of the following is a mapping defect,
and none should be "fixed" by asserting that a search-built model equals its
detail-built twin:

* An Indefinite Delivery Vehicle row reports ``"End Date": null`` and puts the
  figure in ``"Last Date to Order"``, a column with no detail-response
  counterpart that this library does not read. A search-built IDV therefore has
  no ``end_date`` while its detail-built twin does.
  ``tests/fixtures/awards/search_results_idvs.json`` records exactly that shape.
* Loan and direct-payment rows carry a ``"Base Obligation Date"`` where the
  detail response's ``period_of_performance.start_date`` is null, so the
  search-built model can report a start date the detail-built one cannot.
* Recipient level suffixes are per product: the same entity arrives as
  ``"<hash>-C"`` from one and ``"<hash>-R"`` from another, because each level is
  a separate record with its own totals.

The rule these tests hold to: **each model must map its own raw response
faithfully.** Agreement between a search-built model and a detail-built one is
asserted only for fields both products source identically.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.model_contracts import expected_date
from usaspending.models.award import Award


@pytest.fixture
def no_request_client(mock_usa_client):
    """A client for which any request at all is a test failure."""
    mock_usa_client.forbid_requests()
    return mock_usa_client


@pytest.fixture
def iowa_row(load_fixture) -> dict[str, Any]:
    """A recorded ``spending_by_award`` row, the University of Iowa contract.

    Fresh per test: an award replaces its payload in place when a detail fetch
    fires, so tests must not share one row.
    """
    return dict(load_fixture("awards/search_results_contracts.json")["results"][0])


class TestRecipientProjection:
    """A recipient built from a search row reads the flat, title-cased keys."""

    def test_every_flat_recipient_key_is_read(self, iowa_row, no_request_client):
        """The id and the flat spellings resolve from the row alone."""
        award = Award(iowa_row, no_request_client)

        recipient = award.recipient

        assert recipient.recipient_id == iowa_row["recipient_id"]
        assert recipient.uei == iowa_row["Recipient UEI"]
        # `name` is title-cased on the way out, so the raw "THE UNIVERSITY OF
        # IOWA" is compared case-insensitively. The casing rules themselves are
        # pinned by tests/utils/test_textcase.py; what this pins is that
        # `Recipient Name` is the key feeding them.
        assert recipient.name
        assert recipient.name.casefold() == iowa_row["Recipient Name"].casefold()

    def test_the_location_comes_from_the_flat_key(self, iowa_row, no_request_client):
        """`Recipient Location` builds the Location, with no nested `location`."""
        award = Award(iowa_row, no_request_client)

        location = award.recipient.location
        raw_location = iowa_row["Recipient Location"]

        assert location is not None
        assert location.state_code == raw_location["state_code"]
        assert location.zip5 == str(raw_location["zip5"])
        # City names are title-cased for the same reason recipient names are.
        assert location.city_name
        assert location.city_name.casefold() == raw_location["city_name"].casefold()

    def test_the_nested_recipient_wins_over_the_flat_keys(self, iowa_row, no_request_client):
        """A payload carrying both spellings resolves to the nested one.

        Which is the documented precedence, and the reason a snapshot of a
        search-built award records detail values: once a fetch has merged a
        nested `recipient`, the flat columns are no longer consulted.
        """
        nested_recipient = {
            "recipient_id": "nested-hash-R",
            "recipient_name": "Nested Fixture Recipient",
        }
        iowa_row["recipient"] = nested_recipient

        recipient = Award(iowa_row, no_request_client).recipient

        assert recipient.recipient_id == nested_recipient["recipient_id"]
        assert recipient.name == nested_recipient["recipient_name"]


class TestPeriodOfPerformanceProjection:
    """A period built from a search row reads the flat, title-cased date keys."""

    def test_the_nested_period_wins_over_the_flat_keys(self, iowa_row, no_request_client):
        """A payload carrying both spellings resolves to the nested one."""
        nested_period = {"start_date": "2001-01-01", "end_date": "2002-02-02"}
        iowa_row["period_of_performance"] = nested_period

        award = Award(iowa_row, no_request_client)

        assert award.start_date == expected_date(nested_period["start_date"])
        assert award.end_date == expected_date(nested_period["end_date"])

    def test_the_dropped_end_date_alias_stays_dropped(self, no_request_client):
        """`Period of Performance End Date` is no longer read, by design.

        `Award.end_date` used to read this spelling directly, which nothing else
        in the package or in any recorded API response uses. Delegating to
        `PeriodOfPerformance` dropped it, and that is a declared behavior change
        for the release in progress, not an oversight. A row carrying it answers
        None. The `Start Date` alongside it is what lets the period be built from
        the row at all; see the next test for why.
        """
        start_date = "2020-01-01"
        dropped_end_date = "2022-06-30"
        award = Award(
            {
                "Start Date": start_date,
                "Period of Performance End Date": dropped_end_date,
            },
            no_request_client,
        )

        assert award.start_date == expected_date(start_date)
        assert award.end_date is None

    def test_the_dropped_alias_does_not_even_keep_the_award_off_the_network(
        self, no_request_client
    ):
        """The alias is absent from `_SEARCH_KEYS`, which is the presence test.

        An award decides whether it can build a period without fetching by asking
        whether its payload carries any declared key. A payload whose only date is
        the dropped alias carries none, so it goes to the network. Pinned because
        it is the second consequence of dropping the spelling, and the one a
        reader is most likely to miss.
        """
        generated_id = "CONT_AWD_1"
        award = Award(
            {
                "generated_internal_id": generated_id,
                "Period of Performance End Date": "2022-06-30",
            },
            no_request_client,
        )

        with pytest.raises(
            AssertionError,
            match=rf"no request allowed: GET /awards/{generated_id}/",
        ):
            _ = award.end_date
