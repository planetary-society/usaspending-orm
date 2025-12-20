from __future__ import annotations
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import date
from functools import cached_property
from decimal import Decimal
from ..utils.formatter import (
    contracts_titlecase,
    smart_sentence_case,
    to_decimal,
    to_date,
)
from .base_model import ClientAwareModel
from .recipient import Recipient
from .location import Location
from .award import Award

if TYPE_CHECKING:
    from ..client import USASpendingClient


class SubAward(ClientAwareModel):
    """Model representing a subaward from USASpending data.

    Subawards are secondary awards issued by prime recipients of federal contracts
    or grants to other entities (subrecipients) to carry out part of the federal
    program or project. They represent the flow of federal funds from prime
    recipients to subrecipients.

    Key characteristics:
    - Issued by prime recipients, not directly by federal agencies
    - Subject to federal regulations and oversight requirements
    - Must be reported when exceeding $30,000 (per FFATA requirements)
    - Include both contract subawards (subcontracts) and grant subawards

    Subawards enable prime recipients to delegate portions of work while
    maintaining overall responsibility for the federal award's success.
    They extend the reach of federal funding through multiple tiers of
    organizations.

    Example:
        >>> # Find subawards for a specific prime award
        >>> subawards = client.subawards.search()
        ...     .for_prime_award_piid("80NSSC21C0123")
        ...     .limit(10)
        >>> for subaward in subawards:
        ...     print(f"{subaward.sub_awardee_name}: ${subaward.sub_award_amount:,.2f}")
    """

    def __init__(
        self, data: Dict[str, Any], client: Optional[USASpendingClient] = None
    ):
        """Initialize SubAward instance.

        Args:
            data: Dictionary containing subaward data.
            client: USASpendingClient instance.
        """
        super().__init__(data, client)

    # Contract Subaward fields
    CONTRACT_SUBAWARD_FIELDS = [
        "Awarding Agency",
        "Awarding Sub Agency",
        "NAICS",
        "Prime Award ID",
        "prime_award_recipient_id",
        "Prime Award Recipient UEI",
        "Prime Recipient Name",
        "PSC",
        "Sub-Award Amount",
        "Sub-Award Date",
        "Sub-Award Description",
        "Sub-Award ID",
        "Sub-Award Primary Place of Performance",
        "sub_award_recipient_id",
        "Sub-Award Type",
        "Sub-Awardee Name",
        "Sub-Recipient Location",
        "Sub-Recipient UEI",
        "prime_award_generated_internal_id",
        "prime_award_internal_id",
        "internal_id",
        "subaward_description_sorted",
    ]

    # Grant Subaward fields
    GRANT_SUBAWARD_FIELDS = [
        "Assistance Listing",
        "Awarding Agency",
        "Awarding Sub Agency",
        "Prime Award ID",
        "prime_award_recipient_id",
        "Prime Award Recipient UEI",
        "Prime Recipient Name",
        "Sub-Award Amount",
        "Sub-Award Date",
        "Sub-Award Description",
        "Sub-Award ID",
        "Sub-Award Primary Place of Performance",
        "sub_award_recipient_id",
        "Sub-Award Type",
        "Sub-Awardee Name",
        "Sub-Recipient Location",
        "Sub-Recipient UEI",
        "prime_award_generated_internal_id",
        "prime_award_internal_id",
        "internal_id",
        "subaward_description_sorted",
    ]

    @cached_property
    def place_of_performance(self) -> Optional[Location]:
        """Place of performance details for the subaward.

        Returns:
            Optional[Location]: The location object, or None.
        """
        pop_data = self.get_value("Sub-Award Primary Place of Performance")
        if pop_data:
            return Location(pop_data)
        else:
            return None

    @cached_property
    def recipient(self) -> Optional[Recipient]:
        """Sub-award recipient and location.

        Returns:
            Optional[Recipient]: The recipient object, or None.
        """
        recipient = Recipient(
            {
                "recipient_name": self.get_value(["Sub-Awardee Name"]),
                "recipient_unique_id": self.get_value(["sub_award_recipient_id"]),
                "recipient_uei": self.get_value(["Sub-Recipient UEI"]),
            },
            client=self._client,
        )

        # Add location if available to avoid separate API call
        if isinstance(self.get_value(["Sub-Recipient Location"]), dict):
            location_data = self.get_value("Sub-Recipient Location")
            recipient_location = Location(location_data) if location_data else None
            recipient.location = recipient_location

        return recipient

    @cached_property
    def parent_award(self) -> Optional[Award]:
        """Prime award associated with this subaward.

        Returns:
            Optional[Award]: The prime award object, or None.
        """
        if self.prime_award_generated_internal_id:
            return Award(
                {"generated_unique_award_id": self.prime_award_generated_internal_id},
                client=self._client,
            )
        else:
            return None

    @property
    def id(self) -> Optional[str]:
        """Internal subaward identifier.

        Returns:
            Optional[str]: The internal ID, or None.
        """
        return self.get_value("internal_id")

    @property
    def sub_award_id(self) -> Optional[str]:
        """Subaward identifier.

        Returns:
            Optional[str]: The subaward ID, or None.
        """
        return self.get_value("Sub-Award ID")

    @property
    def sub_award_type(self) -> Optional[str]:
        """Type of subaward (e.g., sub-contract, sub-grant).

        Returns:
            Optional[str]: The subaward type, or None.
        """
        return self.get_value("Sub-Award Type")

    @property
    def sub_awardee_name(self) -> Optional[str]:
        """Name of the subaward recipient.

        Returns:
            Optional[str]: The recipient name, or None.
        """
        name = self.get_value("Sub-Awardee Name")
        return contracts_titlecase(name) if name else None

    @property
    def sub_award_date(self) -> Optional[date]:
        """Date the subaward was issued.

        Returns:
            Optional[date]: The subaward date, or None.
        """
        return to_date(self.get_value("Sub-Award Date"))

    @property
    def sub_award_amount(self) -> Optional[Decimal]:
        """Amount of the subaward.

        Returns:
            Optional[Decimal]: The subaward amount, or None.
        """
        return to_decimal(self.get_value("Sub-Award Amount"))

    @property
    def awarding_agency(self) -> Optional[str]:
        """Name of the awarding agency.

        Returns:
            Optional[str]: The awarding agency name, or None.
        """
        return self.get_value("Awarding Agency")

    @property
    def awarding_sub_agency(self) -> Optional[str]:
        """Name of the awarding sub-agency.

        Returns:
            Optional[str]: The awarding sub-agency name, or None.
        """
        return self.get_value("Awarding Sub Agency")

    @property
    def prime_award_id(self) -> Optional[str]:
        """Prime award identifier (PIID/FAIN/URI).

        Returns:
            Optional[str]: The prime award ID, or None.
        """
        return self.get_value("Prime Award ID")

    @property
    def prime_recipient_name(self) -> Optional[str]:
        """Name of the prime award recipient.

        Returns:
            Optional[str]: The prime recipient name, or None.
        """
        name = self.get_value("Prime Recipient Name")
        return contracts_titlecase(name) if name else None

    @property
    def prime_award_recipient_id(self) -> Optional[str]:
        """Prime award recipient identifier.

        Returns:
            Optional[str]: The prime recipient ID, or None.
        """
        return self.get_value("prime_award_recipient_id")

    @property
    def sub_award_description(self) -> Optional[str]:
        """Description of the subaward.

        Returns:
            Optional[str]: The description, or None.
        """
        desc = self.get_value("Sub-Award Description")
        return smart_sentence_case(desc) if desc else None

    @property
    def subaward_description_sorted(self) -> Optional[str]:
        """Sorted version of the subaward description for API internal use.

        Returns:
            Optional[str]: The sorted description, or None.
        """
        return self.get_value("subaward_description_sorted")

    @property
    def sub_recipient_uei(self) -> Optional[str]:
        """Sub-recipient Unique Entity Identifier.

        Returns:
            Optional[str]: The sub-recipient UEI, or None.
        """
        return self.get_value("Sub-Recipient UEI")

    @property
    def prime_award_recipient_uei(self) -> Optional[str]:
        """Prime award recipient Unique Entity Identifier.

        Returns:
            Optional[str]: The prime recipient UEI, or None.
        """
        return self.get_value("Prime Award Recipient UEI")

    @property
    def prime_award_generated_internal_id(self) -> Optional[str]:
        """USASpending-generated unique identifier for the prime award.

        Returns:
            Optional[str]: The generated internal ID, or None.
        """
        return self.get_value("prime_award_generated_internal_id")

    @property
    def prime_award_internal_id(self) -> Optional[int]:
        """Internal database ID for the prime award.

        Returns:
            Optional[int]: The internal ID, or None.
        """
        val = self.get_value("prime_award_internal_id")
        return int(val) if val is not None else None

    @property
    def naics(self) -> Optional[str]:
        """NAICS code for contract subawards.

        Returns:
            Optional[str]: The NAICS code, or None.
        """
        return self.get_value("NAICS")

    @property
    def psc(self) -> Optional[str]:
        """Product Service Code for contract subawards.

        Returns:
            Optional[str]: The PSC, or None.
        """
        return self.get_value("PSC")

    @property
    def assistance_listing(self) -> Optional[str]:
        """Assistance listing for grant subawards.

        Returns:
            Optional[str]: The assistance listing, or None.
        """
        return self.get_value("Assistance Listing")

    def __repr__(self) -> str:
        """String representation of SubAward.

        Returns:
            str: String containing ID, name, and amount.
        """
        return f"<SubAward {self.sub_award_id or '?'} {self.sub_awardee_name or '?'} ${self.sub_award_amount or 0:,.2f}>"

    @property
    def name(self) -> Optional[str]:
        """Alias for sub_awardee_name.

        Returns:
            Optional[str]: The sub-awardee name, or None.
        """
        return self.sub_awardee_name

    @property
    def amount(self) -> Optional[float]:
        """Alias for sub_award_amount.

        Returns:
            Optional[float]: The subaward amount as a float, or None.
        """
        return self.sub_award_amount

    @property
    def description(self) -> Optional[str]:
        """Alias for sub_award_description.

        Returns:
            Optional[str]: The description, or None.
        """
        return self.sub_award_description

    @property
    def award_date(self) -> Optional[date]:
        """Alias for sub_award_date.

        Returns:
            Optional[date]: The award date, or None.
        """
        return self.sub_award_date
