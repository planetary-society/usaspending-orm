"""Offline pins for the display-name keys a global transaction search row carries.

``Transaction`` wraps rows from two API products whose key spellings are
disjoint:

* the award-scoped ``/transactions/`` listing, whose rows use snake_case keys and
  carry a true transaction ``id`` such as ``"CONT_TX_..."``;
* the global ``/search/spending_by_transaction/`` search, whose rows use the
  display names of the requested fields (``"Action Date"``, ``"Transaction
  Amount"``, ...), plus the ``internal_id`` and ``generated_internal_id`` the
  server appends to every row, and which identify only the parent award --
  never the transaction itself.

``tests/models/test_transaction.py`` pins the award-scoped side. What is left to
this module is the global side: which display name feeds each property, which
typed value comes back out, and the handful of places where the two shapes are
deliberately not symmetric (see :class:`TestDescriptions` and
:class:`TestIdentity`).

The recorded rows in ``tests/fixtures/spending_by_transaction.json`` are all
contracts, so shapes those rows cannot show -- a loan, a zero obligation, a
deobligation, an assistance listing that is actually populated -- are built by
hand alongside them.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from usaspending.models.location import Location
from usaspending.models.transaction import Transaction


@pytest.fixture
def search_rows(load_fixture) -> list[dict[str, Any]]:
    """The recorded rows of a real ``spending_by_transaction`` response."""
    return load_fixture("spending_by_transaction.json")["results"]


@pytest.fixture
def clipper_row(search_rows) -> dict[str, Any]:
    """One recorded row: a Europa Clipper delivery order to Caltech."""
    return search_rows[0]


@pytest.fixture
def clipper(clipper_row) -> Transaction:
    """A transaction built from the recorded global search row."""
    return Transaction(clipper_row)


class TestIdentity:
    """A global row identifies the parent award, never the transaction."""

    def test_id_is_none_for_a_global_row(self, clipper):
        """The search reports no transaction identity, so `id` has nothing to read."""
        assert clipper.id is None

    def test_award_internal_id_reads_internal_id(self, clipper):
        """`internal_id` is the parent award's database id, sent as an integer."""
        assert clipper.award_internal_id == 311433720
        assert isinstance(clipper.award_internal_id, int)

    def test_generated_unique_award_id_reads_generated_internal_id(self, clipper):
        """The global search reports the generated award id under its own spelling."""
        assert clipper.generated_unique_award_id == "CONT_AWD_NNN13D494T_8000_NNN12AA01C_8000"

    def test_generated_unique_award_id_reads_the_award_scoped_spelling(self):
        """The same alias pair `Award` reads, so an award-shaped dict resolves too."""
        transaction = Transaction({"generated_unique_award_id": "CONT_AWD_1_2_3_4"})

        assert transaction.generated_unique_award_id == "CONT_AWD_1_2_3_4"

    def test_the_award_scoped_spelling_wins_when_a_row_carries_both(self):
        """Alias order is the precedence: the snake_case spelling is tried first."""
        transaction = Transaction(
            {
                "generated_unique_award_id": "CONT_AWD_SNAKE",
                "generated_internal_id": "CONT_AWD_DISPLAY",
            }
        )

        assert transaction.generated_unique_award_id == "CONT_AWD_SNAKE"

    def test_award_identifier_reads_award_id(self, clipper):
        """`Award ID` is the human-facing parent award id (PIID, FAIN or URI)."""
        assert clipper.award_identifier == "NNN13D494T"

    def test_type_has_no_global_spelling(self, clipper):
        """`type` reads only the award-scoped key, unlike `type_description`.

        The global row's `Award Type` carries the description ("DELIVERY ORDER"),
        not the one-letter code, so there is no code for `type` to report.
        """
        assert clipper.type is None
        assert clipper.type_description == "DELIVERY ORDER"


class TestDisplayNameAliases:
    """Each display name feeds its property, and the value comes back typed."""

    def test_action_date_is_a_date(self, clipper):
        """`Action Date` arrives as a string and is coerced to a date."""
        assert clipper.action_date == date(2018, 5, 1)
        assert isinstance(clipper.action_date, date)

    def test_action_type(self, clipper):
        """`Action Type` carries the one-letter action code."""
        assert clipper.action_type == "C"

    def test_type_description_reads_award_type(self, clipper):
        """`Award Type` is where the global row puts the type description."""
        assert clipper.type_description == "DELIVERY ORDER"

    def test_modification_number_reads_mod(self, clipper):
        """`Mod` is the global spelling of the modification number."""
        assert clipper.modification_number == "40"

    def test_action_type_description_has_no_global_spelling(self, clipper):
        """Only the award-scoped listing reports the expanded action type."""
        assert clipper.action_type_description is None


