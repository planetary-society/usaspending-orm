"""Award model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from functools import cached_property
from datetime import datetime

from .lazy_record import LazyRecord
from .recipient import Recipient
from .location import Location
from .period_of_performance import PeriodOfPerformance
from .agency import Agency
from .download import AwardType, FileFormat

from ..exceptions import ValidationError

from ..utils.formatter import smart_sentence_case, to_float, to_date


if TYPE_CHECKING:
    from ..client import USASpending
    from ..queries.transactions_search import TransactionsSearch
    from ..queries.funding_search import FundingSearch
    from ..download.job import DownloadJob


class Award(LazyRecord):
    """Rich wrapper around a USAspending award record."""

    # Base fields common to all award types
    SEARCH_FIELDS = [
        "Award ID",
        "Recipient Name",
        "Recipent DUNS Number",
        "recipient_id",
        "Awarding Agency",
        "Awarding Agency Code",
        "Awarding Sub Agency",
        "Awarding Sub Agency Code",
        "Funding Agency",
        "Funding Agency Code",
        "Funding Sub Agency",
        "Funding Sub Agency Code",
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
        "Recipient UEI",
        "Recipient Location",
        "Primary Place of Performance",
    ]

    def __init__(
        self, data_or_id: Dict[str, Any] | str, client: Optional[USASpending] = None
    ):
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
        award_id = self.generated_unique_award_id
        if not award_id:
            raise ValidationError(
                "Cannot lazy-load Award data. Property `generated_unique_award_id` is required to fetch details."
            )
        try:
            # Use the awards resource to get full award data
            full_award = self._client.awards.get(award_id)
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
    def parent_award(self) -> Optional[Award]:
        """Reference to parent award for child awards."""
        data = self._lazy_get("parent_award")
        return Award(data, self._client) if data else None

    @property
    def category(self) -> str:
        """A field that generalizes the award's type."""
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
        if isinstance(self.get_value(["description", "Description"]), str):
            return smart_sentence_case(self.get_value(["description", "Description"]))
        return None

    @property
    def type(self) -> Optional[str]:
        """
        The mechanism used to distribute funding. The federal government can distribute
        funding in several forms. These award types include contracts, grants, loans,
        and direct payments.
        """
        return self._lazy_get("type", default="")

    @property
    def type_description(self) -> Optional[str]:
        """The plain text description of the type of the award"""
        return self.get_value(["type_description", "Award Type"], default="")

    @property
    def total_obligation(self) -> float:
        """The amount of money the government is obligated to pay for the award"""
        return to_float(self._lazy_get("total_obligation", "Award Amount")) or 0.0

    @property
    def subaward_count(self) -> Optional[int]:
        """The number of subawards associated with this award."""
        return int(self._lazy_get("subaward_count", default=0))

    @property
    def total_subaward_amount(self) -> Optional[float]:
        """The total amount of subawards for this award."""
        return to_float(self._lazy_get("total_subaward_amount", default=None))

    @property
    def date_signed(self) -> Optional[datetime]:
        """The date the award was signed"""
        return to_date(self._lazy_get("date_signed", default=None))

    @property
    def base_obligation_date(self) -> Optional[datetime]:
        """Base obligation date for the award."""
        return to_date(
            self.get_value(
                ["base_obligation_date", "Base Obligation Date"], default=None
            )
        )

    @property
    def total_account_outlay(self) -> Optional[float]:
        """The total amount of money that has been paid out for the award from the associated federal accounts"""
        return to_float(
            self._lazy_get("total_account_outlay", "Total Outlays", default=None)
        )

    @property
    def total_account_obligation(self) -> Optional[float]:
        """Total amount obligated for this award."""
        return to_float(self._lazy_get("total_account_obligation", default=None))

    @property
    def total_outlay(self) -> Optional[float]:
        """Total amount paid out for this award."""
        return to_float(
            self._lazy_get("total_account_outlay", "Total Outlays", default=None)
        )

    @property
    def account_outlays_by_defc(self) -> List[Dict[str, Any]]:
        """Outlays broken down by Disaster Emergency Fund Code (DEFC)."""
        return self._lazy_get("account_outlays_by_defc", default=[])

    @property
    def account_obligations_by_defc(self) -> List[Dict[str, Any]]:
        """Obligations broken down by Disaster Emergency Fund Code (DEFC)."""
        return self._lazy_get("account_obligations_by_defc", default=[])

    @cached_property
    def executive_details(self) -> Optional[Dict[str, Any]]:
        """Executive compensation details for the award recipient."""
        return self._lazy_get("executive_details")

    @property
    def recipient_uei(self) -> Optional[str]:
        """Recipient Unique Entity Identifier (UEI)."""
        return self.get_value(["recipient_uei", "Recipient UEI"])

    @property
    def covid19_obligations(self) -> float:
        """COVID-19 related obligations amount."""
        return to_float(
            self.get_value(["covid19_obligations", "COVID-19 Obligations"], default=0)
        )

    @property
    def covid19_outlays(self) -> float:
        """COVID-19 related outlays amount."""
        return to_float(
            self.get_value(["covid19_outlays", "COVID-19 Outlays"], default=0)
        )

    @property
    def infrastructure_obligations(self) -> float:
        """Infrastructure related obligations amount."""
        return to_float(
            self.get_value(
                ["infrastructure_obligations", "Infrastructure Obligations"], default=0
            )
        )

    @property
    def infrastructure_outlays(self) -> float:
        """Infrastructure related outlays amount."""
        return to_float(
            self.get_value(
                ["infrastructure_outlays", "Infrastructure Outlays"], default=0
            )
        )

    @property
    def potential_value(self) -> float:
        """Potential total value of the award."""
        return (
            to_float(
                self.get_value(
                    ["Award Amount", "Loan Amount"], default=self.total_obligation
                )
            )
            or 0.0
        )

    @property
    def award_amount(self) -> float:
        """Base award amount."""
        return to_float(self.get_value(["Award Amount", "Loan Amount"])) or 0.0

    @cached_property
    def period_of_performance(self) -> Optional[PeriodOfPerformance]:
        """Award period of performance dates."""
        if isinstance(self.get_value(["period_of_performance"]), dict):
            return PeriodOfPerformance(self._data["period_of_performance"])

        # Award search results return Period of Performance information in a flat structure
        # We need to assign these values to a PeriodOfPerformance object
        # to maintain consistency.
        date_keys = ["Start Date", "End Date", "Last Modified Date"]
        if any(self.get_value([k]) for k in date_keys):
            return PeriodOfPerformance(
                {
                    "start_date": self.get_value(
                        ["Start Date", "Period of Performance Start Date"]
                    ),
                    "end_date": self.get_value(
                        ["End Date", "Period of Performance Current End Date"]
                    ),
                    "last_modified_date": self.get_value(["Last Modified Date"]),
                }
            )
        return PeriodOfPerformance({})

    @cached_property
    def place_of_performance(self) -> Optional[Location]:
        """Award place of performance location."""
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
        """Award recipient with lazy loading."""
        # First check if we already have recipient data
        if isinstance(self.get_value(["recipient"]), dict):
            data = self._data.get("recipient")
            return Recipient(data, self._client) if data else None

        # Check if we have fallback fields before calling API
        recipient_keys = [
            "Recipient Name",
            "Recipient DUNS Number",
            "recipient_id",
            "recipient_hash",
        ]
        if any(self.get_value([k]) for k in recipient_keys):
            recipient = Recipient(
                {
                    "recipient_name": self.get_value(["Recipient Name"]),
                    "recipient_unique_id": self.get_value(["Recipient DUNS Number"]),
                    "recipient_id": self.get_value(["recipient_id"]),
                    "recipient_hash": self.get_value(["recipient_hash"]),
                },
                client=self._client,
            )

            # Add location if available to avoid separate API call
            if isinstance(self.get_value(["Recipient Location"]), dict):
                location_data = self._data.get("Recipient Location")
                recipient_location = (
                    Location(location_data, self._client) if location_data else None
                )
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
        data = self._data.get("funding_agency")
        return Agency(data, self._client) if data else None

    @cached_property
    def awarding_agency(self) -> Optional[Agency]:
        """Awarding agency information."""
        data = self._data.get("awarding_agency")
        return Agency(data, self._client) if data else None

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

    @cached_property
    def transactions_count(self) -> int:
        """Get all transactions associated with this award."""
        # Use the transactions search to get all transactions for this award
        return self._client.transactions.for_award(
            self.generated_unique_award_id
        ).count()

    @property
    def raw(self) -> Dict[str, Any]:
        """Raw award data dictionary."""
        return self._data

    @property
    def usa_spending_url(self) -> str:
        """USASpending.gov URL for this award."""
        award_id = self.generated_unique_award_id or ""
        return f"https://www.usaspending.gov/award/{award_id}/"

    def __repr__(self) -> str:
        """String representation of Award."""
        recipient_name = self.recipient.name if self.recipient else "?"
        award_id = self.prime_award_id or self.generated_unique_award_id or "?"
        return f"<Award {award_id} → {recipient_name}>"

    @property
    def _download_type(self) -> Optional[AwardType]:
        """
        The type required by the download API ('contract' or 'assistance'). 
        This must be implemented by model subclasses
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
            >>> contract = client.awards.get("CONT_AWD_123...")
            >>> job = contract.download(destination_dir="./data")
            >>> print(f"Job queued: {job.file_name}. Waiting...")
            >>> extracted_files = job.wait_for_completion(timeout=600)
            >>> print(f"Download complete. Files: {extracted_files}")
        """
        # Import inside method to avoid potential circular dependencies at the top level
        from ..exceptions import ConfigurationError, ValidationError

        if not self._client:
            raise ConfigurationError("Award instance requires a client reference (USASpending) to perform downloads.")

        # Use the unique ID which is required by the download API
        # Accessing the property might trigger a lazy load if the ID wasn't present initially.
        award_id = self.generated_unique_award_id
        download_type = self._download_type

        if not award_id:
            # If it's still None after access, raise error.
            raise ValidationError("Cannot download award data without a 'generated_unique_award_id'. Ensure the award object is fully loaded.")
        
        if not download_type:
             # Safety check in case a subclass doesn't implement _download_type or the implementation returns None
            raise ValidationError(f"Download is not supported or implemented for award type: {self.__class__.__name__}.")

        # Access the DownloadManager via the client's download resource.
        # We route the call through the appropriate method on the resource.
        if download_type == "contract":
            return self._client.downloads.contract(award_id, file_format, destination_dir)
        elif download_type == "assistance":
            return self._client.downloads.assistance(award_id, file_format, destination_dir)
