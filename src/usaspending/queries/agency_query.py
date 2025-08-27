"""Agency query implementation for retrieving single agency details."""

from typing import TYPE_CHECKING, Optional, Dict, Any
from .single_resource_base import SingleResourceBase
from ..exceptions import ValidationError
from ..client import USASpending
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..models.agency import Agency

logger = USASpendingLogger.get_logger(__name__)


class AgencyQuery(SingleResourceBase):
    """Retrieve a single agency from the USAspending API.
    
    This query class handles fetching agency overview information for a 
    specific fiscal year using the agency's toptier code.
    """

    def __init__(self, client: USASpending):
        """Initialize AgencyQuery with client.
        
        Args:
            client: USASpending client instance
        """
        super().__init__(client)
        logger.debug("AgencyQuery initialized with client: %s", client)

    @property
    def _endpoint(self) -> str:
        """Base endpoint for single agency retrieval."""
        return "/v2/agency/"

    def get_by_id(self, toptier_code: str, fiscal_year: Optional[int] = None) -> "Agency":
        """Retrieve agency by toptier code and optional fiscal year.
        
        Args:
            toptier_code: The toptier code of an agency (3-4 digit string)
            fiscal_year: Optional fiscal year for the data (defaults to current)
            
        Returns:
            Agency model instance with full details
            
        Raises:
            ValidationError: If toptier_code is invalid
            APIError: If agency not found
        """
        if not toptier_code:
            raise ValidationError("toptier_code is required")
        
        # Validate toptier_code format (3-4 digit numeric string)
        toptier_code = str(toptier_code).strip()
        if not toptier_code.isdigit() or len(toptier_code) not in [3, 4]:
            raise ValidationError(
                f"Invalid toptier_code: {toptier_code}. "
                "Must be a 3-4 digit numeric string"
            )
        
        logger.debug(
            "Fetching agency with toptier_code: %s, fiscal_year: %s", 
            toptier_code, fiscal_year
        )
        
        # Make API request with optional fiscal_year parameter
        response = self._get_resource_with_params(toptier_code, fiscal_year)
        
        # Create model instance
        from ..models.agency import Agency
        
        return Agency(response, client=self._client)
    
    def _get_resource_with_params(
        self, toptier_code: str, fiscal_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Retrieve agency with optional query parameters.
        
        Args:
            toptier_code: The agency's toptier code
            fiscal_year: Optional fiscal year parameter
            
        Returns:
            API response dictionary
        """
        # Construct endpoint
        endpoint = self._construct_endpoint(toptier_code)
        
        # Build params dict if fiscal_year provided
        params = {}
        if fiscal_year is not None:
            params["fiscal_year"] = fiscal_year
        
        # Make API request with params
        response = self._client._make_request(
            "GET", 
            endpoint, 
            params=params if params else None
        )
        
        return response