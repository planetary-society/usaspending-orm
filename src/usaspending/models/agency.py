"""Agency model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
from decimal import Decimal
from ..utils.formatter import to_decimal, to_int, to_date
from datetime import date
from functools import cached_property
from .lazy_record import LazyRecord
from ..logging_config import USASpendingLogger
from .award_types import (
    CONTRACT_CODES,
    GRANT_CODES,
    IDV_CODES,
    LOAN_CODES,
    DIRECT_PAYMENT_CODES,
    OTHER_CODES,
)

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..queries.awards_search import AwardsSearch
    from .subtier_agency import SubTierAgency

logger = USASpendingLogger.get_logger(__name__)


# Create data class for def_codes
@dataclass
class DefCode:
    """Disaster Emergency Fund Code (DEFC) data structure.

    Represents a disaster emergency fund code associated with an agency,
    containing legislative and reference information.

    Attributes:
        code: The DEFC code identifier.
        public_law: Associated public law reference.
        title: Optional descriptive title of the fund.
        urls: Optional list of related URLs for additional information.
        disaster: Optional disaster category or description.
    """

    code: str
    public_law: str
    title: Optional[str] = None
    urls: Optional[List[str]] = None
    disaster: Optional[str] = None


class Agency(LazyRecord):
    """Rich wrapper around a USAspending toptier agency record.

    This model represents a toptier agency with its essential properties.
    For subtier agency information, use the SubTierAgency model separately.
    """

    def __init__(
        self,
        data: Dict[str, Any],
        client: USASpendingClient,
        subtier_data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Agency instance.

        Args:
            data: Toptier agency data merged with top-level agency fields
            client: USASpendingClient client instance
            subtier_data: Optional subtier agency data for subtier_agency property
        """
        # Use the base validation method (dict-only)
        raw = self.validate_init_data(data, "Agency", allow_string_id=False)
        super().__init__(raw, client)

        # Store subtier data separately
        self._subtier_data = subtier_data

    def _fetch_details(self) -> Optional[Dict[str, Any]]:
        """Fetch full agency details if we have a toptier_code and client.

        Returns:
            Optional[Dict[str, Any]]: Full agency data from the API, or None
                if unable to fetch due to missing toptier_code or API error.
        """
        # Try to get toptier_code from existing data
        toptier_code = None
        if "toptier_code" in self._data:
            toptier_code = self._data["toptier_code"]
        elif "code" in self._data:
            toptier_code = self._data["code"]

        try:
            # Fetch full agency details using the toptier_code
            from ..queries.agency_query import AgencyQuery

            query = AgencyQuery(self._client)

            # Get fiscal_year if available in current data
            fiscal_year = self._data.get("fiscal_year")
            full_agency = query._get_resource_with_params(toptier_code, fiscal_year)

            return full_agency
        except Exception as e:
            # Log but don't raise - lazy loading should fail gracefully
            logger.debug(f"Could not fetch agency details for {toptier_code}: {e}")
            return None

    def _get_award_summary(
        self,
        award_type_codes: Optional[List[str]] = None,
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding",
    ) -> Optional[Dict[str, Any]]:
        """Fetch award summary data for a given agency code.

        Args:
            award_type_codes (Optional[List[str]]): Optional list of award type codes
                to filter by. If None, includes all award types.
            fiscal_year (Optional[int]): Fiscal year to filter by. If None,
                defaults to the current fiscal year.
            agency_type (str): Type of agency relationship to filter by.
                Must be "awarding" or "funding". Defaults to "awarding".

        Returns:
            Optional[Dict[str, Any]]: Award summary data dictionary containing
                obligations, transaction counts, and other summary metrics,
                or None if unable to fetch due to missing agency code or API error.
        """
        # Get toptier code
        toptier_code = self.code
        if not toptier_code:
            logger.error("Cannot fetch agency award summaries without agency code.")
            return None

        try:
            from ..queries.agency_award_summary import AgencyAwardSummary

            query = AgencyAwardSummary(self._client)

            return query.get_awards_summary(
                toptier_code=toptier_code,
                fiscal_year=fiscal_year,
                agency_type=agency_type,
                award_type_codes=award_type_codes,
            )
        except Exception as e:
            logger.error(f"Could not fetch award summary for {toptier_code}: {e}")
            return {}

    # Properties from full agency API endpoint

    @property
    def fiscal_year(self) -> Optional[int]:
        """Fiscal year for the agency data.

        Returns:
            Optional[int]: The fiscal year for this agency's data,
                or None if not available.
        """
        fiscal_year = self._lazy_get("fiscal_year")
        return to_int(fiscal_year)

    @property
    def toptier_code(self) -> Optional[str]:
        """Agency toptier code (3-4 digit string).

        This is the Treasury Account Fund Symbol (TAFS) used to identify
        the agency at the top-tier level in the government hierarchy.

        Returns:
            Optional[str]: The toptier agency code, or None if not available.
        """
        return self._lazy_get("toptier_code", "code")

    @property
    def code(self) -> Optional[str]:
        """Alias for toptier_code property.

        Returns:
            Optional[str]: The toptier agency code, or None if not available.
        """
        return self.toptier_code

    @property
    def name(self) -> Optional[str]:
        """Primary agency name.

        Returns:
            Optional[str]: The official name of the agency,
                or None if not available.
        """
        # Agency now contains toptier data directly
        return self._lazy_get("name")

    @property
    def abbreviation(self) -> Optional[str]:
        """Primary agency abbreviation.

        Returns:
            Optional[str]: The official abbreviation of the agency,
                or None if not available.
        """
        # Agency now contains toptier data directly
        return self._lazy_get("abbreviation")

    @property
    def id(self):
        """Internal identifier from USASpending.gov.

        Returns:
            Optional[int]: The internal agency identifier,
                or None if not available.
        """
        return self.agency_id

    @property
    def agency_id(self) -> Optional[int]:
        """Internal identifier from USASpending.gov.

        Returns:
            Optional[int]: The internal agency identifier used by the API,
                or None if not available.
        """
        agency_id = self._lazy_get("agency_id", "id")
        return to_int(agency_id)

    @property
    def icon_filename(self) -> Optional[str]:
        """Filename of the agency's icon/logo.

        Returns:
            Optional[str]: The filename of the agency's icon or logo image,
                or None if not available.
        """
        return self._lazy_get("icon_filename")

    @property
    def mission(self) -> Optional[str]:
        """Agency mission statement.

        Returns:
            Optional[str]: The official mission statement of the agency,
                or None if not available.
        """
        return self._lazy_get("mission")

    @property
    def website(self) -> Optional[str]:
        """Agency website URL.

        Returns:
            Optional[str]: The official website URL of the agency,
                or None if not available.
        """
        return self._lazy_get("website")

    @property
    def congressional_justification_url(self) -> Optional[str]:
        """URL to the agency's congressional justification.

        Returns:
            Optional[str]: The URL to the agency's congressional justification document,
                or None if not available.
        """
        return self._lazy_get("congressional_justification_url")

    @property
    def about_agency_data(self) -> Optional[str]:
        """Additional information about the agency's data.

        Returns:
            Optional[str]: Descriptive text about the agency's data quality,
                coverage, or other relevant information, or None if not available.
        """
        return self._lazy_get("about_agency_data")

    @property
    def subtier_agency_count(self) -> Optional[int]:
        """Number of subtier agencies under this agency.

        Returns:
            Optional[int]: The total count of subtier agencies that report
                to this toptier agency, or None if not available.
        """
        count = self._lazy_get("subtier_agency_count")
        return to_int(count)

    @property
    def messages(self) -> List[str]:
        """API messages related to this agency data.

        Returns:
            List[str]: List of informational messages from the API
                related to this agency's data. Empty list if no messages.
        """
        messages = self._lazy_get("messages", default=[])
        if not isinstance(messages, list):
            return []
        return messages

    @property
    def def_codes(self) -> List[DefCode]:
        """List of Disaster Emergency Fund Codes (DEFC) for this agency.

        Returns:
            List[DefCode]: List of DefCode dataclass instances containing
                disaster emergency fund codes associated with this agency.
                Empty list if no DEFCs are available.
        """
        def_codes_data = self._lazy_get("def_codes", default=[])
        if not isinstance(def_codes_data, list):
            return []

        result = []
        for code_data in def_codes_data:
            if isinstance(code_data, dict):
                # Handle the case where urls might be a string or list
                urls = code_data.get("urls")
                if isinstance(urls, str):
                    urls = [urls] if urls else None
                elif urls and not isinstance(urls, list):
                    urls = None

                def_code = DefCode(
                    code=code_data.get("code", ""),
                    public_law=code_data.get("public_law", ""),
                    title=code_data.get("title"),
                    urls=urls,
                    disaster=code_data.get("disaster"),
                )
                result.append(def_code)

        return result

    # Properties derived or related to the agency record
    # These properties are not included in the agency detail API endpoint
    # (generally, they come from a related agency properties in an award)
    # so they cannot be lazy-loaded.

    @property
    def has_agency_page(self) -> bool:
        """Whether this agency has a dedicated page on USASpending.gov.

        Returns:
            bool: True if the agency has a dedicated profile page on USASpending.gov,
                False otherwise.
        """
        return bool(self.get_value(["has_agency_page"], default=False))

    @property
    def office_agency_name(self) -> Optional[str]:
        """Name of the specific office within the agency.

        Returns:
            Optional[str]: The name of a specific office or division within
                the agency, or None if not available.
        """
        return self.get_value("office_agency_name")

    @property
    def slug(self) -> Optional[str]:
        """URL slug for this agency.

        Returns:
            Optional[str]: The URL-friendly slug identifier used in
                USASpending.gov URLs for this agency, or None if not available.
        """
        return self.get_value("slug")

    @property
    def obligations(self) -> Optional[Decimal]:
        """Alias for total_obligations property.

        Returns:
            Optional[Decimal]: The current fiscal year's total obligations
                for this agency, or None if not available.
        """
        return self.total_obligations

    # Related and derived resources.
    # Some of these properties are provided by search query
    # results, others are helper methods that provide quick access
    # to related award and transaction data.

    @cached_property
    def total_obligations(self) -> Optional[Decimal]:
        """Current fiscal year's total obligations made by this agency.

        Returns:
            Optional[Decimal]: The total dollar amount of obligations
                for the current fiscal year, or None if not available.
        """
        obligations = self.get_value(["total_obligations", "obligations"])
        if not obligations:
            # If not present, fetch from award summary
            obligations = self.get_obligations()
        return obligations

    @cached_property
    def latest_action_date(self) -> Optional[date]:
        """Date of the most recent action for this agency's awards.

        Returns:
            Optional[date]: The date of the most recent award action
                associated with this agency, or None if not available.
        """

        # Check if value is present already (often provided in search results)
        latest_action_date_string = self.get_value("latest_action_date")

        # If not, fetch from agency award summary endpoint
        if not latest_action_date_string:
            summary = self._get_award_summary()
            latest_action_date_string = summary.get("latest_action_date")

        return to_date(latest_action_date_string)

    @cached_property
    def transaction_count(self) -> Optional[int]:
        """Total transaction count for this agency across all awards.

        Returns:
            Optional[int]: The total number of transactions associated
                with all awards for this agency, or None if not available.
        """

        # Check if value is present already (often provided in search results)
        transaction_count = self.get_value("transaction_count")

        # If not, fetch from agency award summary endpoint
        if not transaction_count:
            transaction_count = self.get_transaction_count()

        return to_int(transaction_count)

    @property
    def awards(self) -> "AwardsSearch":
        """Get an AwardsSearch instance pre-filtered to this agency as awarding agency.

        Returns:
            AwardsSearch: A query builder instance pre-filtered to show awards
                where this agency is the top-tier awarding agency. Use this to
                search and filter awards associated with this agency.
        """
        return self._client.awards.search().agency(self.name, "awarding", "toptier")

    @property
    def subagencies(self) -> List["SubTierAgency"]:
        """Get list of subtier agencies under this toptier agency.

        Returns:
            List[SubTierAgency]: List of SubTierAgency model instances
                representing all subtier agencies that report to this
                toptier agency. Returns empty list if no subagencies
                are found or if there's an API error.
        """
        # Get toptier code
        toptier_code = self.code
        if not toptier_code:
            logger.error("Cannot fetch sub-agencies without agency code.")
            return []

        try:
            from ..queries.sub_agency_query import SubAgencyQuery
            from .subtier_agency import SubTierAgency

            query = SubAgencyQuery(self._client)

            # Use fiscal year from this agency if available
            fiscal_year = self.fiscal_year

            response = query.get_subagencies(
                toptier_code=toptier_code,
                fiscal_year=fiscal_year,
                limit=100,  # Default to maximum
            )

            # Transform results into SubTierAgency objects
            subagencies = []
            results = response.get("results", [])
            for result in results:
                if isinstance(result, dict):
                    subagency = SubTierAgency(result, self._client)
                    subagencies.append(subagency)

            return subagencies

        except Exception as e:
            logger.debug(f"Could not fetch sub-agencies for {toptier_code}: {e}")
            return []

    def get_obligations(
        self,
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding",
        award_type_codes: Optional[List[str]] = None,
    ) -> Optional[float]:
        """Get obligations for this agency, optionally filtered.

        Args:
            fiscal_year (Optional[int]): Fiscal year to filter by.
                If None, defaults to the current fiscal year.
            agency_type (str): Type of agency relationship to filter by.
                Must be "awarding" or "funding". Defaults to "awarding".
            award_type_codes (Optional[List[str]]): Optional list of award type codes
                to filter by. If None, includes all award types.

        Returns:
            Optional[float]: Total obligations amount as a float,
                or None if unavailable due to missing data or API error.
        """

        # Fetch from award summary API
        summary = self._get_award_summary(
            award_type_codes=award_type_codes,
            fiscal_year=fiscal_year,
            agency_type=agency_type,
        )
        return to_decimal(summary.get("obligations")) if summary else None

    @cached_property
    def contract_obligations(self) -> Optional[Decimal]:
        """Contract obligations for this agency in the current fiscal year.

        Returns:
            Optional[Decimal]: The total dollar amount of contract obligations
                for this agency, or None if unavailable.
        """
        summary = self._get_award_summary(award_type_codes=list(CONTRACT_CODES))
        return to_decimal(summary.get("obligations")) if summary else None

    @cached_property
    def grant_obligations(self) -> Optional[Decimal]:
        """Grant obligations for this agency in the current fiscal year.

        Returns:
            Optional[Decimal]: The total dollar amount of grant obligations
                for this agency, or None if unavailable.
        """
        summary = self._get_award_summary(award_type_codes=list(GRANT_CODES))
        return to_decimal(summary.get("obligations")) if summary else None

    @cached_property
    def idv_obligations(self) -> Optional[Decimal]:
        """Indefinite Delivery Vehicle (IDV) obligations for this agency.

        Returns:
            Optional[Decimal]: The total dollar amount of IDV obligations
                for this agency in the current fiscal year, or None if unavailable.
        """
        summary = self._get_award_summary(award_type_codes=list(IDV_CODES))
        return to_decimal(summary.get("obligations")) if summary else None

    @cached_property
    def loan_obligations(self) -> Optional[Decimal]:
        """Loan obligations for this agency in the current fiscal year.

        Returns:
            Optional[Decimal]: The total dollar amount of loan obligations
                for this agency, or None if unavailable.
        """
        summary = self._get_award_summary(award_type_codes=list(LOAN_CODES))
        return to_decimal(summary.get("obligations")) if summary else None

    @cached_property
    def direct_payment_obligations(self) -> Optional[Decimal]:
        """Direct payment obligations for this agency in the current fiscal year.

        Returns:
            Optional[Decimal]: The total dollar amount of direct payment obligations
                for this agency, or None if unavailable.
        """
        summary = self._get_award_summary(award_type_codes=list(DIRECT_PAYMENT_CODES))
        return to_decimal(summary.get("obligations")) if summary else None

    @cached_property
    def other_obligations(self) -> Optional[Decimal]:
        """Other assistance obligations for this agency in the current fiscal year.

        Returns:
            Optional[Decimal]: The total dollar amount of other assistance obligations
                for this agency, or None if unavailable.
        """
        summary = self._get_award_summary(award_type_codes=list(OTHER_CODES))
        return to_decimal(summary.get("obligations")) if summary else None

    def get_transaction_count(
        self,
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding",
        award_type_codes: Optional[List[str]] = None,
    ) -> Optional[int]:
        """Get transaction count for this agency, optionally filtered.

        Args:
            fiscal_year (Optional[int]): Fiscal year to filter by.
                If None, uses the agency's fiscal year or current fiscal year.
            agency_type (str): Type of agency relationship to filter by.
                Must be "awarding" or "funding". Defaults to "awarding".
            award_type_codes (Optional[List[str]]): Optional list of award type codes
                to filter by. If None, includes all award types.

        Returns:
            Optional[int]: Total transaction count as an integer,
                or None if unavailable due to missing data or API error.
        """
        # If no filters and we have existing data, return it
        if not any([fiscal_year, award_type_codes]) and agency_type == "awarding":
            existing = self._lazy_get("transaction_count")
            if existing is not None:
                return to_int(existing)

        # Fetch from award summary API
        summary = self._get_award_summary(
            award_type_codes=award_type_codes,
            fiscal_year=fiscal_year,
            agency_type=agency_type,
        )
        return to_int(summary.get("transaction_count")) if summary else None

    def __repr__(self) -> str:
        """String representation of Agency.

        Returns:
            str: A string representation showing the agency code and name
                in the format "<Agency CODE: NAME>".
        """
        name = self.name or "?"
        code = self.code or "?"
        return f"<Agency {code}: {name}>"
