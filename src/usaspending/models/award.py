
"""Award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property

from .common import *
from .lazy_record import LazyRecord
from .recipient import Recipient
from .location import Location
from .transaction import Transaction
from .period_of_performance import PeriodOfPerformance

from ..config import AWARD_TYPE_DESCRIPTIONS


from ..helpers import smart_sentence_case, to_float

if TYPE_CHECKING:
    from ..client import USASpending

class Award(LazyRecord):
    """Rich wrapper around a USAspending award record."""

    def __init__(self, data_or_id: Dict[str, Any] | str, client: Optional[USASpending] = None):
        """Initialize Award instance.
        
        Args:
            data_or_id: Award data dictionary or unique award ID string
            client: Optional USASpending client instance
        """
        if isinstance(data_or_id, dict):
            raw: Dict[str, Any] = data_or_id.copy()
        elif isinstance(data_or_id, str):
            raw = {"generated_unique_award_id": data_or_id}
        else:
            raise TypeError("Award expects a dict or an award_id string")
        super().__init__(raw, client)

    def _fetch_details(self, client: 'USASpending') -> Optional[Dict[str, Any]]:
        """Fetch full award details."""
        award_id = self.get_value(['generated_unique_award_id'])
        if not award_id:
            return None
        return client._raw_client.get_award(award_id)

    # Core scalar properties
    @property
    def prime_award_id(self) -> str:
        """Primary award identifier (PIID, FAIN, URI, etc.)."""
        return str(self.get_value(["Award ID", "piid", "fain", "uri"], default=""))

    @property
    def generated_unique_award_id(self) -> Optional[str]:
        """USASpending-generated unique award identifier."""
        return self.get_value(["generated_unique_award_id", "generated_internal_id"])

    @property
    def description(self) -> str:
        """Award description with smart sentence casing."""
        return smart_sentence_case(self.get_value(["description", "Description"], default=""))

    # Financial properties
    @property
    def total_obligations(self) -> float:
        """Total obligated amount for this award."""
        return to_float(self.get_value(["total_obligation", "Award Amount"])) or 0.0

    @property
    def total_outlay(self) -> float:
        """Total amount paid out for this award."""
        return to_float(self.get_value(["total_account_outlay", "Total Outlays"])) or 0.0

    @property
    def potential_value(self) -> float:
        """Potential total value of the award."""
        return to_float(
            self.get_value(["Award Amount", "Loan Amount"], default=self.total_obligations)
        ) or 0.0

    @property
    def award_amount(self) -> float:
        """Base award amount."""
        return to_float(self.get_value(["Award Amount", "Loan Amount"])) or 0.0

    @cached_property
    def period_of_performance(self) -> Optional[PeriodOfPerformance]:
        """Award period of performance dates."""
        if isinstance(self.get_value(["period_of_performance"]), dict):
            return PeriodOfPerformance(self._data["period_of_performance"])

        date_keys = ["Start Date", "End Date", "Period of Performance Start Date"]
        if any(self.get_value([k]) for k in date_keys):
            return PeriodOfPerformance({
                "start_date": self.get_value([
                    "Start Date", "Period of Performance Start Date"
                ]),
                "end_date": self.get_value([
                    "End Date", "Period of Performance Current End Date"
                ]),
                "last_modified_date": self.get_value(["Last Modified Date"]),
            })
        return None

    @cached_property
    def place_of_performance(self) -> Optional[Location]:
        """Award place of performance location."""
        return self._get_or_create_related('place_of_performance', Location)

    @cached_property
    def recipient(self) -> Optional[Recipient]:
        """Award recipient with lazy loading."""
        # First check if we already have recipient data
        if isinstance(self.get_value(["recipient"]), dict):
            return self._get_or_create_related('recipient', Recipient)
        
        # Check if we have fallback fields before calling API
        recipient_keys = ["Recipient Name", "Recipient DUNS Number", "recipient_id"]
        if any(self.get_value([k]) for k in recipient_keys):
            recipient = Recipient({
                "recipient_name": self.get_value(["Recipient Name"]),
                "recipient_unique_id": self.get_value(["Recipient DUNS Number"]),
                "recipient_id": self.get_value(["recipient_id"]),
            }, client=self._client)
            
            # Add location if available to avoid separate API call
            if isinstance(self.get_value(["Recipient Location"]), dict):
                recipient_location = self._get_or_create_related(
                    "Recipient Location", Location
                )
                recipient.location = recipient_location
            
            return recipient
        
        # Only call API if we don't have enough info in the Award entry itself
        self._ensure_details()  # loads the full Award detail
        if isinstance(self.get_value(["recipient"]), dict):
            return self._get_or_create_related("recipient", Recipient)
        
        return None

    @cached_property
    def transactions(self) -> List[Transaction]:
        """Award transactions with pagination."""
        client = get_usaspending_client()
        award_id = self.get_value(
            ["generated_internal_id", "generated_unique_award_id"], 
            default=self.prime_award_id
        )
        if client is None or not award_id:
            return []

        rows: List[Dict[str, Any]] = []
        page, limit, max_pages = 1, 500, 100
        
        while page <= max_pages:
            resp = client.get_transactions(
                award_id=award_id, page=page, limit=limit
            ) or {}
            rows.extend(resp.get("results", []))
            
            meta = resp.get("page_metadata", {})
            if not meta.get("hasNext"):
                break
            page = meta.get("next", page + 1)
            
        return [Transaction(r) for r in rows]

    # Helper methods
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from award data."""
        return self.get_value([key], default=default)

    @property
    def raw(self) -> Dict[str, Any]:
        """Raw award data dictionary."""
        return self._data

    @property
    def usa_spending_url(self) -> str:
        """USASpending.gov URL for this award."""
        award_id = self.generated_unique_award_id or ''
        return f"https://www.usaspending.gov/award/{award_id}/"

    def __repr__(self) -> str:
        """String representation of Award."""
        recipient_name = self.recipient.name if self.recipient else "?"
        award_id = self.prime_award_id or self.generated_unique_award_id or '?'
        return f"<Award {award_id} → {recipient_name}>"