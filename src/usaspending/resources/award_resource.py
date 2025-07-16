"""Award resource implementation."""

from __future__ import annotations
from typing import Optional, Dict, Any, TYPE_CHECKING

from .base_resource import BaseResource
from ..exceptions import ValidationError

if TYPE_CHECKING:
    from ..queries.awards_search import AwardsSearch
    from ..models.award import Award


class AwardResource(BaseResource):
    """Resource for award-related operations.
    
    Provides access to award search and retrieval endpoints.
    """
    
    def get(self, award_id: str) -> Award:
        """Retrieve a single award by ID.
        
        Args:
            award_id: Unique award identifier
            
        Returns:
            Award model instance
            
        Raises:
            ValidationError: If award_id is invalid
            APIError: If award not found
        """
        if not award_id:
            raise ValidationError("award_id is required")
        
        # Clean award ID
        award_id = str(award_id).strip()
        
        # Make API request
        endpoint = f"/api/v2/awards/{award_id}/"
        response = self._client._make_request("GET", endpoint)
        
        # Create model instance
        from ..models.award import Award
        return Award(response, client=self._client)
    
    def search(self) -> AwardsSearch:
        """Create a new award search query builder.
        
        Returns:
            AwardSearch query builder for chaining filters
            
        Example:
            >>> awards = client.awards.search()
            ...     .for_agency("NASA")
            ...     .in_state("TX")
            ...     .fiscal_years(2023, 2024)
            ...     .limit(10)
        """
        from ..queries.awards_search import AwardsSearch
        return AwardsSearch(self._client)