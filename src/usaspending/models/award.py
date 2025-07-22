
"""Award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property
from datetime import datetime

from .lazy_record import LazyRecord
from .recipient import Recipient
from .location import Location
from .transaction import Transaction
from .period_of_performance import PeriodOfPerformance
from .agency import Agency
from ..exceptions import ValidationError



from ..utils.formatter import smart_sentence_case, to_float, to_date

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
            raw = data_or_id.copy()
        elif isinstance(data_or_id, str):
            raw = {"generated_unique_award_id": data_or_id}
        else:
            raise ValidationError("Award expects a dict or an award_id string")
        super().__init__(raw, client)

    def _fetch_details(self) -> Optional[Dict[str, Any]]:
        """Fetch full award details from the awards resource."""
        award_id = self.get_value(['generated_unique_award_id'])
        if not award_id:
            raise ValidationError("Cannot lazy-load Award data. Property `generated_unique_award_id` is required to fetch details.")
        try:
            # Use the awards resource to get full award data
            full_award = self._client.awards.get(award_id)
            return full_award.raw
        except Exception:
            # If fetch fails, return None to avoid breaking the application
            return None

    # Core scalar properties
    @property
    def id(self) -> Optional[int]:
        """Internal USASpending database ID for this award."""
        return self._lazy_get("id")

    @property
    def prime_award_id(self) -> str:
        """Primary award identifier (PIID, FAIN, URI, etc.)."""
        return str(self.get_value(["Award ID", "piid", "fain", "uri"], default=""))

    @property
    def generated_unique_award_id(self) -> Optional[str]:
        """USASpending-generated unique award identifier."""
        return self.get_value(["generated_unique_award_id", "generated_internal_id"])

    @property
    def piid(self) -> Optional[str]:
        """
        The Procurement Instrument Identifier, a unique number assigned
        to a federal contract, grant, or other procurement action.
        """
        return self._lazy_get("piid")

    @property
    def fain(self) -> Optional[str]:
        """Federal Award Identification Number (FAIN) for grants."""
        return self._lazy_get("fain")

    @property
    def uri(self) -> Optional[str]:
        """Unique Record Identifier (URI) for grants."""
        return self._lazy_get("uri")

    @property
    def parent_award(self) -> Optional[Award]:
        """Reference to parent award for child awards."""
        data = self._lazy_get('parent_award')
        return Award(data, self._client) if data else None

    @property
    def  category(self) -> str:
        """The general classification of the award (contract, grant, etc.)."""
        return self._lazy_get("category", default="")
    
    @property
    def description(self) -> str:
        """
        For procurement awards: Per the FPDS data dictionary, a brief, summary
        level, plain English, description of the contract, award, or modification.
        Additional information: the description field may also include abbreviations,
        acronyms, or other information that is not plain English such as that required
        by OMB policies (CARES Act, etc).
        """
        return smart_sentence_case(self.get_value(["description", "Description"], default=""))
    
    @property
    def type(self) -> Optional[str]:
        """Get the award type code."""
        return self._lazy_get("type", default="")
    
    @property
    def type_description(self) -> Optional[str]:
        """Get the award type code description."""
        return self.get_value(["type_description", "Award Type"], default="")
    
    @property
    def total_obligation(self) -> float:
        """Total obligated amount for this award."""
        return to_float(self._lazy_get("total_obligation", "Award Amount")) or 0.0

    @property
    def subaward_count(self) -> Optional[int]:
        """Total amount paid out for this award."""
        return int(self._lazy_get("subaward_count", default=0))
   
    @property
    def total_subaward_amount(self) -> Optional[float]:
        """Total amount of subawards for this award."""
        return to_float(self._lazy_get("total_subaward_amount"),default=None)

    @property
    def date_signed(self) -> Optional[datetime]:
        """Date the award was signed."""
        return to_date(self._lazy_get("date_signed", default=None))

    @property
    def base_obligation_date(self) -> Optional[datetime]:
        """Base obligation date for the award."""
        return to_date(self.get_value(["base_obligation_date", "Base Obligation Date"], default=None))

    @property
    def base_exercised_options(self) -> Optional[float]:
        """The value of the award, including any options that have already been exercised"""
        return to_float(self._lazy_get("base_exercised_options", default=None))

    @property
    def base_and_all_options(self) -> Optional[float]:
        """The total potential value of the award if all available options are exercised in the future"""
        return to_float(self._lazy_get("base_and_all_options", default=None))

    @property
    def total_account_outlay(self) -> Optional[float]:
        """The total amount of money that has been paid out for the award from the associated federal accounts"""
        return to_float(self._lazy_get("total_account_outlay", "Total Outlays", default=None))
    
    @property
    def total_account_obligation(self) -> Optional[float]:
        """Total amount obligated for this award."""
        return to_float(self._lazy_get("total_account_obligation", default=None))

    @property
    def total_outlay(self) -> Optional[float]:
        """Total amount paid out for this award."""
        return to_float(self._lazy_get("total_account_outlay", "Total Outlays", default=None))

    @property
    def account_outlays_by_defc(self) -> List[Dict[str, Any]]:
        """Outlays broken down by Disaster Emergency Fund Code (DEFC)."""
        return self._lazy_get("account_outlays_by_defc", default=[])

    @property
    def account_obligations_by_defc(self) -> List[Dict[str, Any]]:
        """Obligations broken down by Disaster Emergency Fund Code (DEFC)."""
        return self._lazy_get("account_obligations_by_defc", default=[])

    @property
    def total_subsidy_cost(self) -> Optional[float]:
        """Total subsidy cost for loan programs."""
        return to_float(self._lazy_get("total_subsidy_cost", default=None))

    @property
    def total_loan_value(self) -> Optional[float]:
        """Total value of loans for loan programs."""
        return to_float(self._lazy_get("total_loan_value", default=None))

    @property
    def non_federal_funding(self) -> Optional[float]:
        """Non-federal funding amount for grants."""
        return to_float(self._lazy_get("non_federal_funding", default=None))

    @property
    def total_funding(self) -> Optional[float]:
        """Total funding including federal and non-federal sources."""
        return to_float(self._lazy_get("total_funding", default=None))

    @property
    def transaction_obligated_amount(self) -> Optional[float]:
        """Transaction-level obligated amount."""
        return to_float(self._lazy_get("transaction_obligated_amount", default=None))

    @property
    def record_type(self) -> Optional[int]:
        """Grant record type identifier."""
        return self._lazy_get("record_type")

    @property
    def cfda_info(self) -> List[Dict[str, Any]]:
        """Catalog of Federal Domestic Assistance information for grants."""
        return self.get_value(["cfda_info", "Assistance Listings"], default=[])

    @property
    def cfda_number(self) -> Optional[str]:
        """Primary CFDA number for grants."""
        return self.get_value(["cfda_number", "CFDA Number"])

    @property
    def primary_cfda_info(self) -> Optional[Dict[str, Any]]:
        """Primary CFDA program information."""
        return self.get_value(["primary_cfda_info", "primary_assistance_listing"])

    @cached_property
    def funding_opportunity(self) -> Optional[Dict[str, Any]]:
        """Funding opportunity details for grants."""
        return self._lazy_get("funding_opportunity")

    @cached_property
    def latest_transaction_contract_data(self) -> Optional[Dict[str, Any]]:
        """Latest contract transaction data with procurement-specific details."""
        return self._lazy_get("latest_transaction_contract_data")

    @cached_property
    def psc_hierarchy(self) -> Optional[Dict[str, Any]]:
        """Product/Service Code (PSC) hierarchy information."""
        return self._lazy_get("psc_hierarchy")

    @cached_property
    def naics_hierarchy(self) -> Optional[Dict[str, Any]]:
        """North American Industry Classification System (NAICS) hierarchy."""
        return self._lazy_get("naics_hierarchy")

    @cached_property
    def executive_details(self) -> Optional[Dict[str, Any]]:
        """Executive compensation details for the award recipient."""
        return self._lazy_get("executive_details")

    @property
    def sai_number(self) -> Optional[str]:
        """System for Award Identification (SAI) number for grants."""
        return self.get_value(["sai_number", "SAI Number"])

    @property
    def contract_award_type(self) -> Optional[str]:
        """Contract award type description."""
        return self.get_value(["contract_award_type", "Contract Award Type"])

    @property
    def naics_code(self) -> Optional[str]:
        """NAICS industry classification code."""
        naics_data = self.get_value(["naics", "NAICS"])
        if isinstance(naics_data, dict):
            return naics_data.get("code")
        return None

    @property
    def naics_description(self) -> Optional[str]:
        """NAICS industry classification description."""
        naics_data = self.get_value(["naics", "NAICS"])
        if isinstance(naics_data, dict):
            return naics_data.get("description")
        return None

    @property
    def psc_code(self) -> Optional[str]:
        """Product/Service Code (PSC) for contracts."""
        psc_data = self.get_value(["psc", "PSC"])
        if isinstance(psc_data, dict):
            return psc_data.get("code")
        return None

    @property
    def psc_description(self) -> Optional[str]:
        """Product/Service Code (PSC) description."""
        psc_data = self.get_value(["psc", "PSC"])
        if isinstance(psc_data, dict):
            return psc_data.get("description")
        return None

    @property
    def recipient_uei(self) -> Optional[str]:
        """Recipient Unique Entity Identifier (UEI)."""
        return self.get_value(["recipient_uei", "Recipient UEI"])

    @property
    def covid19_obligations(self) -> float:
        """COVID-19 related obligations amount."""
        return to_float(self.get_value(["covid19_obligations", "COVID-19 Obligations"], default=0))

    @property
    def covid19_outlays(self) -> float:
        """COVID-19 related outlays amount."""
        return to_float(self.get_value(["covid19_outlays", "COVID-19 Outlays"], default=0))

    @property
    def infrastructure_obligations(self) -> float:
        """Infrastructure related obligations amount."""
        return to_float(self.get_value(["infrastructure_obligations", "Infrastructure Obligations"], default=0))

    @property
    def infrastructure_outlays(self) -> float:
        """Infrastructure related outlays amount."""
        return to_float(self.get_value(["infrastructure_outlays", "Infrastructure Outlays"], default=0))



    @property
    def potential_value(self) -> float:
        """Potential total value of the award."""
        return to_float(
            self.get_value(["Award Amount", "Loan Amount"], default=self.total_obligation)
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

        # Award search results return Period of Performanec information in a flat structure
        # We need to assign these values to a PeriodOfPerformance object
        # to maintain consistency.
        date_keys = ["Start Date", "End Date", "Last Modified Date"]
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
        return PeriodOfPerformance({})

    @cached_property
    def place_of_performance(self) -> Optional[Location]:
        """Award place of performance location."""
        data = self.get_value(['place_of_performance', 'Primary Place of Performance'])
        return Location(data, self._client) if data else None

    @cached_property
    def recipient(self) -> Optional[Recipient]:
        """Award recipient with lazy loading."""
        # First check if we already have recipient data
        if isinstance(self.get_value(["recipient"]), dict):
            data = self._data.get('recipient')
            return Recipient(data, self._client) if data else None
        
        # Check if we have fallback fields before calling API
        recipient_keys = ["Recipient Name", "Recipient DUNS Number", "recipient_id", "recipient_hash"]
        if any(self.get_value([k]) for k in recipient_keys):
            recipient = Recipient({
                "recipient_name": self.get_value(["Recipient Name"]),
                "recipient_unique_id": self.get_value(["Recipient DUNS Number"]),
                "recipient_id": self.get_value(["recipient_id"]),
                "recipient_hash": self.get_value(["recipient_hash"]),
            }, client=self._client)
            
            # Add location if available to avoid separate API call
            if isinstance(self.get_value(["Recipient Location"]), dict):
                location_data = self._data.get("Recipient Location")
                recipient_location = Location(location_data, self._client) if location_data else None
                recipient.location = recipient_location
            
            return recipient
        
        # Only call API if we don't have enough info in the Award entry itself
        self._ensure_details()  # loads the full Award detail
        if isinstance(self.get_value(["recipient"]), dict):
            data = self._data.get("recipient")
            return Recipient(data, self._client) if data else None
        
        return None

    @cached_property
    def funding_agency(self) -> Optional[Agency]:
        """Funding agency information."""
        data = self._data.get('funding_agency')
        return Agency(data, self._client) if data else None

    @cached_property
    def awarding_agency(self) -> Optional[Agency]:
        """Awarding agency information."""
        data = self._data.get('awarding_agency')
        return Agency(data, self._client) if data else None

    @cached_property
    def transactions(self) -> List[Transaction]:
        return self._client.transactions.for_award(self.generated_unique_award_id).all()
    
    @cached_property
    def transactions_count(self) -> int:
        """Get all transactions associated with this award."""        
        # Use the transactions search to get all transactions for this award
        return self._client.transactions.for_award(self.generated_unique_award_id).count()

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