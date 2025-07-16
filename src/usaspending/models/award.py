
from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property

from .common import *
from .lazy_record import LazyRecord
from .recipient import Recipient
from .location import Location
from .transaction import Transaction
from .period_of_performance import PeriodOfPerformance

from ..helpers import smart_sentence_case, to_float

if TYPE_CHECKING:
    from ..client import USASpending

class Award(LazyRecord):
    """Rich wrapper around a USAspending award record."""

    # ──────────────────────────────────────────
    #  Construction
    # ──────────────────────────────────────────
    def __init__(self, data_or_id: Dict[str, Any] | str, client: Optional[USASpending] = None):
        if isinstance(data_or_id, dict):
            raw: Dict[str, Any] = data_or_id.copy()
        elif isinstance(data_or_id, str):
            raw = {"generated_unique_award_id": data_or_id}
        else:
            raise TypeError("Award expects a dict or an award_id string")
        super().__init__(raw, client)

    def _fetch_details(self, client: 'USASpending') -> Optional[Dict[str, Any]]:
        """Fetch full award details."""
        award_id = self._data.get_value('generated_unique_award_id')
        if not award_id:
            return None
        return client._raw_client.get_award(award_id)

    # ──────────────────────────────────────────
    #  Core scalars  (now via _get)
    # ──────────────────────────────────────────
    @property
    def prime_award_id(self) -> str:
        return str(self._get("Award ID", "piid", "fain", "uri", default=""))   # ★

    @property
    def generated_unique_award_id(self) -> Optional[str]:
        return self._get("generated_unique_award_id", "generated_internal_id") # ★

    @property
    def description(self) -> str:
        return smart_sentence_case(self._get("description", "Description", default=""))  # ★

    # money --------------------------------------------------------------
    @property
    def total_obligations(self) -> float:
        return to_float(self._get("total_obligation", "Award Amount")) or 0.0  # ★

    @property
    def total_outlay(self) -> float:
        return to_float(self._get("total_account_outlay", "Total Outlays")) or 0.0  # ★

    @property
    def potential_value(self) -> float:
        return to_float(
            self._get("Award Amount", "Loan Amount", default=self.total_obligations)
        ) or 0.0                                                                     # ★

    @property
    def award_amount(self) -> float:
        return to_float(
            self._get("Award Amount", "Loan Amount")
        )

    # ──────────────────────────────────────────
    #  Period of performance (unchanged logic)
    # ──────────────────────────────────────────
    @cached_property
    def period_of_performance(self) -> Optional[PeriodOfPerformance]:
        if isinstance(self.get_value("period_of_performance"), dict):
            return PeriodOfPerformance(self._raw["period_of_performance"])

        if any(
            self.get_value(k) for k in ("Start Date", "End Date", "Period of Performance Start Date")
        ):
            return PeriodOfPerformance(
                {
                    "start_date": self.get_value("Start Date")
                    or self.get_value("Period of Performance Start Date"),
                    "end_date": self.get_value("End Date")
                    or self.get_value("Period of Performance Current End Date"),
                    "last_modified_date": self.get_value("Last Modified Date"),
                }
            )
        return None

    # ──────────────────────────────────────────
    #  Place of performance
    # ──────────────────────────────────────────
    @cached_property
    def place_of_performance(self) -> Optional[Location]:
        """Get place of performance - shares same client."""
        return self._get_or_create_related('place_of_performance', Location)
        

    # ──────────────────────────────────────────
    #  Recipient
    # ──────────────────────────────────────────
    @cached_property
    def recipient(self) -> Optional[Recipient]:
        # First check if we already have recipient data
        if isinstance(self.get_value("recipient"), dict):
            return self._get_or_create_related('recipient', Recipient)
        
        # Check if we have fallback fields before calling API
        if any(self.get_value(k) for k in ("Recipient Name", "Recipient DUNS Number","recipient_id")):
            recipient = Recipient(
                {
                    "recipient_name": self.get_value("Recipient Name"),
                    "recipient_unique_id": self.get_value("Recipient DUNS Number"),
                    "recipient_id": self.get_value("recipient_id"),
                }
            )
            # If a location is provided in the Award, add that to the recipient object to avoid an API call
            if isinstance(self.get_value("Recipient Location"), dict):
                recipient_location = self._get_or_create_related(self.get_value("Recipient Location"),Location)
                recipient.location = recipient_location
            
            return recipient
        else:
            # Only call API if we don't have enough info in the Award entry itself
            self._ensure_details() # loads the full Award detail
            if isinstance(self.get_value("recipient"), dict):
                return self._get_or_create_related(self._raw["recipient"],Recipient)
        
        return None

    # ──────────────────────────────────────────
    #  Transactions
    # ──────────────────────────────────────────
    @cached_property
    def transactions(self) -> List[Transaction]:
        client = get_usaspending_client()                                                     # ★
        award_id = self._get(
            "generated_internal_id", "generated_unique_award_id", default=self.prime_award_id
        )
        if client is None or not award_id:
            return []

        rows: List[Dict[str, Any]] = []
        page, limit, max_pages = 1, 500, 100
        while page <= max_pages:
            resp = client.get_transactions(award_id=award_id, page=page, limit=limit) or {}
            rows.extend(resp.get_value("results", []))
            meta = resp.get_value("page_metadata", {})
            if not meta.get_value("hasNext"):
                break
            page = meta.get_value("next", page + 1)
        return [Transaction(r) for r in rows]

    # ──────────────────────────────────────────
    #  Misc helpers
    # ──────────────────────────────────────────
    def get(self, key: str, default: Any = None) -> Any:
        return self._get(key, default=default)                                    # ★

    @property
    def raw(self) -> Dict[str, Any]:
        return self._raw

    @property
    def usa_spending_url(self) -> str:
        return f"https://www.usaspending.gov/award/{self.generated_unique_award_id or ''}/"

    def __repr__(self) -> str:
        rname = self.recipient.name if self.recipient else "?"
        return f"<Award {self.prime_award_id or self.generated_unique_award_id or '?'} → {rname}>"