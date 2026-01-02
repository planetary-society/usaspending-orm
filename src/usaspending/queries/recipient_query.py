from __future__ import annotations

from typing import TYPE_CHECKING

from ..client import USASpendingClient
from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from .filters import parse_fiscal_year
from .single_resource_base import SingleResourceBase

if TYPE_CHECKING:
    from ..models.recipient import Recipient

logger = USASpendingLogger.get_logger(__name__)


class RecipientQuery(SingleResourceBase):
    """Retrieve a single-recipient"""

    def __init__(self, client: USASpendingClient):
        super().__init__(client)

    @property
    def _endpoint(self) -> str:
        """Base endpoint for single recipient retrieval."""
        return "/recipient/"

    def find_by_id(
        self,
        recipient_id: str,
        year: int | str | None = None,
    ) -> Recipient:
        """
        Retrieve a recipient by unique identifier.

        Args:
            recipient_id: The unique recipient identifier (hash + level suffix,
                e.g., "abc123def-R" for a regular recipient or "abc123def-P" for parent).
            year: Optional fiscal year for recipient data. Can be:
                - An integer fiscal year (e.g., 2024)
                - "latest" to get the most recent fiscal year's data
                - "all" to get aggregated data across all years
                - None (default) to use the API's default behavior

        Returns:
            Recipient: A Recipient model instance with the requested data.

        Raises:
            ValidationError: If recipient_id is empty or year is invalid.

        Example:
            >>> # Get recipient with latest year data
            >>> recipient = client.recipients.find_by_id("abc123-R", year="latest")

            >>> # Get recipient with FY2024 data
            >>> recipient = client.recipients.find_by_id("abc123-R", year=2024)

            >>> # Get recipient with all years aggregated
            >>> recipient = client.recipients.find_by_id("abc123-R", year="all")
        """
        if not recipient_id:
            raise ValidationError("recipient_id is required")

        params = None
        if year is not None:
            params = {"year": self._validate_year(year)}

        # Make API request
        response = self._get_resource(recipient_id, params=params)

        # Create model instance
        from ..models.recipient import Recipient

        return Recipient(response, client=self._client)

    def _validate_year(self, year: int | str) -> str:
        """
        Validate and normalize the year parameter.

        Args:
            year: The year value to validate.

        Returns:
            str: The validated year as a string.

        Raises:
            ValidationError: If year is not a valid format.
        """
        # Handle special string values first
        if isinstance(year, str):
            year_lower = year.strip().lower()
            if year_lower in ("latest", "all"):
                return year_lower
            year = year.strip()

        # Use shared validation for numeric years (handles both int and numeric strings)
        validated_year = parse_fiscal_year(year)
        return str(validated_year)

    def _clean_resource_id(self, resource_id: str) -> str:
        """Clean recipient ID formats and whitespace."""
        cleaned_resource_id = super()._clean_resource_id(resource_id)
        return self._clean_recipient_id(cleaned_resource_id)

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
        suffix = (
            "R" if "R" in clean_tokens else (clean_tokens[0] if clean_tokens else "")
        )

        return f"{base}-{suffix}" if suffix else base
