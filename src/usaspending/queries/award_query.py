from .query_builder import QueryBuilder, TYPE_CHECKING
from ..exceptions import ValidationError
from ..client import USASpending

if TYPE_CHECKING:
    from ..models.award import Award
    
class AwardQuery:
    """Retrieve a single-award"""
    
    def __init__(self, client: USASpending):
        self._client = client
    
    def get_by_id(self, award_id: str) -> "Award":
        """Filter by unique award identifier."""
        if not award_id:
            raise ValidationError("award_id is required")
        
        # Clean award ID
        award_id = str(award_id).strip()
        
        # Construct valid endpoint
        endpoint = f"/api/v2/awards/{award_id}/"
        
        # Make API request
        response = self._client._make_request("GET", endpoint)
        
        # Create model instance
        from ..models.award import Award
        return Award(response, client=self._client)