"""Recipient resource implementation."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..queries.spending_search import SpendingSearch
    from ..models.recipient import Recipient

logger = USASpendingLogger.get_logger(__name__)


class RecipientsResource(BaseResource):
    """Resource for recipient-related operations.

    Provides access to recipient search and retrieval endpoints.
    """

    def get(self, recipient_id: str) -> "Recipient":
        """Retrieve a single award by ID.

        Args:
            recipient_id: Unique award identifier

        Returns:
            Award model instance

        Raises:
            : If recipient_id is invalid
            APIError: If award not found
        """
        logger.debug(f"Retrieving recipient by ID: {recipient_id}")
        from ..queries.recipient_query import RecipientQuery

        return RecipientQuery(self._client).find_by_id(recipient_id)

    def search(self) -> "SpendingSearch":
        """Create a new recipient search query builder.

        Returns:
            SpendingSearch query builder configured for recipient searches
        
        Example:
            >>> recipients = client.recipients.search()
            ...     .for_agency("NASA")
            ...     .with_recipient_types("small_business")
            ...     .for_fiscal_year(2024)
            ...     .limit(10)
        """
        logger.debug("Creating new SpendingSearch query builder for recipient searches")
        from ..queries.spending_search import SpendingSearch

        return SpendingSearch(self._client).by_recipient()
