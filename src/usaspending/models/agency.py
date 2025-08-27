"""Agency model for USASpending data."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
from functools import cached_property
from ..utils.formatter import to_float, to_int
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
        """Fetch award summary data from the API.
        
        Args:
            award_type_codes: Optional list of award type codes to filter
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            
        Returns:
            Award summary data dict or None if unable to fetch
        """
        # Get toptier code
        toptier_code = self.code
        if not toptier_code:
            return None
        
        # Use self.fiscal_year as default if no fiscal_year parameter provided
        if fiscal_year is None:
            fiscal_year = self.fiscal_year  # Will be None if not set
        
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
            logger.debug(
                f"Could not fetch award summary for {toptier_code}: {e}"
            )
            return None

    @property
    def has_agency_page(self) -> bool:
        """Whether this agency has a dedicated page on USASpending.gov."""
        return bool(self._lazy_get("has_agency_page", default=False))

    @property
    def office_agency_name(self) -> Optional[str]:
        """Name of the specific office within the agency."""
        return self._lazy_get("office_agency_name")

    @property
    def name(self) -> Optional[str]:
        """Primary agency name."""
        # Agency now contains toptier data directly
        return self._lazy_get("name")

    @property
    def code(self) -> Optional[str]:
        """Primary agency code."""
        # Agency now contains toptier data directly
        code = self.get_value("code")
        if not code:
            code = self.toptier_code
        return code

    @property
    def abbreviation(self) -> Optional[str]:
        """Primary agency abbreviation."""
        # Agency now contains toptier data directly
        return self._lazy_get("abbreviation")

    @property
    def slug(self) -> Optional[str]:
        """URL slug for this agency."""
        return self._lazy_get("slug")

    @property
    def total_obligations(self) -> Optional[float]:
        """Total obligations for this agency across all awards."""
        obligations = self.get_value("total_obligations","obligations")
        return to_float(obligations)
    
    @property
    def awards(self) -> "AwardsSearch":
        """Get an AwardsSearch instance pre-filtered to this agency.
        
        Returns:
            AwardsSearch instance
        """
        from ..queries.filters import AgencyTier, AgencyType
        return self._client.awards.search().for_agency(self.name,AgencyType.AWARDING,AgencyTier.TOPTIER)
    
    def obligations(
        self,
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding",
        award_type_codes: Optional[List[str]] = None
    ) -> Optional[float]:
        """Get obligations for this agency, optionally filtered.
        
        Args:
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            award_type_codes: Optional list of award type codes to filter
            
        Returns:
            Obligations amount or None if unavailable
        """
        # If no filters and we have existing data, return it
        if not any([fiscal_year, award_type_codes]) and agency_type == "awarding":
            existing = self.get_value("total_obligations", "obligations")
            if existing is not None:
                return to_float(existing)
        
        # Fetch from award summary API
        summary = self._get_award_summary(
            award_type_codes=award_type_codes,
            fiscal_year=fiscal_year,
            agency_type=agency_type
        )
        return to_float(summary.get("obligations")) if summary else None
    
    def contract_obligations(
        self, 
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding"
    ) -> Optional[float]:
        """Get contract obligations for this agency.
        
        Args:
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            
        Returns:
            Contract obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(CONTRACT_CODES),
            fiscal_year=fiscal_year,
            agency_type=agency_type
        )
        return to_float(summary.get("obligations")) if summary else None
    
    def grant_obligations(
        self, 
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding"
    ) -> Optional[float]:
        """Get grant obligations for this agency.
        
        Args:
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            
        Returns:
            Grant obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(GRANT_CODES),
            fiscal_year=fiscal_year,
            agency_type=agency_type
        )
        return to_float(summary.get("obligations")) if summary else None
    
    def idv_obligations(
        self, 
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding"
    ) -> Optional[float]:
        """Get Indefinite Delivery Vehicle (IDV) obligations for this agency.
        
        Args:
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            
        Returns:
            IDV obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(IDV_CODES),
            fiscal_year=fiscal_year,
            agency_type=agency_type
        )
        return to_float(summary.get("obligations")) if summary else None
    
    def loan_obligations(
        self, 
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding"
    ) -> Optional[float]:
        """Get loan obligations for this agency.
        
        Args:
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            
        Returns:
            Loan obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(LOAN_CODES),
            fiscal_year=fiscal_year,
            agency_type=agency_type
        )
        return to_float(summary.get("obligations")) if summary else None
    
    def direct_payment_obligations(
        self, 
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding"
    ) -> Optional[float]:
        """Get direct payment obligations for this agency.
        
        Args:
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            
        Returns:
            Direct payment obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(DIRECT_PAYMENT_CODES),
            fiscal_year=fiscal_year,
            agency_type=agency_type
        )
        return to_float(summary.get("obligations")) if summary else None
    
    def other_obligations(
        self, 
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding"
    ) -> Optional[float]:
        """Get other assistance obligations for this agency.
        
        Args:
            fiscal_year: Override the agency's fiscal year (None uses self.fiscal_year)
            agency_type: "awarding" or "funding"
            
        Returns:
            Other assistance obligations amount or None if unavailable
        """
        summary = self._get_award_summary(
            award_type_codes=list(OTHER_CODES),
            fiscal_year=fiscal_year,
            agency_type=agency_type
        )
        return to_float(summary.get("obligations")) if summary else None
    
    def transaction_count(
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
    
    def new_award_count(self) -> Optional[int]:
        """Total new award count for this agency across all awards."""
        count = self._lazy_get("new_award_count")
        return to_int(count)
    
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
    def agency_id(self) -> Optional[int]:
        """Agency ID from the full API response."""
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
    
    def __repr__(self) -> str:
        """String representation of Agency."""
        name = self.name or "?"
        code = self.code or "?"
        return f"<Agency {code}: {name}>"