class TestAmounts:
    """Amounts are Decimals, and zero is a figure rather than a missing value."""

    def test_federal_action_obligation_reads_transaction_amount(self, clipper):
        """`Transaction Amount` feeds the obligation, coerced to two places."""
        assert clipper.federal_action_obligation == Decimal("350198386.00")

    def test_face_value_loan_guarantee_reads_loan_value(self, clipper):
        """`Loan Value` feeds the loan face value; a contract row reports zero."""
        assert clipper.face_value_loan_guarantee == Decimal("0.00")

    def test_original_loan_subsidy_cost_reads_subsidy_cost(self, clipper):
        """`Subsidy Cost` feeds the loan subsidy cost; a contract row reports zero."""
        assert clipper.original_loan_subsidy_cost == Decimal("0.00")

    def test_transaction_amount_is_the_obligation_when_present(self, clipper):
        """The obligation is the first of the three candidates, so it wins."""
        assert clipper.transaction_amount == clipper.federal_action_obligation
        assert clipper.amt == clipper.transaction_amount

    def test_loan_row_amount_falls_through_zero_obligation(self):
        """A live loan row reports a zero obligation with the figure in Loan Value.

        The full selection matrix (zero, negative, fallback order, all-None) is
        pinned in ``test_transaction.py``; this pins its composition with the
        display-name keys on the shape where the loan behavior was discovered.
        """
        transaction = Transaction(
            {
                "Award ID": "LOAN-1",
                "Award Type": "DIRECT LOAN",
                "Transaction Amount": 0.0,
                "Loan Value": 1000000.0,
                "Subsidy Cost": 5000.0,
            }
        )

        assert transaction.transaction_amount == Decimal("1000000.00")
        assert transaction.amt == Decimal("1000000.00")


class TestDescriptions:
    """`transaction_description` reads both shapes; `award_description` does not."""

    def test_transaction_description_reads_the_display_key(self, clipper):
        """`Transaction Description` feeds the sentence-cased description.

        The casing rules themselves are pinned by tests/utils/test_textcase.py.
        What matters here is that the display key is read at all; the leading
        "Igf::CL::igf" is what those rules make of the raw "IGF::CL::IGF" -- the
        first token is capitalized as the start of the sentence, "CL" and
        "Europa" survive as special cases, and the rest lowercases.
        """
        assert clipper.transaction_description.startswith(
            "Igf::CL::igf Europa clipper mission: pre-phase a and phase a"
        )

    def test_transaction_description_reads_the_award_scoped_key(self):
        """The award-scoped listing sends the same text under `description`."""
        transaction = Transaction({"description": "THE TANDEM RECONNECTION...."})

        assert transaction.transaction_description == "The tandem reconnection...."

    def test_award_description_reads_only_the_award_scoped_key(self, clipper):
        """`award_description` is deliberately not taught the display spelling.

        It is the legacy name for `transaction_description`, kept for
        compatibility with callers of the award-scoped listing. Teaching it the
        global spelling would spread a misleading name -- the text is the
        transaction's own description, not the parent award's -- so a global row
        answers the empty string and callers are pushed to the current name.
        """
        assert clipper.award_description == ""
        assert clipper.transaction_description != ""

    def test_award_description_still_serves_an_award_scoped_row(self):
        """The compatibility path itself keeps working, sentence casing included."""
        transaction = Transaction({"description": "THE TANDEM RECONNECTION...."})

        assert transaction.award_description == "The tandem reconnection...."

    def test_a_row_with_no_description_answers_the_empty_string(self):
        """Both descriptions answer "" rather than None when nothing is there."""
        transaction = Transaction({})

        assert transaction.transaction_description == ""
        assert transaction.award_description == ""


