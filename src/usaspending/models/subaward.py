from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime
from functools import cached_property
from decimal import Decimal
from ..utils.formatter import contracts_titlecase, smart_sentence_case, to_decimal, to_date
from .base_model import ClientAwareModel
from .recipient import Recipient
from .location import Location
from .award import Award
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
    def __init__(self, data: Dict[str, Any], client: Optional[USASpending] = None):
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
        "subaward_description_sorted"
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
        "subaward_description_sorted"
    ]
    
    @cached_property
    def place_of_performance(self) -> Optional[Location]:
        """Place of performance details for the subaward."""
        pop_data = self.raw.get("Sub-Award Primary Place of Performance")
        if pop_data:
            return Location(pop_data)
        else:
            return None
 
    @cached_property
    def recipient(self) -> Optional[Recipient]:
        """Sub-award recipient and location."""
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
            location_data = self._data.get("Sub-Recipient Location")
            recipient_location = (
                Location(location_data) if location_data else None
            )
            recipient.location = recipient_location

        return recipient
    
    @cached_property
    def parent_award(self) -> Optional[Award]:
        if self.prime_award_generated_internal_id:
            return Award(
                {"generated_unique_award_id": self.prime_award_generated_internal_id},
                client=self._client,
            )
        else:
            return None
    
    @property
    def id(self) -> Optional[str]:
        """Internal subaward identifier."""
        return self.raw.get("internal_id")
    
    @property
    def sub_award_id(self) -> Optional[str]:
        """Subaward identifier."""
        return self.raw.get("Sub-Award ID")
    
    @property
    def sub_award_type(self) -> Optional[str]:
        """Type of subaward (e.g., sub-contract, sub-grant)."""
        return self.raw.get("Sub-Award Type")
    
    @property
    def sub_awardee_name(self) -> Optional[str]:
        """Name of the subaward recipient."""
        name = self.raw.get("Sub-Awardee Name")
        return contracts_titlecase(name) if name else None
    
    @property
    def sub_award_date(self) -> Optional[datetime]:
        """Date the subaward was issued."""
        return to_date(self.raw.get("Sub-Award Date"))
    
    @property
    def sub_award_amount(self) -> Optional[Decimal]:
        """Amount of the subaward."""
        return to_decimal(self.raw.get("Sub-Award Amount"))
    
    @property
    def awarding_agency(self) -> Optional[str]:
        """Name of the awarding agency."""
        return self.raw.get("Awarding Agency")
    
    @property
    def awarding_sub_agency(self) -> Optional[str]:
        """Name of the awarding sub-agency."""
        return self.raw.get("Awarding Sub Agency")
    
    @property
    def prime_award_id(self) -> Optional[str]:
        """Prime award identifier (PIID/FAIN/URI)."""
        return self.raw.get("Prime Award ID")

    @property
    def prime_recipient_name(self) -> Optional[str]:
        """Name of the prime award recipient."""
        name = self.raw.get("Prime Recipient Name")
        return contracts_titlecase(name) if name else None
    
    @property
    def prime_award_recipient_id(self) -> Optional[str]:
        """Prime award recipient identifier."""
        return self.raw.get("prime_award_recipient_id")
    
    @property
    def sub_award_description(self) -> Optional[str]:
        """Description of the subaward."""
        desc = self.raw.get("Sub-Award Description")
        return smart_sentence_case(desc) if desc else None
    
    @property
    def subaward_description_sorted(self) -> Optional[str]:
        """Sorted version of the subaward description for API internal use."""
        return self.raw.get("subaward_description_sorted")
    
    @property
    def sub_recipient_uei(self) -> Optional[str]:
        """Sub-recipient Unique Entity Identifier."""
        return self.raw.get("Sub-Recipient UEI")
    
    @property
    def prime_award_recipient_uei(self) -> Optional[str]:
        """Prime award recipient Unique Entity Identifier."""
        return self.raw.get("Prime Award Recipient UEI")
    
    @property
    def prime_award_generated_internal_id(self) -> Optional[str]:
        """USASpending-generated unique identifier for the prime award."""
        return self.raw.get("prime_award_generated_internal_id")
    
    @property
    def prime_award_internal_id(self) -> Optional[int]:
        """Internal database ID for the prime award."""
        val = self.raw.get("prime_award_internal_id")
        return int(val) if val is not None else None
    
    @property
    def naics(self) -> Optional[str]:
        """NAICS code for contract subawards."""
        return self.raw.get("NAICS")
    
    @property
    def psc(self) -> Optional[str]:
        """Product Service Code for contract subawards."""
        return self.raw.get("PSC")
    
    @property
    def assistance_listing(self) -> Optional[str]:
        """Assistance listing for grant subawards."""
        return self.raw.get("Assistance Listing")
    
    def __repr__(self) -> str:
        """String representation of SubAward."""
        return f"<SubAward {self.sub_award_id or '?'} {self.sub_awardee_name or '?'} ${self.sub_award_amount or 0:,.2f}>"
        
    @property
    def name(self) -> Optional[str]:
        """Alias for sub_awardee_name."""
        return self.sub_awardee_name

    @property
    def amount(self) -> Optional[float]:
        """Alias for sub_award_amount."""
        return self.sub_award_amount

    @property
    def description(self) -> Optional[str]:
        """Alias for sub_award_description."""
        return self.sub_award_description

    @property
    def award_date(self) -> Optional[datetime]:
        """Alias for sub_award_date."""
        return self.sub_award_date