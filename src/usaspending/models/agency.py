"""Agency model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
from ..utils.formatter import to_float, to_int, to_date
from datetime import date
from functools import cached_property
from .lazy_record import LazyRecord
from ..logging_config import USASpendingLogger
from ..config import (
    CONTRACT_CODES,
    GRANT_CODES,
    IDV_CODES,
    LOAN_CODES,
    DIRECT_PAYMENT_CODES,
    OTHER_CODES
)

if TYPE_CHECKING:
    from ..client import USASpending
    from ..queries.awards_search import AwardsSearch
    from .subtier_agency import SubTierAgency

logger = USASpendingLogger.get_logger(__name__)

# Create data class for def_codes
@dataclass
class DefCode:
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

    def __init__(self, data: Dict[str, Any], client: USASpending, subtier_data: Optional[Dict[str, Any]] = None):
        """Initialize Agency instance.

        Args:
            data: Toptier agency data merged with top-level agency fields
            client: USASpending client instance
            subtier_data: Optional subtier agency data for subtier_agency property
        """
        super().__init__(data, client)
        
        # Store subtier data separately
        self._subtier_data = subtier_data


    def _fetch_details(self) -> Optional[Dict[str, Any]]:
        """Fetch full agency details if we have a toptier_code and client.
        
        Returns:
            Full agency data from the API, or None if unable to fetch
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
        agency_type: str = "awarding"
    ) -> Optional[Dict[str, Any]]:
        """Fetch award summary data for a given agency code
        
        Args:
            award_type_codes: Optional list of award type codes to filter
            fiscal_year: If none, defaults to the current fiscal year
            agency_type: "awarding" or "funding"
            
        Returns:
            Award summary data dict or None if unable to fetch
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
                award_type_codes=award_type_codes
            )
        except Exception as e:
            logger.error(
                f"Could not fetch award summary for {toptier_code}: {e}"
            )
            return {}

    # Properties from full agency API endpoint
    
    @property
    def fiscal_year(self) -> Optional[int]:
        """Fiscal year for the agency data."""
        fiscal_year = self._lazy_get("fiscal_year")
        return to_int(fiscal_year)
    
    @property
    def toptier_code(self) -> Optional[str]:
        """Agency toptier code (3-4 digit string)."""
        return self._lazy_get("toptier_code")

    @property
    def code(self) -> Optional[str]:
        """Treasury agency code."""
        code = self.get_value("code") or self.toptier_code
        return code

    @property
    def name(self) -> Optional[str]:
        """Primary agency name."""
        # Agency now contains toptier data directly
        return self._lazy_get("name")
    
    @property
    def abbreviation(self) -> Optional[str]:
        """Primary agency abbreviation."""
        # Agency now contains toptier data directly
        return self._lazy_get("abbreviation")

    @property
    def id(self):
        """Internal identifier from USASpending.gov """
        return self.agency_id
    
    @property
    def agency_id(self) -> Optional[int]:
        """Internal identifier from USASpending.gov"""
        agency_id = self._lazy_get("agency_id","id")
        return to_int(agency_id)

    @property
    def icon_filename(self) -> Optional[str]:
        """Filename of the agency's icon/logo."""
        return self._lazy_get("icon_filename")
    
    @property
    def mission(self) -> Optional[str]:
        """Agency mission statement."""
        return self._lazy_get("mission")
    
    @property
    def website(self) -> Optional[str]:
        """Agency website URL."""
        return self._lazy_get("website")
    
    @property
    def congressional_justification_url(self) -> Optional[str]:
        """URL to the agency's congressional justification."""
        return self._lazy_get("congressional_justification_url")
    
    @property
    def about_agency_data(self) -> Optional[str]:
        """Additional information about the agency's data."""
        return self._lazy_get("about_agency_data")
    
    @property
    def subtier_agency_count(self) -> Optional[int]:
        """Number of subtier agencies under this agency."""
        count = self._lazy_get("subtier_agency_count")
        return to_int(count)

    @property
    def messages(self) -> List[str]:
        """API messages related to this agency data."""
        messages = self._lazy_get("messages", default=[])
        if not isinstance(messages, list):
            return []
        return messages
    
    @property
    def def_codes(self) -> List[DefCode]:
        """List of Disaster Emergency Fund Codes (DEFC) for this agency.
        
        Returns:
            List of DefCode dataclass instances
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
                    disaster=code_data.get("disaster")
                )
                result.append(def_code)
        
        return result

    # Properties derived or related to the agency record
    # These properties are not included in the agency detail API endpoint
    # (generally, they come from a related agency properties in an award)
    # so they cannot be lazy-loaded.
    
    @property
    def has_agency_page(self) -> bool:
        """Whether this agency has a dedicated page on USASpending.gov."""
        return bool(self.get_value(["has_agency_page"], default=False))

    @property
    def office_agency_name(self) -> Optional[str]:
        """Name of the specific office within the agency."""
        return self.get_value("office_agency_name")
    
    @property
    def slug(self) -> Optional[str]:
        """URL slug for this agency."""
        return self.get_value("slug")

    @property
    def obligations(self) -> Optional[float]:
        """ Return current fiscal year's total obligations """
        return self.total_obligations
    
    # Related and derived resources.
    # Some of these properties are provided by search query
    # results, others are helper methods that provide quick access
    # to related award and transaction data.

    @cached_property
    def total_obligations(self) -> Optional[float]:
        """ Return current fiscal year's total obligations """
        obligations = self.get_value(["total_obligations","obligations"])
        if not obligations:
            # If not present, fetch from award summary
            obligations = self.get_obligations()
        return obligations
    
    @cached_property
    def latest_action_date(self) -> Optional[date]:
        """Date of the most recent action for this agency's awards."""
        
        # Check if value is present already (often provided in search results)
        latest_action_date_string = self.get_value("latest_action_date")
        
        # If not, fetch from agency award summary endpoint
        if not latest_action_date_string:
            summary = self._get_award_summary()
            latest_action_date_string = summary.get("latest_action_date")
        
        return to_date(latest_action_date_string)
    
    @cached_property
    def transaction_count(self) -> Optional[int]:
        """Total transaction count for this agency across all awards."""
        
        # Check if value is present already (often provided in search results)
        transaction_count = self.get_value("transaction_count")
        
        # If not, fetch from agency award summary endpoint
        if not transaction_count:    
            transaction_count = self.get_transaction_count()
        
        return to_int(transaction_count)
    
    @property
    def awards(self) -> "AwardsSearch":
        """Get an AwardsSearch instance pre-filtered to the current agency as a top-tier "Awarding" agency.
        
        Returns:
            AwardsSearch instance
        """
        from ..queries.filters import AgencyTier, AgencyType
        return self._client.awards.search().for_agency(self.name,AgencyType.AWARDING,AgencyTier.TOPTIER)
    
    @property
    def subagencies(self) -> List["SubTierAgency"]:
        """Get list of sub-agencies for this agency.
        
        Returns:
            List of SubTierAgency instances
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
                limit=100  # Default to maximum
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
            logger.debug(
                f"Could not fetch sub-agencies for {toptier_code}: {e}"
            )
            return []
    
    def get_obligations(
        self,
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding",
        award_type_codes: Optional[List[str]] = None
    ) -> Optional[float]:
        """Get obligations for this agency, optionally filtered.
        
        Args:
            fiscal_year: Return obligation totals for a given fiscal year (defaults to current FY)
            agency_type: "awarding" or "funding"
            award_type_codes: Optional list of award type codes to filter
            
        Returns:
            Obligations amount or None if unavailable
        """
        
        # Fetch from award summary API
        summary = self._get_award_summary(
            award_type_codes=award_type_codes,
            fiscal_year=fiscal_year,
            agency_type=agency_type
        )
        return to_float(summary.get("obligations")) if summary else None
    
    @cached_property
    def contract_obligations(self) -> Optional[float]:
        """Get contract obligations for this agency.
            
        Returns:
            Contract obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(CONTRACT_CODES)
        )
        return to_float(summary.get("obligations")) if summary else None

    @cached_property    
    def grant_obligations(self) -> Optional[float]:
        """Get grant obligations for this agency in the current fiscal year.
            
        Returns:
            Grant obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(GRANT_CODES)
        )
        return to_float(summary.get("obligations")) if summary else None
    
    @cached_property
    def idv_obligations(self) -> Optional[float]:
        """Get Indefinite Delivery Vehicle (IDV) obligations for this agency in the current fiscal year.
        
        Returns:
            IDV obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(IDV_CODES)
        )
        return to_float(summary.get("obligations")) if summary else None
    
    @cached_property
    def loan_obligations(self) -> Optional[float]:
        """Get loan obligations for this agency for the current fiscal year

        Returns:
            Loan obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(LOAN_CODES)
        )
        return to_float(summary.get("obligations")) if summary else None
    
    @cached_property
    def direct_payment_obligations(self) -> Optional[float]:
        """Get direct payment obligations for this agency for the current fiscal year.
            
        Returns:
            Direct payment obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(DIRECT_PAYMENT_CODES)
        )
        return to_float(summary.get("obligations")) if summary else None
    
    @cached_property
    def other_obligations(self) -> Optional[float]:
        """Get other assistance obligations for this agency.
 
        Returns:
            Other assistance obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(OTHER_CODES)
        )
        return to_float(summary.get("obligations")) if summary else None
    
    def get_transaction_count(
        self,
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding",
        award_type_codes: Optional[List[str]] = None
    ) -> Optional[int]:
        """Get transaction count for this agency, optionally filtered.
        
        Args:
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            award_type_codes: Optional list of award type codes to filter
            
        Returns:
            Transaction count or None if unavailable
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
            agency_type=agency_type
        )
        return to_int(summary.get("transaction_count")) if summary else None
    
    def __repr__(self) -> str:
        """String representation of Agency."""
        name = self.name or "?"
        code = self.code or "?"
        return f"<Agency {code}: {name}>"