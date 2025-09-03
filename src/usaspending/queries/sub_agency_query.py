"""Sub-agency query implementation for retrieving agency sub-agencies with pagination."""

from typing import TYPE_CHECKING, Optional, Dict, Any, List
from .single_resource_base import SingleResourceBase
from ..exceptions import ValidationError
from ..client import USASpending
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    pass

logger = USASpendingLogger.get_logger(__name__)


class SubAgencyQuery(SingleResourceBase):
    """Retrieve sub-agency data from the USAspending API.
    
    This query class handles fetching sub-agency information including
    transaction counts and obligations filtered by fiscal year, agency type,
    and award type codes.
    """

    def __init__(self, client: USASpending):
        """Initialize SubAgencyQuery with client.
        
        Args:
            client: USASpending client instance
        """
        super().__init__(client)
        logger.debug("SubAgencyQuery initialized with client: %s", client)

    @property
    def _endpoint(self) -> str:
        """Base endpoint for sub-agency retrieval."""
        return '/agency/{toptier_code}/sub_agency/'
    
    def _construct_endpoint(self, resource_id: str) -> str:
        """Construct the full endpoint URL for agency sub-agency.
        
        Args:
            resource_id: The toptier_code for the agency
            
        Returns:
            Full endpoint path including /sub_agency/
        """
        endpoint = self._endpoint.replace("{toptier_code}", resource_id)
        return endpoint

    def find_by_id(self, toptier_code: str) -> Dict[str, Any]:
        """Not used for sub-agency - use get_subagencies instead.
        
        Raises:
            NotImplementedError: This method should not be used directly
        """
        raise NotImplementedError(
            "Use get_subagencies() method instead for sub-agency data"
        )

    def get_subagencies(
        self,
        toptier_code: str,
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding",
        award_type_codes: Optional[List[str]] = None,
        order: str = "desc",
        sort: str = "total_obligations",
        page: int = 1,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Retrieve agency sub-agencies with optional filters and pagination.
        
        Args:
            toptier_code: The toptier code of an agency (3-4 digit string)
            fiscal_year: Optional fiscal year for the data (defaults to current)
            agency_type: "awarding" or "funding" (defaults to "awarding")
            award_type_codes: Optional list of award type codes to filter by
            order: Sort direction "asc" or "desc" (defaults to "desc")
            sort: Sort field - "name", "total_obligations", "transaction_count", "new_award_count"
            page: Page number (defaults to 1)
            limit: Items per page, max 100 (defaults to 100)
            
        Returns:
            Dictionary containing:
                - toptier_code: Agency toptier code
                - fiscal_year: Fiscal year of data
                - page_metadata: Pagination metadata
                - results: List of sub-agency data
                - messages: Any API messages
            
        Raises:
            ValidationError: If toptier_code is invalid or other parameters are invalid
            APIError: If API request fails
        """
        # Validate toptier_code
        if not toptier_code:
            raise ValidationError("toptier_code is required")
        
        toptier_code = str(toptier_code).strip()
        if not toptier_code.isdigit() or len(toptier_code) not in [3, 4]:
            raise ValidationError(
                f"Invalid toptier_code: {toptier_code}. "
                "Must be a 3-4 digit numeric string"
            )
        
        # Validate agency_type
        if agency_type not in ["awarding", "funding"]:
            raise ValidationError(
                f"Invalid agency_type: {agency_type}. "
                "Must be 'awarding' or 'funding'"
            )
        
        # Validate order
        if order not in ["asc", "desc"]:
            raise ValidationError(
                f"Invalid order: {order}. "
                "Must be 'asc' or 'desc'"
            )
        
        # Validate sort
        valid_sorts = ["name", "total_obligations", "transaction_count", "new_award_count"]
        if sort not in valid_sorts:
            raise ValidationError(
                f"Invalid sort: {sort}. "
                f"Must be one of: {', '.join(valid_sorts)}"
            )
        
        # Validate page
        if page < 1:
            raise ValidationError("page must be >= 1")
        
        # Validate limit
        if limit < 1 or limit > 100:
            raise ValidationError("limit must be between 1 and 100")
        
        logger.debug(
            "Fetching sub-agencies for toptier_code: %s, fiscal_year: %s, "
            "agency_type: %s, award_type_codes: %s, order: %s, sort: %s, "
            "page: %s, limit: %s",
            toptier_code, fiscal_year, agency_type, award_type_codes, 
            order, sort, page, limit
        )
        
        # Build params
        params = {
            "agency_type": agency_type,
            "order": order,
            "sort": sort,
            "page": page,
            "limit": limit
        }
        
        if fiscal_year is not None:
            params["fiscal_year"] = fiscal_year
        
        if award_type_codes:
            # Convert to list if needed and filter out None/empty values
            if isinstance(award_type_codes, (set, frozenset)):
                award_type_codes = list(award_type_codes)
            award_type_codes = [code for code in award_type_codes if code]
            
            if award_type_codes:
                # API expects award_type_codes as array parameter
                params["award_type_codes"] = award_type_codes
        
        # Construct endpoint
        endpoint = self._construct_endpoint(toptier_code)
        
        # Make API request with params
        response = self._client._make_request(
            "GET",
            endpoint,
            params=params
        )
        
        return response