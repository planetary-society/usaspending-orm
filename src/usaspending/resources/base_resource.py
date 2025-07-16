from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import USASpending


class BaseResource:
    """Base class for API resources.
    
    Resources provide structured gateways to USASpending API endpoints
    and return appropriate query builders or model instances.
    """
    
    def __init__(self, client: USASpending):
        """Initialize resource with client reference.
        
        Args:
            client: USASpending client instance
        """
        self._client :USASpending = client
    
    @property
    def client(self) -> USASpending:
        """Get client instance."""
        return self._client