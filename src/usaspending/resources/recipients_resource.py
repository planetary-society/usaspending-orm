"""Recipient resource implementation."""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..queries.recipients_search import RecipientsSearch
    from ..models.recipient import Recipient

logger = USASpendingLogger.get_logger(__name__)


class RecipientsResource(BaseResource):
    """Resource for recipient-related operations.

    Provides access to recipient search and retrieval endpoints.
    """

    def find_by_recipient_id(self, recipient_id: str) -> Optional["Recipient"]:
        """Retrieve a single recipient by ID.

        Args:
            recipient_id: Unique recipient identifier

        Returns:
            Recipient model instance

        Raises:
            ValidationError: If recipient_id is invalid
            APIError: If recipient not found
        """
        logger.debug(f"Retrieving recipient by ID: {recipient_id}")
        from ..queries.recipient_query import RecipientQuery

        return RecipientQuery(self._client).find_by_id(recipient_id)

    def search(self) -> "RecipientsSearch":
        """Create a new recipient search query builder.

        Returns:
            RecipientsSearch query builder for recipient searches
        
        Example:
            >>> recipients = client.recipients.search()
            ...     .with_keyword("california")
            ...     .with_award_type("contracts")
            ...     .order_by("amount", "desc")
            ...     .limit(10)
        """
        logger.debug("Creating new RecipientsSearch query builder for recipient searches")
        from ..queries.recipients_search import RecipientsSearch

        return RecipientsSearch(self._client)

    def find_by_duns(self, duns: str) -> Optional["Recipient"]:
        """Retrieve a single recipient by DUNS number.

        Args:
            duns: Unique DUNS identifier

        Returns:
            Recipient model instance or None if not found

        Raises:
            ValidationError: If duns is invalid
        """
        logger.debug(f"Searching recipient by DUNS: {duns}")
        from ..queries.recipients_search import RecipientsSearch
        recipients = RecipientsSearch(self._client).with_keyword(duns).limit(4)
        # Return the parent recipient if available, otherwise first result
        for r in recipients:
            if "-P" in r.recipient_id:
                return r
        # Return first result if no parent found (avoids hanging len() call)
        return recipients.first()
        
    def find_by_uei(self, uei: str) -> Optional["Recipient"]:
        """Retrieve a single recipient by UEI number.

        Args:
            uei: Unique Entity Identifier

        Returns:
            Recipient model instance or None if not found

        Raises:
            ValidationError: If uei is invalid
        """
        logger.debug(f"Searching recipient by UEI: {uei}")
        from ..queries.recipients_search import RecipientsSearch
        recipients = RecipientsSearch(self._client).with_keyword(uei).limit(4)
        # Return the parent recipient if available, otherwise first result
        for r in recipients:
            if "-P" in r.recipient_id:
                return r
        # Return first result if no parent found (avoids hanging len() call)
        return recipients.first()
        