class TestRecipientAndAgencies:
    """Recipient and agency columns, with names cased on the way out."""

    def test_recipient_name_is_title_cased(self, clipper):
        """`Recipient Name` arrives uppercased and is title-cased for display."""
        assert clipper.recipient_name == "California Institute of Technology"

    def test_recipient_uei_passes_through(self, clipper):
        """`Recipient UEI` is an identifier, so it is reported as sent."""
        assert clipper.recipient_uei == "YC1YP79BFD19"

    def test_recipient_id_passes_through(self, clipper):
        """`recipient_id` carries the hash plus its level suffix, unchanged."""
        assert clipper.recipient_id == "6e76fa33-2d96-c636-941c-bca1997db076-C"

    def test_agency_names(self, clipper):
        """All four agency columns are read, toptier and subtier, both sides."""
        agency = "National Aeronautics and Space Administration"

        assert clipper.awarding_agency_name == agency
        assert clipper.awarding_sub_agency_name == agency
        assert clipper.funding_agency_name == agency
        assert clipper.funding_sub_agency_name == agency

    def test_recipient_and_agency_columns_are_absent_from_an_award_scoped_row(self):
        """None of these have an award-scoped spelling, so that shape answers None."""
        transaction = Transaction({"id": "CONT_TX_1", "description": "X"})

        assert transaction.recipient_name is None
        assert transaction.recipient_uei is None
        assert transaction.recipient_id is None
        assert transaction.awarding_agency_name is None
        assert transaction.funding_agency_name is None


class TestParentAwardDates:
    """Two date columns that describe the parent award, not the transaction."""

    def test_issued_date_is_a_date(self, clipper):
        """`Issued Date` is coerced like any other date column."""
        assert clipper.issued_date == date(2018, 5, 1)

    def test_last_date_to_order_is_none_when_the_row_reports_null(self, clipper):
        """Only an IDV has an ordering period; a delivery order reports null."""
        assert clipper.raw["Last Date to Order"] is None
        assert clipper.last_date_to_order is None

    def test_last_date_to_order_parses_when_the_row_reports_one(self):
        """An IDV row's ordering-period end is coerced to a date."""
        transaction = Transaction({"Last Date to Order": "2026-09-30"})

        assert transaction.last_date_to_order == date(2026, 9, 30)


class TestClassifications:
    """NAICS, PSC and Assistance Listing arrive as small nested dictionaries."""

    def test_naics_code_and_description(self, clipper):
        """Both NAICS fields are read from inside the nested dictionary."""
        assert clipper.naics_code == "541712"
        assert clipper.naics_description == (
            "RESEARCH AND DEVELOPMENT IN THE PHYSICAL, ENGINEERING, AND LIFE "
            "SCIENCES (EXCEPT BIOTECHNOLOGY)"
        )

    def test_psc_code_and_description(self, clipper):
        """Both PSC fields are read from inside the nested dictionary."""
        assert clipper.psc_code == "AR22"
        assert clipper.psc_description == (
            "R&D- SPACE: SCIENCE/APPLICATIONS (APPLIED RESEARCH/EXPLORATORY DEVELOPMENT)"
        )

    def test_none_when_the_nested_dictionary_is_absent(self):
        """A row that never carried the column answers None, not an error."""
        transaction = Transaction({})

        assert transaction.naics_code is None
        assert transaction.naics_description is None
        assert transaction.psc_code is None
        assert transaction.psc_description is None

    def test_none_when_the_nested_dictionary_is_null(self):
        """An explicit null is not a dictionary, so it reads the same as absent."""
        transaction = Transaction({"NAICS": None, "PSC": None})

        assert transaction.naics_code is None
        assert transaction.psc_code is None

    def test_cfda_number_is_none_when_the_listing_is_empty(self, clipper):
        """A contract row carries the column with null fields inside it.

        Which is why the fixture cannot show the populated path: the recorded
        rows are all contracts, and an `Assistance Listing` full of nulls reads
        exactly as no assistance listing at all.
        """
        assert clipper.raw["Assistance Listing"] == {"cfda_number": None, "cfda_title": None}
        assert clipper.cfda_number is None
        assert clipper.cfda_title is None

    def test_cfda_number_reads_the_nested_listing(self):
        """An assistance row reports the CFDA number inside the dictionary."""
        transaction = Transaction(
            {
                "Assistance Listing": {
                    "cfda_number": "43.008",
                    "cfda_title": "Office of Stem Engagement",
                }
            }
        )

        assert transaction.cfda_number == "43.008"
        assert transaction.cfda_title == "Office of Stem Engagement"

    def test_the_flat_cfda_number_wins_over_the_nested_one(self):
        """The award-scoped spelling is checked first, so it takes precedence."""
        transaction = Transaction(
            {
                "cfda_number": "43.001",
                "Assistance Listing": {"cfda_number": "99.999", "cfda_title": "Ignored"},
            }
        )

        assert transaction.cfda_number == "43.001"

    def test_cfda_number_is_none_when_neither_spelling_is_present(self):
        """Neither flat key nor nested dictionary means no CFDA number."""
        assert Transaction({}).cfda_number is None
        assert Transaction({}).cfda_title is None

    def test_def_codes_from_the_row(self, clipper):
        """`def_codes` is reported as a list and comes back as one."""
        assert clipper.def_codes == ["Q"]

    def test_def_codes_is_empty_when_the_key_is_absent(self):
        """A missing list answers an empty list, so callers can always iterate."""
        assert Transaction({}).def_codes == []
        assert Transaction({"def_codes": None}).def_codes == []


