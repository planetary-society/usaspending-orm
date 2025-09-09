"""Agency award summary query implementation for retrieving award aggregations."""

from typing import TYPE_CHECKING, Optional, Dict, Any, List
from .single_resource_base import SingleResourceBase
from ..exceptions import ValidationError
from ..client import USASpendingClient
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    pass

logger = USASpendingLogger.get_logger(__name__)


class AgencyAwardSummary(SingleResourceBase):
    """Retrieve agency award summary data from the USAspending API.
    
    This query class handles fetching aggregated award information including
    transaction counts and obligations filtered by fiscal year, agency type,
    and award type codes.
    """

    def __init__(self, client: USASpendingClient):
        """Initialize AgencyAwardSummary with client.
        
        Args:
            client: USASpendingClient client instance
        """
        super().__init__(client)
        logger.debug("AgencyAwardSummary initialized with client: %s", client)

    @property
    def _endpoint(self) -> str:
        """Base endpoint for agency award summary retrieval."""
        return "/agency/"
    
    def _construct_endpoint(self, resource_id: str) -> str:
        """Construct the full endpoint URL for agency award summary.
        
        Args:
            resource_id: The toptier_code for the agency
            
        Returns:
            Full endpoint path including /awards/
        """
        return f"{self._endpoint}{resource_id}/awards/"

    def find_by_id(self, toptier_code: str) -> Dict[str, Any]:
        """Not used for award summary - use get_awards_summary instead.
        
        Raises:
            NotImplementedError: This method should not be used directly
        """
        raise NotImplementedError(
            "Use get_awards_summary() method instead for award summary data"
        )

    def get_awards_summary(
        self,
        toptier_code: str,
        fiscal_year: Optional[int] = None,
        agency_type: str = "awarding",
        award_type_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Retrieve agency award summary with optional filters.
        
        Args:
            toptier_code: The toptier code of an agency (3-4 digit string)
            fiscal_year: Optional fiscal year for the data (defaults to current)
            agency_type: "awarding" or "funding" (defaults to "awarding")
            award_type_codes: Optional list of award type codes to filter by
            
        Returns:
            Dictionary containing:
                - toptier_code: Agency toptier code
                - fiscal_year: Fiscal year of data
                - latest_action_date: Latest transaction date
                - transaction_count: Number of transactions
                - obligations: Total obligations amount
                - messages: Any API messages
            
        Raises:
            ValidationError: If toptier_code is invalid or agency_type is invalid
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
        
        logger.debug(
            "Fetching award summary for toptier_code: %s, fiscal_year: %s, "
            "agency_type: %s, award_type_codes: %s",
            toptier_code, fiscal_year, agency_type, award_type_codes
        )
        
        # Build params
        params = {"agency_type": agency_type}
        
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