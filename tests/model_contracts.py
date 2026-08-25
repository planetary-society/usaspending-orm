"""Response-derived model contracts shared by offline and live tests.

Each contract identifies which raw response key a model property reads and
applies an independent test-side coercion. Expected values therefore come from
the fixture or live response used to build the model, never from hard-coded
output snapshots. Upstream values may change freely while wrong keys and
conversions still fail.

The tables run against recorded inputs in
``tests/models/test_model_field_contracts.py`` and against current API responses
in ``tests/test_live_contract_integration.py``.

The coercions are restated here rather than imported from ``usaspending.utils``.
A comparison that ran the raw value through the very function it is checking
would agree with itself by construction, including about a wrong scale or
rounding mode.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable, NamedTuple

from usaspending.models.grant import Grant
from usaspending.models.loan import Loan


def expected_money(value: Any) -> Decimal:
    """Coerce a raw API number the way a money property is documented to.

    Args:
        value: A raw number, or the string the API often sends instead.

    Returns:
        Decimal: The value at two decimal places, rounded half up.
    """
    return Decimal(str(value)).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)


def expected_date(value: Any) -> date:
    """Read the date portion of a raw API date, the way ``to_date`` is documented to.

    Args:
        value: A raw date, which the API sends either as ``YYYY-MM-DD`` or as a
            datetime whose date portion is what a date property reports.

    Returns:
        date: The date the value names.
    """
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


class FieldContract(NamedTuple):
    """One model property and the raw response keys it is meant to read.

    Attributes:
        prop: The property name on the model.
        keys: Every raw key the property reads, in the order it reads them.
        coerce: The coercion the property applies to a raw value.
        default: What the property answers when no key carries a value.
        owner: The class that declares this key chain, or None when the chain is
            the same for every class defining the property. Where a subclass
            narrows or widens what it inherits, both are listed and the most
            derived owner wins. Matched by ``isinstance``, so a future subclass
            keeps the chain it inherits rather than dropping out.
    """

    prop: str
    keys: tuple[str, ...]
    coerce: Callable[[Any], Any]
    default: Any = None
    owner: type | None = None


#: Money and count properties on an award. A property the class in hand does not
#: define is skipped, so this one table covers Award and all four subtypes.
AWARD_FIELDS: tuple[FieldContract, ...] = (
    FieldContract(
        "award_amount",
        ("Award Amount", "Loan Amount", "total_obligation", "total_funding"),
        expected_money,
    ),
    FieldContract("base_and_all_options", ("base_and_all_options",), expected_money),
    FieldContract("base_exercised_options", ("base_exercised_options",), expected_money),
    FieldContract(
        "covid19_obligations", ("covid19_obligations", "COVID-19 Obligations"), expected_money
    ),
    FieldContract("covid19_outlays", ("covid19_outlays", "COVID-19 Outlays"), expected_money),
    FieldContract(
        "infrastructure_obligations",
        ("infrastructure_obligations", "Infrastructure Obligations"),
        expected_money,
    ),
    FieldContract(
        "infrastructure_outlays",
        ("infrastructure_outlays", "Infrastructure Outlays"),
        expected_money,
    ),
    # The one property here that answers a figure rather than None when the award
    # reports nothing.
    FieldContract("subaward_count", ("subaward_count",), int, default=0),
    FieldContract("total_account_obligation", ("total_account_obligation",), expected_money),
    FieldContract("total_account_outlay", ("total_account_outlay",), expected_money),
    FieldContract("total_funding", ("total_funding",), expected_money),
    FieldContract("total_loan_value", ("Loan Value", "total_loan_value"), expected_money),
    FieldContract("total_obligation", ("total_obligation", "Award Amount"), expected_money),
    FieldContract("total_outlay", ("total_outlay", "Total Outlays"), expected_money),
    FieldContract("total_subaward_amount", ("total_subaward_amount",), expected_money),
    # Loan overrides the property it inherits to prefer the flat search spelling,
    # which Grant does not read. Listed as two entries rather than one merged
    # chain, which would hide the difference on a row carrying "Subsidy Cost".
    FieldContract("total_subsidy_cost", ("total_subsidy_cost",), expected_money, owner=Grant),
    FieldContract(
        "total_subsidy_cost", ("Subsidy Cost", "total_subsidy_cost"), expected_money, owner=Loan
    ),
)

#: Dates on a period of performance. Run against the period model rather than the
#: award, so ``raw`` is the payload the dates are actually read from: the nested
#: object from a detail response, or the projection taken from a search row.
PERIOD_FIELDS: tuple[FieldContract, ...] = (
    FieldContract(
        "start_date",
        ("start_date", "Start Date", "Period of Performance Start Date", "Base Obligation Date"),
        expected_date,
    ),
    FieldContract(
        "end_date",
        ("end_date", "End Date", "Period of Performance Current End Date"),
        expected_date,
    ),
    FieldContract(
        "last_modified_date", ("last_modified_date", "Last Modified Date"), expected_date
    ),
)

#: The recipient-side aggregates, which the API computes and revises.
RECIPIENT_FIELDS: tuple[FieldContract, ...] = (
    FieldContract(
        "total_face_value_loan_amount", ("total_face_value_loan_amount",), expected_money
    ),
    FieldContract(
        "total_face_value_loan_transactions", ("total_face_value_loan_transactions",), int
    ),
    FieldContract("total_transaction_amount", ("total_transaction_amount",), expected_money),
    FieldContract("total_transactions", ("total_transactions",), int),
)

#: Agency figures that move with each ingest.
AGENCY_FIELDS: tuple[FieldContract, ...] = (
    FieldContract("fiscal_year", ("fiscal_year",), int),
    FieldContract("subtier_agency_count", ("subtier_agency_count",), int),
)

TRANSACTION_FIELDS: tuple[FieldContract, ...] = (
    FieldContract("id", ("id",), str),
    FieldContract("award_internal_id", ("internal_id",), int),
    FieldContract(
        "generated_unique_award_id",
        ("generated_unique_award_id", "generated_internal_id"),
        str,
    ),
    FieldContract("award_identifier", ("Award ID",), str),
    FieldContract("award_id", ("Award ID",), str),
    FieldContract("action_date", ("action_date", "Action Date"), expected_date),
    FieldContract("action_type", ("action_type", "Action Type"), str),
    FieldContract("type_description", ("type_description", "Award Type"), str),
    FieldContract("modification_number", ("modification_number", "Mod"), str),
    FieldContract(
        "federal_action_obligation",
        ("federal_action_obligation", "Transaction Amount"),
        expected_money,
    ),
    FieldContract(
        "face_value_loan_guarantee",
        ("face_value_loan_guarantee", "Loan Value"),
        expected_money,
    ),
    FieldContract(
        "original_loan_subsidy_cost",
        ("original_loan_subsidy_cost", "Subsidy Cost"),
        expected_money,
    ),
)

AWARD_ACCOUNT_FIELDS: tuple[FieldContract, ...] = (
    FieldContract(
        "total_transaction_obligated_amount",
        ("total_transaction_obligated_amount",),
        expected_money,
    ),
    FieldContract(
        "obligated_amount",
        ("total_transaction_obligated_amount",),
        expected_money,
    ),
    FieldContract("funding_agency_id", ("funding_agency_id",), int),
    FieldContract("funding_toptier_agency_id", ("funding_toptier_agency_id",), str),
)

FUNDING_FIELDS: tuple[FieldContract, ...] = (
    FieldContract(
        "transaction_obligated_amount", ("transaction_obligated_amount",), expected_money
    ),
    FieldContract("gross_outlay_amount", ("gross_outlay_amount",), expected_money),
    FieldContract("funding_agency_id", ("funding_agency_id",), int),
    FieldContract("funding_toptier_agency_id", ("funding_toptier_agency_id",), str),
    FieldContract("awarding_agency_id", ("awarding_agency_id",), int),
    FieldContract("awarding_toptier_agency_id", ("awarding_toptier_agency_id",), str),
    FieldContract("reporting_fiscal_year", ("reporting_fiscal_year",), int),
    FieldContract("reporting_fiscal_quarter", ("reporting_fiscal_quarter",), int),
    FieldContract("reporting_fiscal_month", ("reporting_fiscal_month",), int),
)

SUBAWARD_FIELDS: tuple[FieldContract, ...] = (
    FieldContract("id", ("internal_id",), str),
    FieldContract("sub_award_id", ("Sub-Award ID",), str),
    FieldContract("sub_award_date", ("Sub-Award Date",), expected_date),
    FieldContract("sub_award_amount", ("Sub-Award Amount",), expected_money),
)

SPENDING_FIELDS: tuple[FieldContract, ...] = (
    FieldContract("code", ("code",), str),
    FieldContract("amount", ("amount",), expected_money),
    FieldContract("total_outlays", ("total_outlays",), expected_money),
    FieldContract("spending_level", ("spending_level",), str),
)


def raw_value(raw: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first value among ``keys`` that is not None.

    Mirrors :meth:`BaseModel.get_value`, which skips a key present with a null
    value and moves on to the next spelling.

    Args:
        raw: The response payload to read.
        keys: Keys to try, in order.

    Returns:
        Any: The first non-None value, or None when no key carries one.
    """
    for key in keys:
        value = raw.get(key)
        if value is not None:
            return value
    return None


