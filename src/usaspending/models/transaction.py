from .common import *
from .base_model import BaseModel
from ..utils.formatter import to_float, smart_sentence_case
from datetime import datetime

@dataclass
class Transaction():
    _raw: Dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def amt(self) -> Optional[float]:
        """Get the transaction amount."""
        amt = self.federal_action_obligation or \
                self.face_value_loan_guarantee or \
                self.original_loan_subsidy_cost or None

        return to_float(amt)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def type(self) -> Optional[str]:
        return self._raw.get("type")

    @property
    def type_description(self) -> Optional[str]:
        return self._raw.get("type_description")

    @property
    def action_date(self) -> Optional[str]:
        action_date = self._raw.get("action_date")
        try:
            return datetime.strptime(action_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return action_date

    @property
    def action_type(self) -> Optional[str]:
        return self._raw.get("action_type")

    @property
    def action_type_description(self) -> Optional[str]:
        return self._raw.get("action_type_description")

    @property
    def modification_number(self) -> Optional[str]:
        return self._raw.get("modification_number")

    @property
    def award_description(self) -> Optional[str]:
        return self._raw.get("description")

    @property
    def federal_action_obligation(self) -> Optional[float]:
        return to_float(self._raw.get("federal_action_obligation"))

    @property
    def face_value_loan_guarantee(self) -> Optional[float]:
        return to_float(self._raw.get("face_value_loan_guarantee"))

    @property
    def original_loan_subsidy_cost(self) -> Optional[float]:
        return to_float(self._raw.get("original_loan_subsidy_cost"))

    @property
    def cfda_number(self) -> Optional[str]:
        return self._raw.get("cfda_number")

    def to_dict(self):
        return self._raw

    def __repr__(self) -> str:
        return f"<Txn {self.id} {str(self.action_date) or '?'} {self.amt}>"
