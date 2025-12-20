from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property
import re
from decimal import Decimal

from .lazy_record import LazyRecord
from .location import Location
from ..utils.formatter import to_decimal, contracts_titlecase

from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)

if TYPE_CHECKING:
    from ..client import USASpendingClient

# FUTURE: Add logic to self-categorize recipient type based on FPDS categories
# This would enhance the Recipient model by automatically determining the recipient
# type (corporation, university, government, etc.) based on FPDS category codes


class Recipient(LazyRecord):
    """Represents an award recipient.

    This class provides access to recipient details, including name, IDs,
    location, and business categories.
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

    def __init__(
        self,
        data_or_id: Dict[str, Any] | str,
        client: Optional[USASpendingClient] = None,
    ):
        """Initialize Recipient.

        Args:
            data_or_id: Dictionary containing recipient data or recipient ID string.
            client: USASpendingClient instance.
        """
        # Use the base validation method
        raw = self.validate_init_data(
            data_or_id, "Recipient", id_field="recipient_id", allow_string_id=True
        )

        # Apply recipient-specific ID cleaning
        rid = raw.get("recipient_id") or raw.get("recipient_hash")
        if rid:
            raw["recipient_id"] = self._clean_recipient_id(rid)

        super().__init__(raw, client)

    def _fetch_details(self) -> Optional[Dict[str, Any]]:
        """Fetch full recipient details from the API.

        Returns:
            Optional[Dict[str, Any]]: The recipient details dictionary, or None.
        """
        recipient_id = self.recipient_id
        if not recipient_id:
            logger.error(
                "Cannot lazy-load Recipient data. Property `recipient_id` is required to fetch details."
            )
            return None
        try:
            # Make direct API call to avoid circular dependency
            endpoint = f"/recipient/{recipient_id}/"
            response = self._client._make_request("GET", endpoint)
            return response
        except Exception as e:
            # If fetch fails, return None to avoid breaking the application
            logger.error(f"Failed to fetch recipient details for {recipient_id}: {e}")
            return None

    @staticmethod
    def _clean_recipient_id(rid: str) -> str:
        """Normalise list-annotated recipient IDs.

        Sometimes these look like "abc123-['C','R']". This will select the
        first letter after the dash.

        Args:
            rid: The raw recipient ID string.

        Returns:
            str: The normalized recipient ID.
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
            tok.strip().strip("'\"").upper() for tok in body.split(",") if tok.strip()
        ]

        letter = tokens[0]
        return f"{base}-{letter}" if letter else base

    @property
    def recipient_id(self) -> Optional[str]:
        """Recipient identifier (hash).

        Returns:
            Optional[str]: The recipient ID/hash, or None.
        """
        return self.get_value(["recipient_id", "recipient_hash"], default=None)

    @property
    def name(self) -> Optional[str]:
        """Recipient name.

        Returns:
            Optional[str]: The recipient name in title case, or None.
        """
        return contracts_titlecase(
            self._lazy_get("name", "recipient_name", "Recipient Name", default=None)
        )

    @property
    def alternate_names(self) -> List[Optional[str]]:
        """List of alternate names for the recipient.

        Returns:
            List[Optional[str]]: List of alternate names in title case, or empty list.
        """
        names = self._lazy_get("alternate_names", default=[])
        if isinstance(names, list):
            return [
                contracts_titlecase(name) for name in names if isinstance(name, str)
            ]
        else:
            return []

    @property
    def duns(self) -> Optional[str]:
        """DUNS number.

        Returns:
            Optional[str]: The DUNS number, or None.
        """
        return self._lazy_get(
            "duns", "recipient_unique_id", "Recipient DUNS Number", default=None
        )

    @property
    def uei(self) -> Optional[str]:
        """Unique Entity Identifier (UEI).

        Returns:
            Optional[str]: The UEI, or None.
        """
        return self._lazy_get("uei", "recipient_uei")

    @cached_property
    def parent(self) -> Optional["Recipient"]:
        """Parent recipient.

        Returns:
            Optional[Recipient]: The parent Recipient object, or None.
        """
        pid = self._lazy_get("parent_id")

        # Don't load a parent if parent id is missing or
        # the parent recipient_id is the same as the current one
        if not pid or pid == self.recipient_id:
            return None
        else:
            return Recipient(
                {
                    "recipient_id": pid,
                    "name": self.get_value("parent_name"),
                    "duns": self.get_value("parent_duns"),
                    "uei": self.get_value("parent_uei"),
                },
                client=self._client,
            )

    @cached_property
    def parents(self) -> List["Recipient"]:
        """List of parent recipients.

        Returns:
            List[Recipient]: List of parent Recipient objects.
        """
        plist = []
        # Use _lazy_get to ensure parents data is loaded if not present
        parents_data = self._lazy_get("parents", default=[])

        for p in parents_data:
            if isinstance(p, dict):
                # Skip if parent_id is missing or the same as current recipient_id
                if not p.get("parent_id") or p.get("parent_id") == self.recipient_id:
                    continue
                plist.append(
                    Recipient(
                        {
                            "recipient_id": p.get("parent_id"),
                            "name": p.get("parent_name"),
                            "duns": p.get("parent_duns"),
                            "uei": p.get("parent_uei"),
                        },
                        client=self._client,
                    )
                )
        return plist

    @property
    def business_types(self) -> List[str]:
        """Business types/categories.

        Returns:
            List[str]: List of business type strings.
        """
        return self._lazy_get("business_types", "business_categories", default=[])

    @property
    def business_categories(self) -> List[str]:
        """Alias for business_types.

        Returns:
            List[str]: List of business category strings.
        """
        return self.business_types

    @cached_property
    def location(self) -> Optional[Location]:
        """Recipient location.

        Returns:
            Optional[Location]: The Location object, or None.
        """
        data = self._lazy_get("location")
        return Location(data, self._client) if data else None

    @property
    def total_transaction_amount(self) -> Optional[Decimal]:
        """Total transaction amount.

        Returns:
            Optional[Decimal]: The total transaction amount, or None.
        """
        return to_decimal(self._lazy_get("total_transaction_amount"))

    @property
    def total_transactions(self) -> Optional[int]:
        """Total number of transactions.

        Returns:
            Optional[int]: The total transaction count, or None.
        """
        return self._lazy_get("total_transactions")

    @property
    def total_face_value_loan_amount(self) -> Optional[Decimal]:
        """Total face value of loan amount.

        Returns:
            Optional[Decimal]: The total face value loan amount, or None.
        """
        return to_decimal(self._lazy_get("total_face_value_loan_amount"))

    @property
    def total_face_value_loan_transactions(self) -> Optional[int]:
        """Total number of loan transactions.

        Returns:
            Optional[int]: The total loan transaction count, or None.
        """
        return self._lazy_get("total_face_value_loan_transactions")

    def __repr__(self) -> str:
        """String representation of Recipient.

        Returns:
            str: String containing recipient name and ID.
        """
        return f"<Recipient {self.name or '?'} ({self.recipient_id})>"
