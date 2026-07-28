from __future__ import annotations

from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar

from ..logging_config import USASpendingLogger
from ..utils.numbers import to_decimal
from ..utils.textcase import titlecase_name
from ..utils.validations import normalize_recipient_id
from .lazy_record import LazyRecord
from .location import Location

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

    An award search result reports its recipient as flat, title-cased keys rather
    than as the nested object a detail response sends. Both spellings are read
    here, so an award holding a search result can hand its payload over via
    :meth:`_from_search_result` rather than translating the keys itself.
    """

    #: The flat keys an award search result carries for its recipient. Every one is
    #: read by a property below, and this is the projection
    #: :meth:`_from_search_result` copies.
    _SEARCH_KEYS: ClassVar[tuple[str, ...]] = (
        "recipient_id",
        "Recipient Name",
        "Recipient DUNS Number",
        "Recipient UEI",
        "Recipient Location",
    )

    @classmethod
    def _from_search_result(cls, data: dict[str, Any], client: USASpendingClient) -> Recipient:
        """Build from an award search result, taking only the keys this model owns.

        Copies rather than aliasing, since this is a lazy record whose ``raw`` is
        replaced in place when a detail fetch fires.

        Args:
            data: An award search result, whose other keys are ignored.
            client: The client the new model should hold.

        Returns:
            Recipient: A model whose ``raw`` holds only recipient data.
        """
        return cls({key: data[key] for key in cls._SEARCH_KEYS if key in data}, client)

    def __init__(
        self,
        data_or_id: dict[str, Any] | str,
        client: USASpendingClient,
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
            raw["recipient_id"] = normalize_recipient_id(rid)

        super().__init__(raw, client)

    def _fetch_details(self) -> dict[str, Any] | None:
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

    @property
    def recipient_id(self) -> str | None:
        """Recipient identifier (hash plus level suffix).

        A raw ID reporting several levels, as ``"<hash>-['C', 'R']"``, is reduced
        to one on construction. See :attr:`recipient_level` for which one, and
        :func:`~usaspending.utils.validations.normalize_recipient_id` for why.

        Returns:
            Optional[str]: The recipient ID/hash, or None.
        """
        return self.get_value(["recipient_id", "recipient_hash"], default=None)

    @property
    def recipient_level(self) -> str | None:
        """Which level of the recipient hierarchy this record describes.

        ``"C"`` for a child, ``"P"`` for a parent, ``"R"`` for a recipient with
        no parent. The same entity can exist at several levels, each a separate
        record with its own totals, so this says which one is in hand. Reported
        by the API rather than parsed from :attr:`recipient_id`.

        Returns:
            Optional[str]: The recipient level, or None when not reported.
        """
        return self._lazy_get("recipient_level")

    @property
    def name(self) -> str | None:
        """Recipient name.

        Returns:
            Optional[str]: The recipient name in title case, or None.
        """
        return titlecase_name(
            self._lazy_get("name", "recipient_name", "Recipient Name", default=None)
        )

    @property
    def alternate_names(self) -> list[str | None]:
        """List of alternate names for the recipient.

        Returns:
            List[Optional[str]]: List of alternate names in title case, or empty list.
        """
        names = self._lazy_get("alternate_names", default=[])
        if isinstance(names, list):
            return [titlecase_name(name) for name in names if isinstance(name, str)]
        else:
            return []

    @property
    def duns(self) -> str | None:
        """DUNS number.

        Returns:
            Optional[str]: The DUNS number, or None.
        """
        return self._lazy_get("duns", "recipient_unique_id", "Recipient DUNS Number", default=None)

    @property
    def uei(self) -> str | None:
        """Unique Entity Identifier (UEI).

        Returns:
            Optional[str]: The UEI, or None.
        """
        return self._lazy_get("uei", "recipient_uei", "Recipient UEI")

    @cached_property
    def parent(self) -> Recipient | None:
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

    @property
    def parents(self) -> list[Recipient]:
        """List of parent recipients.

        Each read returns a new list over the same cached models, so a caller that
        sorts or pops it cannot disturb the next reader. Copying costs far less
        than rebuilding the models, which is why the cache sits behind this rather
        than on it.

        Returns:
            List[Recipient]: List of parent Recipient objects.
        """
        return list(self._parents)

    @cached_property
    def _parents(self) -> list[Recipient]:
        """Build the parent models once."""
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
    def business_types(self) -> list[str]:
        """Business types/categories.

        Returns:
            List[str]: List of business type strings.
        """
        return self._lazy_get("business_types", "business_categories", default=[])

    @property
    def business_categories(self) -> list[str]:
        """Alias for business_types.

        Returns:
            List[str]: List of business category strings.
        """
        return self.business_types

    @cached_property
    def location(self) -> Location | None:
        """Recipient location.

        Returns:
            Optional[Location]: The Location object, or None.
        """
        data = self._lazy_get("location", "Recipient Location")
        return Location(data) if data else None

    @property
    def total_transaction_amount(self) -> Decimal | None:
        """Total transaction amount.

        Returns:
            Optional[Decimal]: The total transaction amount, or None.
        """
        return to_decimal(self._lazy_get("total_transaction_amount"))

    @property
    def total_transactions(self) -> int | None:
        """Total number of transactions.

        Returns:
            Optional[int]: The total transaction count, or None.
        """
        return self._lazy_get("total_transactions")

    @property
    def total_face_value_loan_amount(self) -> Decimal | None:
        """Total face value of loan amount.

        Returns:
            Optional[Decimal]: The total face value loan amount, or None.
        """
        return to_decimal(self._lazy_get("total_face_value_loan_amount"))

    @property
    def total_face_value_loan_transactions(self) -> int | None:
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
