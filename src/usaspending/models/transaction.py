"""Transaction model for USASpending data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..utils.formatter import smart_sentence_case, to_date, to_decimal
from .base_model import BaseModel


class Transaction(BaseModel):
    """Represents a single transaction record for an award."""

    @property
    def amt(self) -> Decimal | None:
        """Get the transaction amount.

        Calculated based on available obligation or loan fields.

        Returns:
            Optional[Decimal]: The transaction amount, or None.
        """
        # Each operand is already coerced by its own getter. The trailing
        # `or None` normalizes a zero amount away, since Decimal("0.00") is
        # falsy.
        return (
            self.federal_action_obligation
            or self.face_value_loan_guarantee
            or self.original_loan_subsidy_cost
            or None
        )

    @property
    def id(self) -> str | None:
        """Transaction identifier.

        Returns:
            Optional[str]: The internal transaction ID, or None.
        """
        return self.get_value("id")

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

        Returns:
            Optional[str]: The transaction type description, or None.
        """
        return self.get_value("type_description")

    @property
    def action_date(self) -> date | None:
        """Date the transaction action occurred.

        Returns:
            Optional[date]: The action date, or None.
        """
        return to_date(self.get_value("action_date"))

    @property
    def action_type(self) -> str | None:
        """Action type code.

        Returns:
            Optional[str]: The action type code, or None.
        """
        return self.get_value("action_type")

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
        return self.get_value("modification_number")

    @property
    def award_description(self) -> str:
        """Description of the award associated with this transaction.

        Returns:
            str: The award description in sentence case, or an empty string.
        """
        return smart_sentence_case(self.get_value("description"))

    @property
    def federal_action_obligation(self) -> Decimal | None:
        """Federal action obligation amount.

        Returns:
            Optional[Decimal]: The federal action obligation, or None.
        """
        return to_decimal(self.get_value("federal_action_obligation"))

    @property
    def face_value_loan_guarantee(self) -> Decimal | None:
        """Face value of loan guarantee.

        Returns:
            Optional[Decimal]: The face value loan guarantee amount, or None.
        """
        return to_decimal(self.get_value("face_value_loan_guarantee"))

    @property
    def original_loan_subsidy_cost(self) -> Decimal | None:
        """Original loan subsidy cost.

        Returns:
            Optional[Decimal]: The original loan subsidy cost, or None.
        """
        return to_decimal(self.get_value("original_loan_subsidy_cost"))

    @property
    def cfda_number(self) -> str | None:
        """Catalog of Federal Domestic Assistance (CFDA) number.

        Returns:
            Optional[str]: The CFDA number, or None.
        """
        return self.get_value("cfda_number")

    def __repr__(self) -> str:
        """String representation of Transaction.

        Returns:
            str: String containing ID, action date, and amount.
        """
        return f"<Txn {self.id or '?'} {str(self.action_date) or '?'} {self.amt}>"
