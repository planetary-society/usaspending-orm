from .base_model import BaseModel
from dataclasses import dataclass
from datetime import date
from typing import Dict, Any, Optional
from decimal import Decimal
from ..utils.formatter import to_decimal, smart_sentence_case, to_date


@dataclass
class Transaction(BaseModel):
    """Represents a single transaction record for an award."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize Transaction.

        Args:
            data: Dictionary containing transaction data.
        """
        super().__init__(data)

    @property
    def amt(self) -> Optional[Decimal]:
        """Get the transaction amount.

        Calculated based on available obligation or loan fields.

        Returns:
            Optional[Decimal]: The transaction amount, or None.
        """
        amt = (
            self.federal_action_obligation
            or self.face_value_loan_guarantee
            or self.original_loan_subsidy_cost
            or None
        )

        return to_decimal(amt)

    @property
    def id(self) -> Optional[str]:
        """Transaction identifier.

        Returns:
            Optional[str]: The internal transaction ID, or None.
        """
        return self.raw.get("id")

    @property
    def type(self) -> Optional[str]:
        """Transaction type code.

        Returns:
            Optional[str]: The transaction type code, or None.
        """
        return self.raw.get("type")

    @property
    def type_description(self) -> Optional[str]:
        """Description of the transaction type.

        Returns:
            Optional[str]: The transaction type description, or None.
        """
        return self.raw.get("type_description")

    @property
    def action_date(self) -> Optional[date]:
        """Date the transaction action occurred.

        Returns:
            Optional[date]: The action date, or None.
        """
        return to_date(self.raw.get("action_date"))

    @property
    def action_type(self) -> Optional[str]:
        """Action type code.

        Returns:
            Optional[str]: The action type code, or None.
        """
        return self.raw.get("action_type")

    @property
    def action_type_description(self) -> Optional[str]:
        """Description of the action type.

        Returns:
            Optional[str]: The action type description, or None.
        """
        return self.raw.get("action_type_description")

    @property
    def modification_number(self) -> Optional[str]:
        """Modification number for the transaction.

        Returns:
            Optional[str]: The modification number, or None.
        """
        return self.raw.get("modification_number")

    @property
    def award_description(self) -> Optional[str]:
        """Description of the award associated with this transaction.

        Returns:
            Optional[str]: The award description in sentence case, or empty string.
        """
        return smart_sentence_case(self.raw.get("description", ""))

    @property
    def federal_action_obligation(self) -> Optional[Decimal]:
        """Federal action obligation amount.

        Returns:
            Optional[Decimal]: The federal action obligation, or None.
        """
        return to_decimal(self.raw.get("federal_action_obligation"))

    @property
    def face_value_loan_guarantee(self) -> Optional[Decimal]:
        """Face value of loan guarantee.

        Returns:
            Optional[Decimal]: The face value loan guarantee amount, or None.
        """
        return to_decimal(self.raw.get("face_value_loan_guarantee"))

    @property
    def original_loan_subsidy_cost(self) -> Optional[Decimal]:
        """Original loan subsidy cost.

        Returns:
            Optional[Decimal]: The original loan subsidy cost, or None.
        """
        return to_decimal(self.raw.get("original_loan_subsidy_cost"))

    @property
    def cfda_number(self) -> Optional[str]:
        """Catalog of Federal Domestic Assistance (CFDA) number.

        Returns:
            Optional[str]: The CFDA number, or None.
        """
        return self.raw.get("cfda_number")

    def __repr__(self) -> str:
        """String representation of Transaction.

        Returns:
            str: String containing ID, action date, and amount.
        """
        return f"<Txn {self.id or '?'} {str(self.action_date) or '?'} {self.amt}>"
