from .base_model import BaseModel
from dataclasses import dataclass
from typing import Dict, Any, Optional
from ..utils.formatter import to_float, smart_sentence_case, to_date


@dataclass
class Transaction(BaseModel):
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @property
    def amt(self) -> Optional[float]:
        """Get the transaction amount."""
        amt = self.federal_action_obligation or \
                self.face_value_loan_guarantee or \
                self.original_loan_subsidy_cost or None

        return to_float(amt)

    @property
    def id(self) -> Optional[str]:
        return self.raw.get("id")

    @property
    def type(self) -> Optional[str]:
        return self.raw.get("type")

    @property
    def type_description(self) -> Optional[str]:
        return self.raw.get("type_description")

    @property
    def action_date(self) -> Optional[str]:
        return to_date(self.raw.get("action_date"))

    @property
    def action_type(self) -> Optional[str]:
        return self.raw.get("action_type")

    @property
    def action_type_description(self) -> Optional[str]:
        return self.raw.get("action_type_description")

    @property
    def modification_number(self) -> Optional[str]:
        return self.raw.get("modification_number")

    @property
    def award_description(self) -> Optional[str]:
        return smart_sentence_case(self.raw.get("description",""))

    @property
    def federal_action_obligation(self) -> Optional[float]:
        return to_float(self.raw.get("federal_action_obligation"))

    @property
    def face_value_loan_guarantee(self) -> Optional[float]:
        return to_float(self.raw.get("face_value_loan_guarantee"))

    @property
    def original_loan_subsidy_cost(self) -> Optional[float]:
        return to_float(self.raw.get("original_loan_subsidy_cost"))

    @property
    def cfda_number(self) -> Optional[str]:
        return self.raw.get("cfda_number")

    def __repr__(self) -> str:
        return f"<Txn {self.id or '?'} {str(self.action_date) or '?'} {self.amt}>"
