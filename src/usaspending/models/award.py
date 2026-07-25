"""Award model for USASpending data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..utils.formatter import smart_sentence_case, to_date, to_decimal, to_int
from .agency import Agency
from .award_identifier import parse_award_identifier
from .award_types import DOWNLOAD_TYPES
from .download import AwardType, FileFormat
from .lazy_record import LazyRecord
from .location import Location
from .period_of_performance import PeriodOfPerformance
from .recipient import Recipient
from .subtier_agency import SubTierAgency

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..download.job import DownloadJob
    from ..queries.award_accounts_query import AwardAccountsQuery
    from ..queries.funding_search import FundingSearch
    from ..queries.subawards_search import SubAwardsSearch
    from ..queries.transactions_search import TransactionsSearch

logger = USASpendingLogger.get_logger(__name__)


class Award(LazyRecord):
    """Rich wrapper around a USAspending award record.

    This class serves as the base for all award types (Contract, Grant, IDV, Loan)
    and provides access to common fields and related resources like recipients,
    agencies, transactions, and subawards.
    """

    # Download type for bulk download API - override in subclasses
    _download_type: str | None = None

    # Base fields common to all award types
    SEARCH_FIELDS: ClassVar[list[str]] = [
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

    def __init__(self, data_or_id: dict[str, Any] | str, client: USASpendingClient):
        """Initialize Award instance.

        Args:
            data_or_id: Either a dictionary containing award data (must include 'generated_unique_award_id'),
                or a string representing the unique award identifier.
                If a dictionary is provided with additional properties, those will be used to populate the instance.
            client: USASpendingClient client instance.

        Raises:
            ValidationError: If data_or_id is not a dict or string, or if required keys are missing.
        """
        # Use the base validation method
        raw = self.validate_init_data(
            data_or_id,
            "Award",
            id_field="generated_unique_award_id",
            allow_string_id=True,
        )
        super().__init__(raw, client)

    def _fetch_details(self) -> dict[str, Any] | None:
        """Fetch full award details from the awards resource.

        Note:
            When this instance is a base ``Award``, the fetched data reveals the
            award type for the first time and the instance rebinds its own
            ``__class__`` to the matching subclass. That reassignment is
            deliberate late binding, not a workaround.

            An award can be constructed before its type is knowable: from an ID
            alone, or from ``SubAward.parent_award`` and ``Award.parent_award``,
            which build a bare ``Award`` from an identifier carried on the child
            record. There is no type code in either case. The alternatives are
            worse. Returning the base class permanently would silently deny
            callers ``Contract.piid``, ``Grant.cfda_number`` and every other
            subtype member, and returning a fresh object instead would leave the
            caller holding a stale instance, since lazy loading is triggered
            through attribute access on an award the caller already has.

            The type decision itself is not duplicated here: it is delegated to
            :func:`~usaspending.models.award_factory.create_award`, the same
            factory the resource layer uses. This code only adopts the class the
            factory chose. ``tests/test_characterization.py`` pins the upgrade
            for both the ID-only and ``parent_award`` paths.

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

            # The type code arrives only with the detail response, so adopt the
            # subclass the factory picks. See the note in this method's docstring.
            if full_data and self.__class__ == Award:
                from .award_factory import create_award

                new_instance = create_award(full_data, self._client)
                if new_instance.__class__ != Award:
                    self.__class__ = new_instance.__class__
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
    def id(self) -> int | None:
        """Internal USASpending database ID for this award.

        Returns:
            Optional[int]: Internal USASpending database ID.
        """
        return self._lazy_get("id", "internal_id")

    @property
    def generated_unique_award_id(self) -> str | None:
        """The award identifier used across USASpending and its Broker systems.

        The code is created by combining various identifiers of award type, awarding
        agency codes, and other standard identifiers.

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
            str: The award identifier (PIID, FAIN, or URI), or empty string if not found.
        """
        return parse_award_identifier(self.generated_unique_award_id) or ""

    @property
    def category(self) -> str:
        """Plain English description of the award type.

        Returns:
            str: One of "contract", "grant", "idv", "loan", or "other" if unknown.
        """
        return self._lazy_get("category", default="")

    @property
    def type(self) -> str | None:
        """Award's subtype code.

        See `award_types.py` for all valid codes.

        Returns:
            Optional[str]: The award subtype code.
        """
        return self._lazy_get("type", default="")

    @property
    def award_type_code(self) -> str | None:
        """More expressive property name for `type` to avoid confusion with Python built-in.

        Returns:
            Optional[str]: The award subtype code.
        """
        return self.type

    @property
    def type_description(self) -> str | None:
        """Plain text description of the award type.

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
    def total_obligation(self) -> Decimal | None:
        """The amount of money the government is obligated to pay for the award.

        This is a system generated element providing the sum of all the amounts
        entered in the "Action Obligation" field.

        Returns:
            Optional[Decimal]: The total obligated amount, or None when the
            award reports none. A reported zero returns ``Decimal("0.00")``.
        """
        return to_decimal(self._lazy_get("total_obligation", "Award Amount"))

    @property
    def subaward_count(self) -> int:
        """Number of subawards associated with this award.

        Returns:
            int: The count of subawards.
        """
        return to_int(self._lazy_get("subaward_count", default=0)) or 0

    @property
    def total_subaward_amount(self) -> Decimal | None:
        """Total amount of subawards for this award.

        Returns:
            Optional[Decimal]: The total subaward amount, or None if not available.
        """
        return to_decimal(self._lazy_get("total_subaward_amount", default=None))

    @property
    def date_signed(self) -> date | None:
        """Date the award was signed by the Government or a binding agreement was reached.

        Returns:
            Optional[date]: The date the award was signed, or None if not available.
        """
        return to_date(self._lazy_get("date_signed", "Base Obligation Date", default=None))

    @property
    def base_obligation_date(self) -> date | None:
        """Base obligation date for the award (alias for date_signed).

        Returns:
            Optional[date]: The base obligation date, or None if not available.
        """
        return self.date_signed

    @property
    def total_account_outlay(self) -> Decimal | None:
        """Total amount of money paid out for the award from associated federal accounts.

        Returns:
            Optional[Decimal]: The total account outlay amount, or None if not available.
        """
        return to_decimal(self._lazy_get("total_account_outlay", default=None))

    @property
    def total_account_obligation(self) -> Decimal | None:
        """Total amount obligated for this award from associated federal accounts.

        Returns:
            Optional[Decimal]: The total account obligation amount, or None if not available.
        """
        return to_decimal(self._lazy_get("total_account_obligation", default=None))

    @property
    def total_outlay(self) -> Decimal | None:
        """Total outlay amount for the award.

        Returns:
            Optional[Decimal]: The total outlay amount, or None if not available.
        """
        return to_decimal(self._lazy_get("total_outlay", "Total Outlays", default=None))

    @property
    def account_outlays_by_defc(self) -> list[dict[str, Any]]:
        """Outlays broken down by Disaster Emergency Fund Code (DEFC).

        Returns:
            List[Dict[str, Any]]: List of outlay records by DEFC code.
        """
        return self._lazy_get("account_outlays_by_defc", default=[])

    @property
    def account_obligations_by_defc(self) -> list[dict[str, Any]]:
        """Obligations broken down by Disaster Emergency Fund Code (DEFC).

        Returns:
            List[Dict[str, Any]]: List of obligation records by DEFC code.
        """
        return self._lazy_get("account_obligations_by_defc", default=[])

    @cached_property
    def parent_award(self) -> Award | None:
        """Reference to parent award for child awards.

        Returns:
            Optional[Award]: The parent award object, or None if this is a parent award.
        """
        data = self._lazy_get("parent_award")
        from .award_factory import create_award

        return create_award(data, self._client) if data else None

    @cached_property
    def executive_details(self) -> dict[str, Any] | None:
        """Executive compensation details for the award recipient.

        Returns:
            Optional[Dict[str, Any]]: Executive compensation data, or None if not available.
        """
        return self._lazy_get("executive_details")

    @property
    def recipient_uei(self) -> str | None:
        """Recipient Unique Entity Identifier (UEI).

        Returns:
            Optional[str]: The recipient's UEI, or None if not available.
        """
        # Try nested recipient object if available
        if self.recipient and self.recipient.uei:
            uei = self.recipient.uei
        else:
            uei = self._lazy_get("recipient_uei", "Recipient UEI")

        return uei

    @property
    def covid19_obligations(self) -> Decimal | None:
        """COVID-19 related obligations amount.

        Returns:
            Optional[Decimal]: The COVID-19 obligations amount, or None when the
            award reports none. A reported zero returns ``Decimal("0.00")``.
        """
        return to_decimal(self._lazy_get("covid19_obligations", "COVID-19 Obligations"))

    @property
    def covid19_outlays(self) -> Decimal | None:
        """COVID-19 related outlays amount.

        Returns:
            Optional[Decimal]: The COVID-19 outlays amount, or None when the
            award reports none. A reported zero returns ``Decimal("0.00")``.
        """
        return to_decimal(self._lazy_get("covid19_outlays", "COVID-19 Outlays"))

    @property
    def infrastructure_obligations(self) -> Decimal | None:
        """Infrastructure related obligations amount.

        Returns:
            Optional[Decimal]: The infrastructure obligations amount, or None
            when the award reports none. A reported zero returns
            ``Decimal("0.00")``.
        """
        return to_decimal(
            self._lazy_get("infrastructure_obligations", "Infrastructure Obligations")
        )

    @property
    def infrastructure_outlays(self) -> Decimal | None:
        """Infrastructure related outlays amount.

        Returns:
            Optional[Decimal]: The infrastructure outlays amount, or None when
            the award reports none. A reported zero returns ``Decimal("0.00")``.
        """
        return to_decimal(self._lazy_get("infrastructure_outlays", "Infrastructure Outlays"))

    # Helper properties. These often map to field names returned by
    # the spending_by_award/Award Search results, or provide general access methods
    # that are common across award types.

    @property
    def award_amount(self) -> Decimal | None:
        """General helper for total obligated or loaned amount.

        Returns:
            Optional[Decimal]: The total award amount, or None when the award
            reports none. A reported zero returns ``Decimal("0.00")``.
        """
        return to_decimal(
            self._lazy_get("Award Amount", "Loan Amount", "total_obligation", "total_funding")
        )

    @property
    def start_date(self) -> date | None:
        """Award start date from period of performance or obligation data.

        Returns:
            Optional[date]: The award start date, or None if not available.
        """
        start_date = self.get_value(
            ["Start Date", "Base Obligation Date", "Period of Performance Start Date"]
        )
        if not start_date and self.period_of_performance and self.period_of_performance.start_date:
            start_date = self.period_of_performance.start_date
        return to_date(start_date)

    @property
    def end_date(self) -> date | None:
        """Award end date from period of performance data.

        Returns:
            Optional[date]: The award end date, or None if not available.
        """
        end_date = self.get_value(["End Date", "Period of Performance End Date"])
        if not end_date and self.period_of_performance and self.period_of_performance.end_date:
            end_date = self.period_of_performance.end_date
        return to_date(end_date)

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
    def period_of_performance(self) -> PeriodOfPerformance | None:
        """Award period of performance dates.

        Returns:
            Optional[PeriodOfPerformance]: Period of performance object with start/end dates, or None.
        """
        if "period_of_performance" in self.raw and isinstance(
            self.raw.get("period_of_performance"), dict
        ):
            return PeriodOfPerformance(self.raw.get("period_of_performance"))

        # Award search results return Period of Performance information in a flat structure
        # We need to assign these values to a PeriodOfPerformance object
        # to maintain consistency.
        date_keys = ["Start Date", "End Date", "Last Modified Date"]
        if any(k in self._data for k in date_keys):
            return PeriodOfPerformance(
                {
                    "start_date": self.get_value(
                        [
                            "Start Date",
                            "Base Obligation Date",
                            "Period of Performance Start Date",
                        ]
                    ),
                    "end_date": self.get_value(
                        ["End Date", "Period of Performance Current End Date"]
                    ),
                    "last_modified_date": self.get_value("Last Modified Date"),
                }
            )

        # If no data, trigger fetch
        self._ensure_details()
        return PeriodOfPerformance(self.get_value("period_of_performance"))

    @cached_property
    def place_of_performance(self) -> Location | None:
        """Award place of performance location.

        Returns:
            Optional[Location]: Location object for where work is performed, or None.
        """
        data = self._lazy_get("place_of_performance", "Primary Place of Performance", default=None)
        if not isinstance(data, dict) or not data:
            return None

        # Check if all values in the dict are None/null (common for IDV awards)
        if all(v is None for v in data.values()):
            return None

        return Location(data)

    @cached_property
    def recipient(self) -> Recipient | None:
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
            if "Recipient Location" in self._data and isinstance(
                self._data["Recipient Location"], dict
            ):
                recipient.location = Location(self._data["Recipient Location"])
            return recipient

        # If no recipient data is available locally, trigger a fetch
        self._ensure_details()
        if "recipient" in self._data and isinstance(self._data["recipient"], dict):
            return Recipient(self._data["recipient"], self._client)

        return None

    def _load_agency_data(self, agency_type: str) -> dict[str, Any] | None:
        """Load agency data from either nested or flat structure.

        Args:
            agency_type: Either "funding" or "awarding".

        Returns:
            Optional[Dict[str, Any]]: Processed agency data dict, or None when
            the award reports no agency record. Never returns a non-dict: the
            IDV child-awards endpoint reuses the nested key for a bare agency
            name string, which cannot be built into an agency.

        Raises:
            ValidationError: If agency_type is not "funding" or "awarding".
        """
        if agency_type not in ["funding", "awarding"]:
            raise ValidationError(
                f"Invalid agency_type: {agency_type}. Must be 'funding' or 'awarding'."
            )

        # Detail responses nest the agency under a snake_case key, while search
        # results flatten it into Title Case columns that differ only by this
        # prefix, so both key sets derive from agency_type.
        prefix = agency_type.capitalize()
        nested_key = f"{agency_type}_agency"
        name_key = f"{prefix} Agency"
        code_key = f"{prefix} Agency Code"
        sub_name_key = f"{prefix} Sub Agency"
        sub_code_key = f"{prefix} Sub Agency Code"
        flat_keys = [name_key, code_key, sub_name_key, sub_code_key]

        # Nested agency data, from full award details. Only a dict is an agency
        # record; /idvs/awards/ puts a plain agency-name string under this same
        # key, so accepting anything truthy would hand a str to the builders.
        nested = self.raw.get(nested_key)
        if isinstance(nested, dict) and nested:
            return nested

        # Then check for flat agency fields (from search results)
        if any(key in self.raw for key in flat_keys):
            return {
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
                # spending_by_award results carry an awarding_agency_id but no
                # funding equivalent.
                "id": self.raw.get(f"{agency_type}_agency_id"),
                "has_agency_page": False,  # Not available in search results
                "office_agency_name": None,  # Not available in search results
            }

        # Finally try lazy loading. This cannot fetch past a key that is already
        # present, so re-check the type rather than trusting the fetch.
        fetched = self._lazy_get(nested_key)
        return fetched if isinstance(fetched, dict) else None

    def _build_agency(self, agency_type: str) -> Agency | None:
        """Build the toptier Agency for one side of the award.

        Args:
            agency_type: Either "funding" or "awarding".

        Returns:
            Optional[Agency]: The agency, or None when the award reports none.
        """
        data = self._load_agency_data(agency_type)

        if not data:
            return None

        # Merge the toptier fields (name, code, abbreviation, slug) up alongside
        # the agency-level ones, which is the shape the Agency model expects.
        agency_data = {
            "agency_id": data.get("id"),
            "has_agency_page": data.get("has_agency_page"),
            "office_agency_name": data.get("office_agency_name"),
            **data.get("toptier_agency", {}),
        }

        return Agency(agency_data, self._client)

    def _build_subtier_agency(self, agency_type: str) -> SubTierAgency | None:
        """Build the SubTierAgency for one side of the award.

        Args:
            agency_type: Either "funding" or "awarding".

        Returns:
            Optional[SubTierAgency]: The subtier agency, or None when the award
            reports none.
        """
        data = self._load_agency_data(agency_type)

        if not data:
            return None

        subtier_data = data.get("subtier_agency")
        if not subtier_data:
            return None

        # The office name lives at the agency level, but belongs to the subtier.
        subtier_data = subtier_data.copy()
        office_name = data.get("office_agency_name")
        if office_name:
            subtier_data["office_agency_name"] = office_name

        return SubTierAgency(subtier_data, self._client)

    @cached_property
    def funding_agency(self) -> Agency | None:
        """Funding agency information.

        Returns:
            Optional[Agency]: Agency object for the funding agency, or None.
        """
        return self._build_agency("funding")

    @cached_property
    def awarding_agency(self) -> Agency | None:
        """Awarding agency information.

        Returns:
            Optional[Agency]: Agency object for the awarding agency, or None.
        """
        return self._build_agency("awarding")

    @cached_property
    def funding_subtier_agency(self) -> SubTierAgency | None:
        """Funding subtier agency information.

        Returns:
            Optional[SubTierAgency]: SubTierAgency object for the funding subtier, or None.
        """
        return self._build_subtier_agency("funding")

    @cached_property
    def awarding_subtier_agency(self) -> SubTierAgency | None:
        """Awarding subtier agency information.

        Returns:
            Optional[SubTierAgency]: SubTierAgency object for the awarding subtier, or None.
        """
        return self._build_subtier_agency("awarding")

    @property
    def transactions(self) -> TransactionsSearch:
        """Get transactions query builder for this award.

        Returns a TransactionsSearch object that can be further filtered and chained.

        Examples:
            >>> award.transactions.count()  # Get count without loading all data
            >>> award.transactions.limit(10).all()  # Get first 10 transactions
            >>> list(award.transactions)  # Iterate through all transactions

        Returns:
            TransactionsSearch: The query builder for transactions.
        """
        return self._client.transactions.award_id(self.generated_unique_award_id)

    @property
    def funding(self) -> FundingSearch:
        """Get funding query builder for this award.

        Returns a FundingSearch object that can be further filtered and chained.

        Examples:
            >>> award.funding.count()  # Get count without loading all data
            >>> award.funding.order_by(
            ...     "fiscal_date", "asc"
            ... ).all()  # Get all funding records sorted by date
            >>> list(award.funding.limit(10))  # Iterate through first 10 funding records

        Returns:
            FundingSearch: The query builder for funding.
        """
        return self._client.funding.award_id(self.generated_unique_award_id)

    @property
    def accounts(self) -> AwardAccountsQuery:
        """Get accounts query builder for this award.

        Returns an AwardAccountsQuery object for federal accounts
        associated with this award's funding.

        Examples:
            >>> award.accounts.count()  # Get count without loading all data
            >>> list(award.accounts)  # Iterate through all accounts
            >>> award.accounts.order_by("amount", "desc").all()  # Sort by amount

        Returns:
            AwardAccountsQuery: The query builder for accounts.
        """
        return self._client.award_accounts.award_id(self.generated_unique_award_id)

    @property
    def subawards(self) -> SubAwardsSearch:
        """Get subawards query builder for this award.

        Returns:
            SubAwardsSearch: Query builder object for subawards (implemented in subclasses).

        Raises:
            NotImplementedError: If not implemented in the subclass.
        """
        raise NotImplementedError()

    # Downloading detailed award data
    @property
    def download_type(self) -> AwardType:
        """Type required by the download API.

        Returns:
            AwardType: Download type ('contract', 'assistance', or 'idv').

        Raises:
            NotImplementedError: If download is not supported for this award type.
        """
        if self._download_type is None:
            raise NotImplementedError(
                f"Download not supported for {self.__class__.__name__}. "
                "Only Contract, Grant, and IDV awards support bulk downloads."
            )
        if self._download_type not in DOWNLOAD_TYPES:
            # Guards the name-based dispatch in download(): DownloadResource has
            # other public methods, so an unrecognized type must not reach it.
            raise NotImplementedError(
                f"{self.__class__.__name__} declares unknown download type "
                f"{self._download_type!r}. Expected one of {sorted(DOWNLOAD_TYPES)}."
            )
        return self._download_type

    def download(
        self, file_format: FileFormat = "csv", destination_dir: str | None = None
    ) -> DownloadJob:
        """Queue a download job for this award's detailed data.

        This utilizes the USASpending bulk download API, which queues the request
        and processes it asynchronously.

        Args:
            file_format: The format of the file(s) in the zip file containing the data.
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            DownloadJob: A DownloadJob object. Use job.wait_for_completion() to block until finished.

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
            raise ValidationError(
                "Cannot download award data without a 'generated_unique_award_id'. Ensure the award object is fully loaded."
            )

        # Each download type names the DownloadResource method that queues it, so
        # no dispatch table is needed. download_type validates against
        # DOWNLOAD_TYPES first, so the attribute is guaranteed to exist.
        download_type = self.download_type
        queue_download = getattr(self._client.downloads, download_type)

        return queue_download(award_id, file_format, destination_dir)

    def __repr__(self) -> str:
        """String representation of Award.

        Returns:
            str: Formatted string showing award ID and recipient name.
        """
        recipient_name = self.recipient.name if self.recipient else "?"
        award_id = self.award_identifier or self.generated_unique_award_id or "?"
        return f"<Award {award_id} → {recipient_name}>"
