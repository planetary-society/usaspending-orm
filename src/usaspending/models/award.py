"""Award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property
from datetime import datetime
from decimal import Decimal

from .lazy_record import LazyRecord
from .recipient import Recipient
from .location import Location
from .period_of_performance import PeriodOfPerformance
from .agency import Agency
from .subtier_agency import SubTierAgency
from .download import AwardType, FileFormat

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..utils.formatter import smart_sentence_case, to_decimal, to_date

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..queries.transactions_search import TransactionsSearch
    from ..queries.funding_search import FundingSearch
    from ..queries.subawards_search import SubAwardsSearch
    from ..download.job import DownloadJob

logger = USASpendingLogger.get_logger(__name__)

class Award(LazyRecord):
    """Rich wrapper around a USAspending award record."""

    # Base fields common to all award types
    SEARCH_FIELDS = [
        "Award ID",
        "recipient_id",
        "Recipient Name",
        "Recipient DUNS Number",
        "Recipient UEI",
        "Recipient Location",
        "Awarding Agency",
        "Awarding Agency Code",
        "Awarding Sub Agency",
        "Awarding Sub Agency Code",
        "Funding Agency",
        "Funding Agency Code",
        "Funding Sub Agency",
        "Funding Sub Agency Code",
        "Place of Performance City Code",
        "Place of Performance State Code",
        "Place of Performance Country Code",
        "Place of Performance Zip5",
        "Description",
        "Last Modified Date",
        "Base Obligation Date",
        "prime_award_recipient_id",
        "generated_internal_id",
        "def_codes",
        "COVID-19 Obligations",
        "COVID-19 Outlays",
        "Infrastructure Obligations",
        "Infrastructure Outlays",
        "Primary Place of Performance",
    ]

    def __init__(
        self, data_or_id: Dict[str, Any] | str, client: USASpendingClient
    ):
        """
        Initialize Award instance.

        Args:
            data_or_id (Dict[str, Any] | str): Either a dictionary containing award data (must include 'generated_unique_award_id'), or a string representing the unique award identifier. If a dictionary is provided with additional properties, those will be used to populate the instance.
            client (USASpendingClient): USASpendingClient client instance.

        Raises:
            ValidationError: If data_or_id is not a dict or string, or if required keys are missing.
        """
        if isinstance(data_or_id, dict):
            raw = data_or_id.copy()
        elif isinstance(data_or_id, str):
            raw = {"generated_unique_award_id": data_or_id}
        else:
            raise ValidationError("Award expects a dict with the generated_unique_award_id key present, or a string of the same id.")
        super().__init__(raw, client)

    def _fetch_details(self) -> Optional[Dict[str, Any]]:
        """Fetch full award details from the awards resource.
        
        Returns:
            Optional[Dict[str, Any]]: Award data dictionary or None if fetch fails.
        """
        award_id = self.generated_unique_award_id
        if not award_id:
            raise ValidationError(
                "Cannot lazy-load Award data. Property `generated_unique_award_id` is required to fetch details."
            )
        try:
            # Use the awards resource to get full award data
            full_award = self._client.awards.find_by_generated_id(award_id)
            full_data = full_award.raw

            # If we're a base Award class and now have type information,
            # convert to appropriate subclass
            if full_data and self.__class__ == Award:
                from .award_factory import create_award

                new_instance = create_award(full_data, self._client)
                if new_instance.__class__ != Award:
                    # Copy state from new instance to self
                    self.__class__ = new_instance.__class__
                    # Merge the data
                    self._data.update(full_data)
                    return full_data

            return full_data
        except Exception:
            logger.error(
                f"Failed to fetch full details for Award ID {award_id}. "
                "Check if the ID is valid and the client is configured correctly."
            )
            raise

    # Core Award properties
    @property
    def id(self) -> Optional[int]:
        """Internal USASpending database ID for this award.
        
        Returns:
            Optional[int]: Internal USASpending database ID.
        """
        return self._lazy_get("id","internal_id")

    @property
    def generated_unique_award_id(self) -> Optional[str]:
        """The award identifier used across USASpending and its Broker systems.
        
        The code is created by combining various identifiers of award type, awarding
        agency codes, and other standard identifiers:
        
        Procurement Award ID Formats (FPDS):
        `upper('CONT_AWD' + '_' + Coalesce(<piid>,'-NONE-') + '_' +  Coalesce(<agency_id>,'-NONE-') + '_' + Coalesce(<parent_award_id>,'-NONE-') + '_' +  Coalesce(<referenced_idv_agency_iden>,'-NONE-'))`
        `upper('CONT_IDV' + '_' + Coalesce(<piid>,'-NONE-') + '_' +  Coalesce(<agency_id>,'-NONE-'))`
        
        Assistance Award ID Formats (FABS)
        `upper('ASST_AGG' + '_' +  Coalesce(<uri>,'-NONE-') + '_' +  Coalesce(<awarding_sub_tier_agency_c>,'-NONE-'))`
        `upper('ASST_NON' + '_' +  Coalesce(<fain>,'-NONE-') + '_' +  Coalesce(<awarding_sub_tier_agency_c>,'-NONE-'))`
        
        Returns:
            Optional[str]: The generated unique award identifier.
        """
        # This cannot be lazy-loaded since it's required to fetch details
        return self.get_value(["generated_unique_award_id", "generated_internal_id"])

    @property
    def award_identifier(self) -> str:
        """General-purpose award identifier, type-agnostic.

        Specific property getters for PIID, FAIN, and URI are implemented in subclasses such as Contract, Grant, and IDV.
        Use this property for a unified identifier, and refer to subclass documentation for type-specific identifiers.

        Returns:
            str: The award identifier (PIID, FAIN, or URI).
            
        Example:
            contract = Contract(...)
            print(contract.award_identifier)  # Returns PIID for contracts
        """
        return str(self._lazy_get("Award ID", "piid", "fain", "uri", default=""))

    @property
    def category(self) -> str:
        """Plain English description of the award type.

        Returns:
            str: One of "contract", "grant", "idv", "loan", or "other" if unknown.
        """
        return self._lazy_get("category", default="")

    @property
    def type(self) -> Optional[str]:
        """Award's subtype code.
        
        See `award_types.py` for all valid codes.
        
        Returns:
            Optional[str]: The award subtype code.
        """
        return self._lazy_get("type", default="")
    
    @property
    def award_type_code(self) -> Optional[str]:
        """More expressive property name for `type` to avoid confusion with Python built-in.
        
        Returns:
            Optional[str]: The award subtype code.
        """
        return self.type
    
    @property
    def type_description(self) -> Optional[str]:
        """Plain text description of the award type.

        Retrieves a description for the award type using a lazy getter,
        prioritizing "Contract Award Type" and "Award Type" keys.

        Returns:
            Optional[str]: The description of the award type, or empty string if not available.
        """
        return self._lazy_get("type_description", "Contract Award Type", "Award Type", default="")

    @property
    def description(self) -> str:
        """Brief, plain English summary of the award.

        Returns:
            str: The award description in sentence case, or empty string if not available.
        """
        desc = self._lazy_get("description", "Description")
        if isinstance(desc, str):
            return smart_sentence_case(desc)
        return ""

    @property
    def total_obligation(self) -> Decimal:
        """The amount of money the government is obligated to pay for the award.
        
        This is a system generated element providing the sum of all the amounts
        entered in the "Action Obligation" field for a particular PIID and Agency.
        
        Example: Contract has 9 Modifications under "Transaction Number" as '1'
        and 9 modifications with the same PIID under "Transaction Number" as '2'.
        The base contracts and all the modifications have "Action Obligation" as $10
        each. The value for the field "Total Obligated Amount" when the either of
        the bases or the modification is retrieved through atom feeds will be $200
        ($100 under Transaction Number 1 + $100 under Transaction Number 2). 
        "Total Obligated Amount" is generated irrespective of the "Transaction Number"
        on the Awards.
        
        Returns:
            Decimal: The total obligated amount for the award or 0.00.
        
        """
        return to_decimal(self._lazy_get("total_obligation", "Award Amount")) or Decimal('0.00')

    @property
    def subaward_count(self) -> int:
        """Number of subawards associated with this award.
        
        Returns:
            int: The count of subawards.
        """
        return int(self._lazy_get("subaward_count", default=0))

    @property
    def total_subaward_amount(self) -> Optional[Decimal]:
        """Total amount of subawards for this award.
        
        Returns:
            Optional[Decimal]: The total subaward amount, or None if not available.
        """
        return to_decimal(self._lazy_get("total_subaward_amount", default=None))

    @property
    def date_signed(self) -> Optional[datetime]:
        """Date the award was signed by the Government or a binding agreement was reached.
        
        Returns:
            Optional[datetime]: The date the award was signed, or None if not available.
        """
        return to_date(self._lazy_get("date_signed", "Base Obligation Date", default=None))

    @property
    def base_obligation_date(self) -> Optional[datetime]:
        """Base obligation date for the award (alias for date_signed).
        
        Returns:
            Optional[datetime]: The base obligation date, or None if not available.
        """
        return self.date_signed

    @property
    def total_account_outlay(self) -> Optional[Decimal]:
        """Total amount of money paid out for the award from associated federal accounts.
        
        Returns:
            Optional[Decimal]: The total account outlay amount, or None if not available.
        """
        return to_decimal(
            self._lazy_get("total_account_outlay", default=None)
        )

    @property
    def total_account_obligation(self) -> Optional[Decimal]:
        """Total amount obligated for this award.
        
        Returns:
            Optional[Decimal]: The total account obligation amount, or None if not available.
        """
        return to_decimal(self._lazy_get("total_account_obligation", default=None))

    @property
    def total_outlay(self) -> Optional[Decimal]:
        """Total outlay amount for the award.
        
        Returns:
            Optional[Decimal]: The total outlay amount, or None if not available.
        """
        return to_decimal(self._lazy_get("total_outlay", "Total Outlays", default=None))

    @property
    def account_outlays_by_defc(self) -> List[Dict[str, Any]]:
        """Outlays broken down by Disaster Emergency Fund Code (DEFC).
        
        Returns:
            List[Dict[str, Any]]: List of outlay records by DEFC code.
        """
        return self._lazy_get("account_outlays_by_defc", default=[])

    @property
    def account_obligations_by_defc(self) -> List[Dict[str, Any]]:
        """Obligations broken down by Disaster Emergency Fund Code (DEFC).
        
        Returns:
            List[Dict[str, Any]]: List of obligation records by DEFC code.
        """
        return self._lazy_get("account_obligations_by_defc", default=[])

    @cached_property
    def parent_award(self) -> Optional[Award]:
        """Reference to parent award for child awards.
        
        Returns:
            Optional[Award]: The parent award object, or None if this is a parent award.
        """
        data = self._lazy_get("parent_award")
        from .award_factory import create_award
        return create_award(data, self._client) if data else None

    @cached_property
    def executive_details(self) -> Optional[Dict[str, Any]]:
        """Executive compensation details for the award recipient.
        
        Returns:
            Optional[Dict[str, Any]]: Executive compensation data, or None if not available.
        """
        return self._lazy_get("executive_details")

    @property
    def recipient_uei(self) -> Optional[str]:
        """Recipient Unique Entity Identifier (UEI).
        
        Returns:
            Optional[str]: The recipient's UEI, or None if not available.
        """
        uei = self._lazy_get("recipient_uei", "Recipient UEI")
        if not uei:
            # Try nested recipient object if available
            if self.recipient and self.recipient.uei:
                uei = self.recipient.uei
        return uei

    @property
    def covid19_obligations(self) -> Decimal:
        """COVID-19 related obligations amount.
        
        Returns:
            Decimal: The COVID-19 obligations amount, or 0.00 if not available.
        """
        return to_decimal(
            self._lazy_get("covid19_obligations", "COVID-19 Obligations", default=0)
        ) or Decimal('0.00')

    @property
    def covid19_outlays(self) -> Decimal:
        """COVID-19 related outlays amount.
        
        Returns:
            Decimal: The COVID-19 outlays amount, or 0.00 if not available.
        """
        return to_decimal(
            self._lazy_get("covid19_outlays", "COVID-19 Outlays", default=0)
        ) or Decimal('0.00')

    @property
    def infrastructure_obligations(self) -> Decimal:
        """Infrastructure related obligations amount.
        
        Returns:
            Decimal: The infrastructure obligations amount, or 0.00 if not available.
        """
        return to_decimal(
            self._lazy_get(
                "infrastructure_obligations", "Infrastructure Obligations", default=0
            )
        ) or Decimal('0.00')

    @property
    def infrastructure_outlays(self) -> Decimal:
        """Infrastructure related outlays amount.
        
        Returns:
            Decimal: The infrastructure outlays amount, or 0.00 if not available.
        """
        return to_decimal(
            self._lazy_get(
                "infrastructure_outlays", "Infrastructure Outlays", default=0
            )
        ) or Decimal('0.00')


    # Helper properties properties. These often map to field names returned by
    # the spending_by_award/Award Search results, or provide general access methods
    # that are common across award types.
    
    @property
    def award_amount(self) -> Decimal:
        """General helper for total obligated or loaned amount.
        
        Returns:
            Decimal: The total award amount, or 0.00 if not available.
        """
        return to_decimal(self._lazy_get("Award Amount", "Loan Amount", "total_obligation","total_funding")) or Decimal('0.00')

    @property
    def start_date(self) -> Optional[datetime]:
        """Award start date from period of performance or obligation data.
        
        Returns:
            Optional[datetime]: The award start date, or None if not available.
        """
        start_date = self.get_value(["Start Date", "Base Obligation Date", "Period of Performance Start Date"])
        if not start_date:
            if self.period_of_performance and self.period_of_performance.start_date:
                start_date = self.period_of_performance.start_date
        return start_date

    @property
    def end_date(self) -> Optional[datetime]:
        """Award end date from period of performance data.
        
        Returns:
            Optional[datetime]: The award end date, or None if not available.
        """
        end_date = self.get_value(["End Date", "Period of Performance End Date"])
        if not end_date:
            if self.period_of_performance and self.period_of_performance.end_date:
                end_date = self.period_of_performance.end_date
        return end_date

    @property
    def usa_spending_url(self) -> str:
        """USASpending.gov public URL for this award.
        
        Returns:
            str: The public URL for this award, or empty string if award ID unavailable.
        """
        award_id = self.generated_unique_award_id
        if award_id and isinstance(award_id, str):
            return f"https://www.usaspending.gov/award/{award_id}/"
        else:
            return ""

    # Properties that return complex objects and related award data
    #
    # Currently implemented are:
    #
    # Belongs To (one-to-one relationships):
    # - parent_award (Award object: parent award if this is a child award)
    # - recipient (Recipient object: details about the award recipient)
    # - funding_agency (Agency object: details about the funding agency)
    # - awarding_agency (Agency object: details about the awarding agency)
    # - funding_subtier_agency (SubTierAgency object: details about the funding subtier agency)
    # - awarding_subtier_agency (SubTierAgency object: details about the awarding subtier agency)
    #
    # Has One (one-to-one relationships):
    # - period_of_performance (PlaceOfPerformance object: Start and End dates for award)
    # - place_of_performance (Location object: location where the work is performed)
    #
    # Has Many (one-to-many relationships):
    # - transactions (TransactionsSearch object: query builder for transactions associated with the award)
    # - funding (FundingSearch object: query builder for treasury funding records (outlay and obligation) associated with the award)
    # - subawards (SubAwardsSearch object: query builder for subawards associated with the award)
    

    @cached_property
    def period_of_performance(self) -> Optional[PeriodOfPerformance]:
        """Award period of performance dates.
        
        Returns:
            Optional[PeriodOfPerformance]: Period of performance object with start/end dates, or None.
        """
        if "period_of_performance" in self.raw and isinstance(self.raw.get("period_of_performance"), dict):
            return PeriodOfPerformance(self.raw.get("period_of_performance"))

        # Award search results return Period of Performance information in a flat structure
        # We need to assign these values to a PeriodOfPerformance object
        # to maintain consistency.
        date_keys = ["Start Date", "End Date", "Last Modified Date"]
        if any(k in self._data for k in date_keys):
            return PeriodOfPerformance(
                {
                    "start_date": self.get_value(["Start Date", "Base Obligation Date", "Period of Performance Start Date"]),
                    "end_date": self.get_value(["End Date", "Period of Performance Current End Date"]),
                    "last_modified_date": self.get_value("Last Modified Date"),
                }
            )

        # If no data, trigger fetch
        self._ensure_details()        
        return PeriodOfPerformance(self.get_value("period_of_performance"))


    @cached_property
    def place_of_performance(self) -> Optional[Location]:
        """Award place of performance location.
        
        Returns:
            Optional[Location]: Location object for where work is performed, or None.
        """
        data = self._lazy_get(
            "place_of_performance", "Primary Place of Performance", default=None
        )
        if not isinstance(data, dict) or not data:
            return None

        # Check if all values in the dict are None/null (common for IDV awards)
        if all(v is None for v in data.values()):
            return None

        return Location(data, self._client)

    @cached_property
    def recipient(self) -> Optional[Recipient]:
        """Award recipient with lazy loading.
        
        Returns:
            Optional[Recipient]: Recipient object with award recipient details, or None.
        """
        # First check if we already have a nested recipient object
        if "recipient" in self._data and isinstance(self._data["recipient"], dict):
            return Recipient(self._data["recipient"], self._client)

        # Then, check for flat recipient fields from search results
        recipient_keys = ["Recipient Name", "recipient_id", "Recipient Location"]
        if any(key in self._data for key in recipient_keys):
            recipient_data = {
                "recipient_name": self._data.get("Recipient Name"),
                "recipient_unique_id": self._data.get("Recipient DUNS Number"),
                "recipient_id": self._data.get("recipient_id"),
                "recipient_hash": self._data.get("recipient_hash"),
                "recipient_uei": self._data.get("Recipient UEI"),
            }
            recipient = Recipient(recipient_data, self._client)
            if "Recipient Location" in self._data and isinstance(self._data["Recipient Location"], dict):
                recipient.location = Location(self._data["Recipient Location"], self._client)
            return recipient

        # If no recipient data is available locally, trigger a fetch
        self._ensure_details()
        if "recipient" in self._data and isinstance(self._data["recipient"], dict):
            return Recipient(self._data["recipient"], self._client)

        return None

    def _load_agency_data(self, agency_type: str) -> Optional[Dict[str, Any]]:
        """Load agency data from either nested or flat structure.
        
        Args:
            agency_type (str): Either "funding" or "awarding".
            
        Returns:
            Optional[Dict[str, Any]]: Processed agency data dict or None if not available.
        """
        if agency_type not in ["funding", "awarding"]:
            raise ValueError(f"Invalid agency_type: {agency_type}")
        
        # Define field mappings based on agency type
        if agency_type == "funding":
            nested_key = "funding_agency"
            flat_keys = ["Funding Agency", "Funding Agency Code",
                        "Funding Sub Agency", "Funding Sub Agency Code"]
            name_key = "Funding Agency"
            code_key = "Funding Agency Code" 
            sub_name_key = "Funding Sub Agency"
            sub_code_key = "Funding Sub Agency Code"
            # No funding_agency_id available in search results
            id_key = None
        else:  # awarding
            nested_key = "awarding_agency"
            flat_keys = ["Awarding Agency", "Awarding Agency Code",
                        "Awarding Sub Agency", "Awarding Sub Agency Code"]
            name_key = "Awarding Agency"
            code_key = "Awarding Agency Code"
            sub_name_key = "Awarding Sub Agency"
            sub_code_key = "Awarding Sub Agency Code"
            id_key = "awarding_agency_id"
        
        # First check if we have nested agency data (from full award details)
        if self.raw.get(nested_key):
            return self.raw.get(nested_key)
        
        # Then check for flat agency fields (from search results)
        if any(key in self.raw for key in flat_keys):
            data = {
                "toptier_agency": {
                    "name": self.raw.get(name_key),
                    "code": self.raw.get(code_key),  # Agency code
                    "abbreviation": self.raw.get(code_key),
                },
                "subtier_agency": {
                    "name": self.raw.get(sub_name_key),
                    "code": self.raw.get(sub_code_key),  # Subtier code
                    "abbreviation": self.raw.get(sub_code_key),
                },
                "id": self.raw.get(id_key) if id_key else None,
                "has_agency_page": False,  # Not available in search results
                "office_agency_name": None,  # Not available in search results
            }
            return data
        
        # Finally try lazy loading
        return self._lazy_get(nested_key)

    @cached_property
    def funding_agency(self) -> Optional[Agency]:
        """Funding agency information.
        
        Returns:
            Optional[Agency]: Agency object for the funding agency, or None.
        """
        data = self._load_agency_data("funding")
        
        if not data:
            return None
            
        # Extract toptier data and merge with top-level agency fields
        toptier_data = data.get("toptier_agency", {})
        agency_data = {
            "agency_id": data.get("id"),
            "has_agency_page": data.get("has_agency_page"),
            "office_agency_name": data.get("office_agency_name"),
            **toptier_data  # Merge toptier fields (name, code, abbreviation, slug)
        }
        
        subtier_data = data.get("subtier_agency")
        return Agency(agency_data, self._client, subtier_data)

    @cached_property
    def awarding_agency(self) -> Optional[Agency]:
        """Awarding agency information.
        
        Returns:
            Optional[Agency]: Agency object for the awarding agency, or None.
        """
        data = self._load_agency_data("awarding")
        
        if not data:
            return None
            
        # Extract toptier data and merge with top-level agency fields
        toptier_data = data.get("toptier_agency", {})
        agency_data = {
            "agency_id": data.get("id"),
            "has_agency_page": data.get("has_agency_page"),
            "office_agency_name": data.get("office_agency_name"),
            **toptier_data  # Merge toptier fields (name, code, abbreviation, slug)
        }
        
        subtier_data = data.get("subtier_agency")
        return Agency(agency_data, self._client, subtier_data)

    @cached_property
    def funding_subtier_agency(self) -> Optional["SubTierAgency"]:
        """Funding subtier agency information.
        
        Returns:
            Optional[SubTierAgency]: SubTierAgency object for the funding subtier, or None.
        """
        data = self._load_agency_data("funding")
        
        if not data:
            return None
        
        subtier_data = data.get("subtier_agency")
        if not subtier_data:
            return None
        
        # Create a copy and add office_agency_name if available
        enhanced_subtier_data = subtier_data.copy()
        office_name = data.get("office_agency_name")
        if office_name:
            enhanced_subtier_data["office_agency_name"] = office_name
            
        from .subtier_agency import SubTierAgency
        return SubTierAgency(enhanced_subtier_data, self._client)

    @cached_property
    def awarding_subtier_agency(self) -> Optional["SubTierAgency"]:
        """Awarding subtier agency information.
        
        Returns:
            Optional[SubTierAgency]: SubTierAgency object for the awarding subtier, or None.
        """
        data = self._load_agency_data("awarding")
        
        if not data:
            return None
        
        subtier_data = data.get("subtier_agency")
        if not subtier_data:
            return None
        
        # Create a copy and add office_agency_name if available
        enhanced_subtier_data = subtier_data.copy()
        office_name = data.get("office_agency_name")
        if office_name:
            enhanced_subtier_data["office_agency_name"] = office_name
            
        from .subtier_agency import SubTierAgency
        return SubTierAgency(enhanced_subtier_data, self._client)

    @property
    def transactions(self) -> "TransactionsSearch":
        """Get transactions query builder for this award.

        Returns a TransactionsSearch object that can be further filtered and chained.

        Examples:
            >>> award.transactions.count()  # Get count without loading all data
            >>> award.transactions.limit(10).all()  # Get first 10 transactions
            >>> list(award.transactions)  # Iterate through all transactions
        """
        return self._client.transactions.for_award(self.generated_unique_award_id)

    @property
    def funding(self) -> "FundingSearch":
        """Get funding query builder for this award.

        Returns a FundingSearch object that can be further filtered and chained.

        Examples:
            >>> award.funding.count()  # Get count without loading all data
            >>> award.funding.order_by("fiscal_date", "asc").all()  # Get all funding records sorted by date
            >>> list(award.funding.limit(10))  # Iterate through first 10 funding records
        """
        return self._client.funding.for_award(self.generated_unique_award_id)

    @property
    def subawards(self) -> "SubAwardsSearch":
        """Get subawards query builder for this award.

        Returns:
            SubAwardsSearch: Query builder object for subawards (implemented in subclasses).
            
        Note:
            Implemented in subclasses.
        """
        raise NotImplementedError()
    

    # Downloading detailed award data
    @property
    def _download_type(self) -> Optional[AwardType]:
        """Type required by the download API.
        
        Returns:
            Optional[AwardType]: Download type ('contract', 'assistance', or 'idv').
            
        Note:
            Implementation varies by model subclass.
        """
        from .contract import Contract
        from .grant import Grant
        from .idv import IDV

        if isinstance(self, Contract):
            return "contract"
        elif isinstance(self, Grant):
            return "assistance"
        elif isinstance(self, IDV):
            return "idv"
        else:
            raise(NotImplementedError)
        

    def download(self, file_format: FileFormat = "csv", destination_dir: Optional[str] = None) -> "DownloadJob":
        """
        Queue a download job for this award's detailed data.

        This utilizes the USASpending bulk download API, which queues the request 
        and processes it asynchronously.

        Args:
            file_format: The format of the file(s) in the zip file containing the data
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob object. Use job.wait_for_completion() to block until finished.
        
        Raises:
            ConfigurationError: If the Award instance lacks a client reference.
            ValidationError: If the award ID or download type is missing/invalid.

        Example:
            >>> contract = client.awards.find_by_generated_id("CONT_AWD_123...")
            >>> job = contract.download(destination_dir="./data")
            >>> print(f"Job queued: {job.file_name}. Waiting...")
            >>> extracted_files = job.wait_for_completion(timeout=600)
            >>> print(f"Download complete. Files: {extracted_files}")
        """

        award_id = self.generated_unique_award_id
        
        if not award_id:
            # If we don't have an award ID, we cannot proceed
            raise ValidationError("Cannot download award data without a 'generated_unique_award_id'. Ensure the award object is fully loaded.")
        
        download_type = self._download_type

        if not download_type:
             # Safety check in case a subclass doesn't implement _download_type or the implementation returns None
            raise ValidationError(f"Download is not supported or implemented for award type: {self.__class__.__name__}.")

        # Access the DownloadManager via the client's download resource.
        # We route the call through the appropriate method on the resource.
        if download_type == "contract":
            return self._client.downloads.contract(award_id, file_format, destination_dir)
        elif download_type == "assistance":
            return self._client.downloads.assistance(award_id, file_format, destination_dir)
        elif download_type == "idv":
            return self._client.downloads.idv(award_id, file_format, destination_dir)
        else:
            raise NotImplementedError

    def __repr__(self) -> str:
        """String representation of Award.
        
        Returns:
            str: Formatted string showing award ID and recipient name.
        """
        recipient_name = self.recipient.name if self.recipient else "?"
        award_id = self.award_identifier or self.generated_unique_award_id or "?"
        return f"<Award {award_id} → {recipient_name}>"
