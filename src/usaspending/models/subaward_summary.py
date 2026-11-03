"""Stored subaward totals for one prime award."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from ..utils.numbers import to_decimal, to_int
from .base_model import BaseModel


class SubAwardSummary(BaseModel):
    """Prime-award summary returned by the grouped subaward endpoint.

    Totals describe the whole award, not just subawards within the query's date
    range. The API reports zero for absent amounts; identifiers may be null.
    Loan ``award_obligation`` is subsidy cost. The server returns a zero ratio
    for a zero or missing denominator; other ratios can exceed one.
    """

    @property
    def award_id(self) -> str | None:
        """Return the prime award's display identifier, when present."""
        return self.get_value("award_id")

    @property
    def award_generated_internal_id(self) -> str | None:
        """Return the prime award's generated unique identifier."""
        return self.get_value("award_generated_internal_id")

    @property
    def subaward_count(self) -> int | None:
        """Return the number of subawards recorded for this prime award."""
        return to_int(self.get_value("subaward_count"))

    @property
    def subaward_obligation(self) -> Decimal | None:
        """Return the stored total subaward obligation in dollars."""
        return to_decimal(self.get_value("subaward_obligation"))

    @property
    def award_obligation(self) -> Decimal | None:
        """Return the prime award amount used as the ratio denominator."""
        return to_decimal(self.get_value("award_obligation"))

    @property
    def subaward_to_award_ratio(self) -> Decimal | None:
        """Return the server's ratio without money rounding or recalculation."""
        value = self.get_value("subaward_to_award_ratio")
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, InvalidOperation):
            return None
