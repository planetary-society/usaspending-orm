from .common import *
from ..utils.formatter import to_float

@dataclass
class Transaction:
    _raw: Dict[str, Any] = field(repr=False, default_factory=dict)

    @property  # fmt: off
    def id(self)                       -> Optional[str]:  return self._raw.get("id")
    def type(self)                     -> Optional[str]:  return self._raw.get("type")
    def type_description(self)         -> Optional[str]:  return self._raw.get("type_description")
    def action_date(self)              -> Optional[str]:  return self._raw.get("action_date")
    def action_type(self)              -> Optional[str]:  return self._raw.get("action_type")
    def action_type_description(self)  -> Optional[str]:  return self._raw.get("action_type_description")
    def modification_number(self)      -> Optional[str]:  return self._raw.get("modification_number")
    def description(self)              -> Optional[str]:  return self._raw.get("description")

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
    def cfda_number(self) -> Optional[str]:    return self._raw.get("cfda_number")

    def get(self, key: str, default: Any = None) -> Any:  return self._raw.get(key, default)
    @property
    def raw(self):                             return self._raw

    def to_dict(self) -> dict:
        return self._raw

    def __repr__(self) -> str:
        amt = (self.federal_action_obligation or
               self.face_value_loan_guarantee or
               self.original_loan_subsidy_cost or "?")
        return f"<Txn {self.modification_number or 'Base'} {self.action_date or '?'} {amt}>"
