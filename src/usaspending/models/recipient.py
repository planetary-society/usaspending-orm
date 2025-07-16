from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property
import re

from .common import *
from .lazy_record import LazyRecord
from .location import Location
from ..utils.formatter import to_float, contracts_titlecase

if TYPE_CHECKING:
    from ..client import USASpending

# TODO: Add logic to self-categorize recipient type based on FPDS categories

# ──────────────────────────────────────────────────
#  Recipient wrapper
# ──────────────────────────────────────────────────
class Recipient(LazyRecord):
    """
    Wrapper around USAspending recipient data.

    Construction
    ------------
    • Recipient(recipient_overview_dict_or_search_row)
    • Recipient(recipient_id_str)
    """

    # compiled once at import time
    _LIST_SUFFIX_RE = re.compile(
        r"""
        ^(?P<base>.+?)          # everything before the dash (non-greedy)
        -\[\s*(?P<body>[^\]]+)\]  #  -[  ... ]
        $                       # end of string
        """,
        re.VERBOSE,
    )

    # ─────────────────────────────────────────────
    #  Construction
    # ─────────────────────────────────────────────
    def __init__(self, data_or_id: Dict[str, Any] | str, client: Optional[USASpending] = None):
        if isinstance(data_or_id, dict):
            raw = data_or_id.copy()
            if rid := raw.get("recipient_id"):
                raw["recipient_id"] = self._clean_recipient_id(rid)
        elif isinstance(data_or_id, str):
            raw = {"recipient_id": self._clean_recipient_id(data_or_id)}
        else:
            raise TypeError("Recipient expects dict or recipient_id string")
        super().__init__(raw, client)
        
    # ---------------------- fetch hook -------------------------------- #
    def _fetch_details(self, client: 'USASpending') -> Optional[Dict[str, Any]]:
        rid = self.recipient_id
        return client._raw_client.get_recipient(rid) if rid else None

    # ─────────────────────────────────────────────
    #  Static cleaning utility
    # ─────────────────────────────────────────────
    
    @staticmethod
    def _clean_recipient_id(rid: str) -> str:
        """
        Normalise funky list-annotated recipient IDs.
        """
        if not isinstance(rid, str):
            return rid  # defensive; shouldn't happen

        rid = rid.strip().rstrip("/")  # drop accidental trailing slash

        m = Recipient._LIST_SUFFIX_RE.match(rid)
        if not m:
            return rid  # already in normal form

        base = m.group("base")
        body = m.group("body")

        # turn  "'C','R'"  or  "'R'"  etc.  into a list of clean tokens
        tokens = [
            tok.strip().strip("'\"").upper()
            for tok in body.split(",")
            if tok.strip()
        ]

        letter = "R" if "R" in tokens else tokens[0]
        return f"{base}-{letter}" if letter else base

    # ─────────────────────────────────────────────
    #  Core scalar props
    # ─────────────────────────────────────────────
    @property
    def recipient_id(self) -> Optional[str]:
        return self.get_value(["recipient_id", "recipient_hash"], default=None)

    @property
    def name(self) -> Optional[str]:
        return contracts_titlecase(self.get_value(["name", "recipient_name", "Recipient Name"]))

    @property
    def duns(self) -> Optional[str]:
        return self.get_value(["duns", "recipient_unique_id", "Recipient DUNS Number"])

    @property
    def uei(self) -> Optional[str]:
        return self.get_value(["uei", "recipient_uei"])

    # ─────────────────────────────────────────────
    #  Parent relationships
    # ─────────────────────────────────────────────
    @cached_property
    def parent(self) -> Optional["Recipient"]:
        pid = self.get_value("parent_id")
        if not pid:
            return None
        return Recipient(
            {
                "recipient_id": pid,
                "name": self.get_value("parent_name"),
                "duns": self.get_value("parent_duns"),
                "uei": self.get_value("parent_uei"),
            },
            client=self._client
        )

    @cached_property
    def parents(self) -> List["Recipient"]:
        plist = []
        for p in self.get_value("parents", default=[]):
            if isinstance(p, dict):
                plist.append(
                    Recipient(
                        {
                            "recipient_id": p.get("parent_id"),
                            "name": p.get("parent_name"),
                            "duns": p.get("parent_duns"),
                            "uei": p.get("parent_uei"),
                        },
                        client=self._client
                    )
                )
        return plist

    # ─────────────────────────────────────────────
    #  Business & totals 
    # ─────────────────────────────────────────────
    @property
    def business_types(self) -> List[str]:
        return self.get_value("business_types", "business_categories", default=[])

    @cached_property
    def location(self) -> Optional[Location]:
        """Get recipient location - shares same client."""
        return self._get_or_create_related('location', Location)


    @property
    def total_transaction_amount(self):          return to_float(self.get_value("total_transaction_amount"))
    @property
    def total_transactions(self):                return self.get_value("total_transactions")
    @property
    def total_face_value_loan_amount(self):      return to_float(self.get_value("total_face_value_loan_amount"))
    @property
    def total_face_value_loan_transactions(self):return self.get_value("total_face_value_loan_transactions")

    def __repr__(self) -> str:                    return f"<Recipient {self.name or '?'} ({self.recipient_id})>"