"""Recipient resource implementation."""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from .base_resource import BaseResource
from ..exceptions import ValidationError

if TYPE_CHECKING:
    from ..queries.recipient import RecipientSearch
    from ..models.recipient import Recipient


class RecipientResource(BaseResource):
    """Resource for recipient-related operations.
    
    Provides access to recipient search and retrieval endpoints.
    """
    
    def get(self, recipient_id: str) -> Recipient:
        """Retrieve a single recipient by ID.
        
        Args:
            recipient_id: Unique recipient identifier (with hash suffix)
            
        Returns:
            Recipient model instance
            
        Raises:
            ValidationError: If recipient_id is invalid
            APIError: If recipient not found
        """
        if not recipient_id:
            raise ValidationError("recipient_id is required")
        
        # Clean recipient ID (handle potential list suffixes)
        recipient_id = self._clean_recipient_id(str(recipient_id).strip())
        
        # Make API request
        endpoint = f"/recipient/{recipient_id}/"
        response = self._client._make_request("GET", endpoint)
        
        # Create model instance
        from ..models.recipient import Recipient
        return Recipient(response, client=self._client)
    
    def search(self) -> RecipientSearch:
        """Create a new recipient search query builder.
        
        Returns:
            RecipientSearch query builder for chaining filters
        """
        from ..queries.recipient import RecipientSearch
        return RecipientSearch(self._client)
    
    def _clean_recipient_id(self, recipient_id: str) -> str:
        """Clean recipient ID format.
        
        Handles cases like "abc123-['C','R']" -> "abc123-R"
        """
        import re
        
        # Pattern for list suffix: -[...]
        pattern = r"^(.+?)-\[\s*([^\]]+)\]$"
        match = re.match(pattern, recipient_id)
        
        if not match:
            return recipient_id
        
        base = match.group(1)
        tokens = match.group(2)
        
        # Extract and clean tokens
        clean_tokens = []
        for token in tokens.split(","):
            clean_token = token.strip().strip("'\"").upper()
            if clean_token:
                clean_tokens.append(clean_token)
        
        # Prefer 'R' if present, otherwise first token
        suffix = "R" if "R" in clean_tokens else (clean_tokens[0] if clean_tokens else "")
        
        return f"{base}-{suffix}" if suffix else base