"""Loan award model for USASpending data."""

from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from ..utils.numbers import to_decimal
from .award import Award
from .grant import Grant


class Loan(Grant):
    """Loan award type.

    A loan is a form of financial assistance, so most of its fields come from
    Grant unchanged. Three properties are its own: ``total_loan_value``, which
    only loans have, plus ``total_subsidy_cost`` and ``cfda_number``, which read
    the flat keys award search returns. ``TYPE_FIELDS`` below still enumerates
    the full loan field set, inherited members included.
    """

    TYPE_FIELDS: ClassVar[list[str]] = [
        "fain",
        "uri",
        "total_subsidy_cost",
        "total_loan_value",
        "cfda_info",
        "cfda_number",
        "primary_cfda_info",
        "sai_number",
    ]

    SEARCH_FIELDS: ClassVar[list[str]] = [
        *Award.SEARCH_FIELDS,
        "Issued Date",
        "Loan Value",
        "Subsidy Cost",
        "SAI Number",
        "CFDA Number",
        "Assistance Listings",
        "primary_assistance_listing",
    ]

    @property
    def total_subsidy_cost(self) -> Decimal | None:
        """Total of the original loan subsidy cost from associated transactions.

        Prefers the flat "Subsidy Cost" key that award search returns.

        Returns:
            Optional[Decimal]: The total subsidy cost, or None.
        """
        return to_decimal(self._lazy_get("Subsidy Cost", "total_subsidy_cost", default=None))

    @property
    def total_loan_value(self) -> Decimal | None:
        """Total of the face value loan guarantee from associated transactions.

        Returns:
            Optional[Decimal]: The total loan value, or None.
        """
        return to_decimal(self._lazy_get("Loan Value", "total_loan_value", default=None))

    # Narrows Grant's resolution to the flat key only. Grant tries
    # primary_cfda_info, then cfda_info[0], then this same flat key, so it is a
    # strict superset -- this override can only find less. On a detail response,
    # which reports CFDA data nested under cfda_info and leaves the flat key
    # null, it returns None where the inherited version returns the number. The
    # response-derived contract tests preserve that mapping without snapshotting
    # a particular API value. Removing it is a behavior change, tracked
    # separately, not an oversight.
    @property
    def cfda_number(self) -> str | None:
        """Primary CFDA number for loans, read from the flat search field.

        Returns None on detail responses, which nest CFDA data under
        ``cfda_info``. Use :attr:`cfda_info` to read those.

        Returns:
            Optional[str]: The primary CFDA number, or None.
        """
        return self._lazy_get("cfda_number", "CFDA Number")