def _fields_for(obj: object, fields: tuple[FieldContract, ...]) -> list[FieldContract]:
    """Select the entry describing each property the object actually has.

    Where two entries name the same property, the one whose ``owner`` is the most
    derived class of the object wins, so ``Loan`` gets its own chain and ``Grant``
    keeps the inherited one.

    Args:
        obj: The model being checked.
        fields: The table to select from.

    Returns:
        list[FieldContract]: One entry per applicable property, in table order.
    """
    chosen: dict[str, FieldContract] = {}

    for field in fields:
        if not hasattr(type(obj), field.prop):
            continue
        if field.owner is not None and not isinstance(obj, field.owner):
            continue

        current = chosen.get(field.prop)
        if current is None or (
            field.owner is not None
            and (current.owner is None or issubclass(field.owner, current.owner))
        ):
            chosen[field.prop] = field

    return list(chosen.values())


def compare_fields(
    name: str,
    obj: object,
    fields: tuple[FieldContract, ...],
    keys_present_only: bool = False,
) -> set[str]:
    """Assert every contracted property matches the payload the model holds.

    Args:
        name: Label used in the failure message.
        obj: The model to read. Its ``raw`` is both sides of the comparison.
        fields: The table describing the properties to check.
        keys_present_only: Skip entries no key of which the payload carries. Set
            for a search result, where reading such a property would send the
            model to the network for a detail response and the comparison would
            then be against a merged payload rather than against one response.

    Returns:
        set[str]: The properties whose expected value was not None, i.e. those a
        real figure was compared for. A property the payload leaves empty is
        checked (it must answer its default) but is not reported here, so a
        caller can tell a real comparison from a run of None-equals-None.

    Raises:
        AssertionError: If any property disagrees with its payload, or if a raw
            value could not be coerced at all.
    """
    raw = obj.raw
    pinned: set[str] = set()
    mismatches: dict[str, Any] = {}

    for field in _fields_for(obj, fields):
        if keys_present_only and not any(key in raw for key in field.keys):
            continue

        value = raw_value(raw, field.keys)
        if value is None:
            expected: Any = field.default
        else:
            try:
                expected = field.coerce(value)
            except Exception as exc:
                # Reported rather than raised: an unparseable raw value is a
                # finding about this property, and erroring here would lose every
                # other property's result and break the promise that this
                # function fails only on a mapping defect.
                mismatches[field.prop] = {
                    "keys": field.keys,
                    "raw": value,
                    "uncoercible": f"{type(exc).__name__}: {exc}",
                }
                continue
            pinned.add(field.prop)

        actual = getattr(obj, field.prop)
        if actual != expected:
            mismatches[field.prop] = {
                "keys": field.keys,
                "expected": expected,
                "actual": actual,
            }

    assert mismatches == {}, (
        f"{name}: {len(mismatches)} contracted propert(ies) disagree with the "
        f"response they were built from. Both sides come from one payload, so "
        f"this is a mapping defect and not live data drift. {mismatches}"
    )
    return pinned