class TestLocations:
    """The two location columns build `Location` objects from their dictionaries."""

    def test_recipient_location(self, clipper):
        """`Recipient Location` builds a Location that reads its own keys."""
        location = clipper.recipient_location

        assert isinstance(location, Location)
        # City names are title-cased by Location, as everywhere else.
        assert location.city == "Pasadena"
        assert location.state_code == "CA"
        assert location.zip5 == "91109"

    def test_place_of_performance(self, clipper):
        """`Primary Place of Performance` builds the second Location."""
        location = clipper.place_of_performance

        assert isinstance(location, Location)
        assert location.city == "Pasadena"
        assert location.state_code == "CA"
        assert location.zip5 == "91109"

    def test_none_when_the_location_key_is_absent(self):
        """An award-scoped row carries no locations, so both answer None."""
        transaction = Transaction({"id": "CONT_TX_1"})

        assert transaction.recipient_location is None
        assert transaction.place_of_performance is None

    def test_none_when_the_location_key_is_null(self):
        """An explicit null is not a dictionary, so no Location is built."""
        transaction = Transaction(
            {"Recipient Location": None, "Primary Place of Performance": None}
        )

        assert transaction.recipient_location is None
        assert transaction.place_of_performance is None


class TestRawAndRepr:
    """The row is kept as sent, and the repr falls back to the award id."""

    def test_raw_returns_the_row_unmodified(self, clipper, clipper_row):
        """No key is rewritten on the way in; the display names survive intact.

        The dual-shape reading happens per property, so the payload the model
        holds is the response verbatim -- which is what makes `raw` usable for
        the columns this model does not expose.
        """
        assert clipper.raw is clipper_row
        assert clipper.raw["Award ID"] == "NNN13D494T"
        assert clipper.raw["Transaction Amount"] == 350198386.0
        assert "id" not in clipper.raw

    def test_repr_falls_back_to_the_award_identifier(self, clipper):
        """With no transaction id, the repr names the parent award instead."""
        assert repr(clipper) == "<Txn NNN13D494T 2018-05-01 350198386.00>"

    def test_every_recorded_row_reads_as_a_global_transaction(self, search_rows):
        """The whole recorded response, not just the first row, reads consistently."""
        transactions = [Transaction(row) for row in search_rows]

        assert len(transactions) == 3
        for transaction in transactions:
            assert transaction.id is None
            assert transaction.award_identifier is not None
            assert isinstance(transaction.award_internal_id, int)
            assert transaction.generated_unique_award_id.startswith("CONT_AWD_")
            assert isinstance(transaction.action_date, date)
            assert transaction.type_description == "DELIVERY ORDER"
            assert transaction.recipient_name == "California Institute of Technology"
            assert transaction.amt == transaction.federal_action_obligation
            assert transaction.amt > 0


class TestRawKeyAliases:
    """Every raw key reads through a getter matching its snake_cased name.

    Each alias delegates to a normalized helper; these pins keep the pairs
    from drifting. The deliberate exceptions (agency names, dict-valued
    classifications, the server's award identifiers) are documented in the
    module docstring.
    """

    @pytest.mark.parametrize(
        ("alias", "target"),
        [
            ("award_id", "award_identifier"),
            ("mod", "modification_number"),
            ("award_type", "type_description"),
            ("amount", "transaction_amount"),
            ("amt", "transaction_amount"),
            ("loan_value", "face_value_loan_guarantee"),
            ("subsidy_cost", "original_loan_subsidy_cost"),
            ("description", "transaction_description"),
            ("primary_place_of_performance", "place_of_performance"),
        ],
    )
    def test_alias_matches_its_target(self, clipper, alias, target):
        """The alias and its normalized helper answer identically."""
        assert getattr(clipper, alias) == getattr(clipper, target)
