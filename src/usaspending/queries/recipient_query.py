from typing import TYPE_CHECKING
from .single_resource_base import SingleResourceBase
from ..exceptions import ValidationError
from ..client import USASpending
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..models.recipient import Recipient

logger = USASpendingLogger.get_logger(__name__)

class RecipientQuery(SingleResourceBase):
    """Retrieve a single-recipient"""
    
    def __init__(self, client: USASpending):
        self.super().__init__(client)
    
    @property
    def _endpoint(self) -> str:
        """Base endpoint for single recipient retrieval."""
        return "/v2/recipients/"
    
    def get_by_id(self, recipient_id: str) -> "Recipient":
        """Filter by unique recipient identifier."""
        if not recipient_id:
            raise ValidationError("recipient_id is required")
    
        # Make API request
        response = self._get_resource(recipient_id)
        
        # Create model instance
        from ..models.recipient import Recipient
        return Recipient(response, client=self._client)
    
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