"""Transaction model for USASpending data.

A ``Transaction`` wraps one row from either of two API products:

- The award-scoped ``/transactions/`` listing, whose rows use snake_case keys
  and carry a true transaction ``id``.
- The global ``/search/spending_by_transaction/`` search, whose rows use the
  display-name keys of the requested fields (for example ``"Action Date"``)
  and identify only the parent award, never the transaction itself.

The two shapes have disjoint key spellings, so each property simply reads
both spellings and whichever is present wins. Every raw key has a getter under
its snake_cased name, alongside the library's normalized helper names, with
four deliberate exceptions: ``awarding_agency``, ``funding_agency`` and the
sub-agency spellings are reserved for the object-returning convention
``Award`` and ``Funding`` establish, so the string values live under
``*_agency_name``; ``naics``, ``psc`` and ``assistance_listing`` are
dictionaries upstream, served here through their scalar ``*_code``/
``*_description`` helpers; ``internal_id`` would read as the transaction's own
id when it is the parent award's, so it is ``award_internal_id``; and
``generated_internal_id`` is normalized to ``generated_unique_award_id``
exactly as ``Award`` normalizes the same key.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import cached_property
from typing import ClassVar

from ..utils.dates import to_date
from ..utils.numbers import to_decimal, to_int
from ..utils.textcase import TextFormatter, titlecase_name
from .base_model import BaseModel
from .location import Location


class Transaction(BaseModel):
    """Represents a single transaction record for an award."""

    # The documented field names of the spending_by_transaction endpoint. The
    # server appends `internal_id` and `generated_internal_id` to every row
    # whether or not they are requested, so neither is listed. Deliberately
    # excluded: undocumented slug fields, the scalar components that repeat
    # what the derived dict fields (Recipient Location, Primary Place of
    # Performance, NAICS, PSC, Assistance Listing) already carry, and
    # `awarding_agency_id`, an internal database id the library's name-based
    # agency filters never need.
    SEARCH_FIELDS: ClassVar[list[str]] = [
        "Award ID",
        "Mod",
        "Recipient Name",
        "Recipient UEI",
        "Action Date",
        "Action Type",
        "Award Type",
        "Transaction Amount",
        "Transaction Description",
        "Awarding Agency",
        "Awarding Sub Agency",
        "Funding Agency",
        "Funding Sub Agency",
        "Loan Value",
        "Subsidy Cost",
        "Issued Date",
        "Last Date to Order",
        "Recipient Location",
        "Primary Place of Performance",
        "NAICS",
        "PSC",
        "Assistance Listing",
        "recipient_id",
        "def_codes",
    ]

    # --- Identity ---

    @property
    def id(self) -> str | None:
        """Transaction identifier, carried by award-scoped rows only.

        Global search rows identify the parent award but not the transaction,
        so this is None for them; see :attr:`award_internal_id` and
        :attr:`generated_unique_award_id` for the identifiers they do carry.

        Returns:
            Optional[str]: The internal transaction ID, or None.
        """
        return self.get_value("id")

    @property
    def award_internal_id(self) -> int | None:
        """Internal database ID of the parent award, from global search rows.

        Returns:
            Optional[int]: The award's internal ID, or None.
        """
        return to_int(self.get_value("internal_id"))

    @property
    def generated_unique_award_id(self) -> str | None:
        """Generated unique identifier of the parent award.

        Reads the same alias pair :class:`~usaspending.models.award.Award`
        reads, since the global search reports this under
        ``generated_internal_id``.

        Returns:
            Optional[str]: The generated unique award ID, or None.
        """
        return self.get_value(["generated_unique_award_id", "generated_internal_id"])

    @property
    def award_identifier(self) -> str | None:
        """Human-facing parent award ID (PIID, FAIN or URI), from global rows.

        Returns:
            Optional[str]: The display award ID, or None.
        """
        return self.get_value("Award ID")

    @property
    def award_id(self) -> str | None:
        """Alias for :attr:`award_identifier`, matching the raw "Award ID" key.

        The display PIID, FAIN or URI, distinct from :attr:`award_internal_id`
        and :attr:`generated_unique_award_id`.

        Returns:
            Optional[str]: The display award ID, or None.
        """
        return self.award_identifier

    # --- Amounts ---

    @property
    def transaction_amount(self) -> Decimal | None:
        """The transaction's own dollar figure.

        The first nonzero of federal action obligation, loan face value and
        loan subsidy cost. Loan rows report a zero obligation with the real
        figure in the loan fields, so a zero falls through to them; when every
        present amount is zero the result is zero, not None, since a zero
        obligation is still a real transaction. Negative figures, such as
        deobligations, are preserved.

        Note:
            For loans this reports the face value, the figure USAspending.gov
            displays as a loan's amount. That deliberately differs from the
            site's internal "pragmatic obligation" convention, which uses the
            subsidy cost (the budgetary cost) for loans, so summing this
            property over a result set that mixes loans with other categories
            mixes credit volume with obligations. Read
            :attr:`original_loan_subsidy_cost` directly for budgetary totals.

        Returns:
            Optional[Decimal]: The transaction amount, or None when the row
            carries none of the three fields.
        """
        amounts = [
            value
            for value in (
                self.federal_action_obligation,
                self.face_value_loan_guarantee,
                self.original_loan_subsidy_cost,
            )
            if value is not None
        ]
        for value in amounts:
            if value != 0:
                return value
        return amounts[0] if amounts else None

    @property
    def amount(self) -> Decimal | None:
        """Alias for :attr:`transaction_amount`, matching ``SubAward.amount``.

        Returns:
            Optional[Decimal]: The transaction amount, or None.
        """
        return self.transaction_amount

    @property
    def amt(self) -> Decimal | None:
        """Alias for :attr:`transaction_amount`.

        Returns:
            Optional[Decimal]: The transaction amount, or None.
        """
        return self.transaction_amount

    @property
    def federal_action_obligation(self) -> Decimal | None:
        """Federal action obligation amount.

        Returns:
            Optional[Decimal]: The federal action obligation, or None.
        """
        return to_decimal(self.get_value(["federal_action_obligation", "Transaction Amount"]))

    @property
    def face_value_loan_guarantee(self) -> Decimal | None:
        """Face value of loan guarantee.

        Returns:
            Optional[Decimal]: The face value loan guarantee amount, or None.
        """
        return to_decimal(self.get_value(["face_value_loan_guarantee", "Loan Value"]))

    @property
    def loan_value(self) -> Decimal | None:
        """Alias for :attr:`face_value_loan_guarantee`, matching "Loan Value".

        Returns:
            Optional[Decimal]: The face value loan guarantee amount, or None.
        """
        return self.face_value_loan_guarantee

    @property
    def original_loan_subsidy_cost(self) -> Decimal | None:
        """Original loan subsidy cost.

        Returns:
            Optional[Decimal]: The original loan subsidy cost, or None.
        """
        return to_decimal(self.get_value(["original_loan_subsidy_cost", "Subsidy Cost"]))

    @property
    def subsidy_cost(self) -> Decimal | None:
        """Alias for :attr:`original_loan_subsidy_cost`, matching "Subsidy Cost".

        Returns:
            Optional[Decimal]: The original loan subsidy cost, or None.
        """
        return self.original_loan_subsidy_cost

    # --- Action ---

    @property
    def type(self) -> str | None:
        """Transaction type code.

        Returns:
            Optional[str]: The transaction type code, or None.
        """
        return self.get_value("type")

    @property
    def type_description(self) -> str | None:
        """Description of the transaction type.

        Global search rows report this under "Award Type".

        Returns:
            Optional[str]: The transaction type description, or None.
        """
        return self.get_value(["type_description", "Award Type"])

    @property
    def award_type(self) -> str | None:
        """Alias for :attr:`type_description`, matching the raw "Award Type" key.

        The description string upstream reports under that label, not the type
        code, which is :attr:`type`.

        Returns:
            Optional[str]: The transaction type description, or None.
        """
        return self.type_description

    @property
    def action_date(self) -> date | None:
        """Date the transaction action occurred.

        Returns:
            Optional[date]: The action date, or None.
        """
        return to_date(self.get_value(["action_date", "Action Date"]))

    @property
    def action_type(self) -> str | None:
        """Action type code.

        Returns:
            Optional[str]: The action type code, or None.
        """
        return self.get_value(["action_type", "Action Type"])

    @property
    def action_type_description(self) -> str | None:
        """Description of the action type.

        Returns:
            Optional[str]: The action type description, or None.
        """
        return self.get_value("action_type_description")

    @property
    def modification_number(self) -> str | None:
        """Modification number for the transaction.

        Returns:
            Optional[str]: The modification number, or None.
        """
        return self.get_value(["modification_number", "Mod"])

    @property
    def mod(self) -> str | None:
        """Alias for :attr:`modification_number`, matching the raw "Mod" key.

        Returns:
            Optional[str]: The modification number, or None.
        """
        return self.modification_number

    # --- Descriptions ---

    @property
    def transaction_description(self) -> str:
        """Description of this transaction.

        Returns:
            str: The transaction description in sentence case, or an empty
            string.
        """
        return TextFormatter.to_sentence_case(
            self.get_value(["description", "Transaction Description"])
        )

    @property
    def description(self) -> str:
        """Alias for :attr:`transaction_description`, matching the raw key.

        Returns:
            str: The transaction description in sentence case, or an empty
            string.
        """
        return self.transaction_description

    @property
    def award_description(self) -> str:
        """Legacy name for :attr:`transaction_description`.

        The award-scoped endpoint sends the transaction's own description under
        the key ``description``, which this property's name predates
        recognizing. Kept for compatibility; prefer
        :attr:`transaction_description`.

        Returns:
            str: The transaction description in sentence case, or an empty string.
        """
        return TextFormatter.to_sentence_case(self.get_value("description"))

    # --- Recipient and agencies ---

    @property
    def recipient_name(self) -> str | None:
        """Name of the recipient, from global search rows.

        Returns:
            Optional[str]: The recipient name in title case, or None.
        """
        return titlecase_name(self.get_value("Recipient Name"))

    @property
    def recipient_uei(self) -> str | None:
        """Unique Entity Identifier of the recipient, from global search rows.

        Returns:
            Optional[str]: The recipient UEI, or None.
        """
        return self.get_value("Recipient UEI")

    @property
    def recipient_id(self) -> str | None:
        """Recipient hash identifier with level suffix, from global search rows.

        Returns:
            Optional[str]: The recipient ID such as ``"<hash>-C"``, or None.
        """
        return self.get_value("recipient_id")

    @property
    def awarding_agency_name(self) -> str | None:
        """Name of the awarding toptier agency, from global search rows.

        Returns:
            Optional[str]: The awarding agency name, or None.
        """
        return self.get_value("Awarding Agency")

    @property
    def awarding_sub_agency_name(self) -> str | None:
        """Name of the awarding subtier agency, from global search rows.

        Returns:
            Optional[str]: The awarding subtier agency name, or None.
        """
        return self.get_value("Awarding Sub Agency")

    @property
    def funding_agency_name(self) -> str | None:
        """Name of the funding toptier agency, from global search rows.

        Returns:
            Optional[str]: The funding agency name, or None.
        """
        return self.get_value("Funding Agency")

    @property
    def funding_sub_agency_name(self) -> str | None:
        """Name of the funding subtier agency, from global search rows.

        Returns:
            Optional[str]: The funding subtier agency name, or None.
        """
        return self.get_value("Funding Sub Agency")

    # --- Dates from the parent award ---

    @property
    def issued_date(self) -> date | None:
        """Date the API reports under "Issued Date", from global search rows.

        Upstream fills this from the transaction's own reported
        period-of-performance start date. Each modification restates it, so it
        usually equals the award's start date; it is not the action date.

        Returns:
            Optional[date]: The reported issued date, or None.
        """
        return to_date(self.get_value("Issued Date"))

    @property
    def last_date_to_order(self) -> date | None:
        """End of the parent IDV's ordering period, from global search rows.

        Returns:
            Optional[date]: The last date to order, or None.
        """
        return to_date(self.get_value("Last Date to Order"))

    # --- Classifications ---

    def _classification_value(self, key: str, field: str) -> str | None:
        """Read one field from a nested classification dictionary.

        The global search returns NAICS, PSC and Assistance Listing as small
        dictionaries; this is the one place that reads inside them.

        Args:
            key: Row key holding the dictionary, such as ``"NAICS"``.
            field: Field within it, such as ``"code"``.

        Returns:
            Optional[str]: The value, or None when the dictionary is absent.
        """
        data = self.get_value(key)
        if isinstance(data, dict):
            return data.get(field)
        return None

    @property
    def naics_code(self) -> str | None:
        """NAICS industry classification code, from global search rows.

        Returns:
            Optional[str]: The NAICS code, or None.
        """
        return self._classification_value("NAICS", "code")

    @property
    def naics_description(self) -> str | None:
        """NAICS industry classification description, from global search rows.

        Returns:
            Optional[str]: The NAICS description, or None.
        """
        return self._classification_value("NAICS", "description")

    @property
    def psc_code(self) -> str | None:
        """Product/Service Code, from global search rows.

        Returns:
            Optional[str]: The PSC code, or None.
        """
        return self._classification_value("PSC", "code")

    @property
    def psc_description(self) -> str | None:
        """Product/Service Code description, from global search rows.

        Returns:
            Optional[str]: The PSC description, or None.
        """
        return self._classification_value("PSC", "description")

    @property
    def cfda_number(self) -> str | None:
        """Catalog of Federal Domestic Assistance (CFDA) number.

        Award-scoped rows carry it flat; global rows nest it in the
        ``Assistance Listing`` dictionary.

        Returns:
            Optional[str]: The CFDA number, or None.
        """
        value = self.get_value("cfda_number")
        if value is not None:
            return value
        return self._classification_value("Assistance Listing", "cfda_number")

    @property
    def cfda_title(self) -> str | None:
        """Title of the assistance listing, from global search rows.

        Returns:
            Optional[str]: The CFDA title, or None.
        """
        return self._classification_value("Assistance Listing", "cfda_title")

    @property
    def def_codes(self) -> list[str]:
        """Disaster Emergency Fund codes, from global search rows.

        Returns:
            list[str]: The DEF codes, or an empty list.
        """
        value = self.get_value("def_codes")
        return list(value) if isinstance(value, list) else []

    # --- Locations ---

    def _location(self, key: str) -> Location | None:
        """Build a Location from a nested location dictionary, if present.

        Args:
            key: Row key holding the location dictionary.

        Returns:
            Optional[Location]: The location, or None when absent.
        """
        data = self.get_value(key)
        return Location(data) if isinstance(data, dict) else None

    @cached_property
    def recipient_location(self) -> Location | None:
        """Location of the recipient, from global search rows.

        Returns:
            Optional[Location]: The recipient location, or None.
        """
        return self._location("Recipient Location")

    @cached_property
    def place_of_performance(self) -> Location | None:
        """Primary place of performance, from global search rows.

        Returns:
            Optional[Location]: The place of performance, or None.
        """
        return self._location("Primary Place of Performance")

    @property
    def primary_place_of_performance(self) -> Location | None:
        """Alias for :attr:`place_of_performance`, matching the raw key.

        Returns:
            Optional[Location]: The place of performance, or None.
        """
        return self.place_of_performance

    def __repr__(self) -> str:
        """String representation of Transaction.

        Returns:
            str: String containing an identifier, action date, and amount.
        """
        identifier = self.id or self.award_identifier or "?"
        return f"<Txn {identifier} {self.action_date or '?'} {self.amt}>"
