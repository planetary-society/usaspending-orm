"""Recipient resource implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger
from .base_resource import BaseResource

if TYPE_CHECKING:
    from ..models.recipient import Recipient
    from ..queries.recipients_search import RecipientsSearch

logger = USASpendingLogger.get_logger(__name__)


class RecipientsResource(BaseResource):
    """Resource for recipient-related operations.

    Provides access to recipient search and retrieval endpoints.
    """

    def find_by_recipient_id(
        self,
        recipient_id: str,
        year: int | str | None = None,
    ) -> Recipient:
        """Retrieve a single recipient by ID.

        Direct-ID lookups raise on miss rather than returning None. For the
        search-delegation convention (which returns Optional), see
        ``find_by_duns`` and ``find_by_uei``.

        Choosing a level: the same entity can exist at several levels, each a
        separate record with its own totals. An ID given with an explicit
        suffix is used as-is, so pass ``"<hash>-R"`` to fetch that level
        specifically. Only a multi-level ID, of the ``"<hash>-['C', 'R']"``
        form that ``raw()`` and the website report, is reduced to one level,
        and it avoids ``-R`` because that record frequently reports zero
        spending. :attr:`Recipient.recipient_level` reports which level came
        back.

        Args:
            recipient_id: Unique recipient identifier (hash + level suffix,
                e.g., "abc123def-R" for regular or "abc123def-P" for parent)
            year: Optional fiscal year for recipient data. Can be:
                - An integer fiscal year (e.g., 2024)
                - "latest" to get the most recent fiscal year's data
                - "all" to get aggregated data across all years
                - None (default) to use the API's default behavior

        Returns:
            Recipient model instance

        Raises:
            ValidationError: If recipient_id is invalid or year format is invalid
            APIError: If recipient not found

        Example:
            >>> recipient = client.recipients.find_by_recipient_id("abc123-R", year=2024)
            >>> recipient = client.recipients.find_by_recipient_id("abc123-P", year="latest")
        """
        logger.debug(f"Retrieving recipient by ID: {recipient_id}, year: {year}")
        from ..queries.recipient_query import RecipientQuery

        return RecipientQuery(self._client).find_by_id(recipient_id, year=year)

    def search(self) -> RecipientsSearch:
        """Create a new recipient search query builder.

        Returns:
            RecipientsSearch query builder for recipient searches

        Example:
            >>> recipients = client.recipients.search()
            ...     .keyword("california")
            ...     .award_type("contracts")
            ...     .order_by("amount", "desc")
            ...     .limit(10)
        """
        logger.debug("Creating new RecipientsSearch query builder for recipient searches")
        from ..queries.recipients_search import RecipientsSearch

        return RecipientsSearch(self._client)

    def _find_by_keyword(self, keyword: str, label: str) -> Recipient | None:
        """Find one recipient by a keyword that identifies it, such as a DUNS or UEI.

        Prefers a parent-level result. A single entity can appear at several
        recipient levels, and the parent record is the one that aggregates its
        children, which is what a caller looking an entity up by its identifier
        expects.

        Args:
            keyword: The identifier to search for.
            label: What the keyword is, for the debug log.

        Returns:
            Optional[Recipient]: The parent-level match if there is one, else the
            first result, else None.
        """
        logger.debug(f"Searching recipient by {label}: {keyword}")
        from ..queries.recipients_search import RecipientsSearch

        recipients = RecipientsSearch(self._client).keyword(keyword).limit(4)
        for recipient in recipients:
            # A suffix check, not a substring one: the level is the tail of the
            # ID, and the search results are already normalized to one level.
            if recipient.recipient_id and recipient.recipient_id.endswith("-P"):
                return recipient

        # first() rather than indexing, which would force a count of a query
        # whose total the API does not report cheaply.
        return recipients.first()

    def find_by_duns(self, duns: str) -> Recipient | None:
        """Retrieve a single recipient by DUNS number.

        Args:
            duns: Unique DUNS identifier

        Returns:
            Recipient model instance or None if not found

        Raises:
            ValidationError: If duns is invalid
        """
        return self._find_by_keyword(duns, "DUNS")

    def find_by_uei(self, uei: str) -> Recipient | None:
        """Retrieve a single recipient by UEI number.

        Args:
            uei: Unique Entity Identifier

        Returns:
            Recipient model instance or None if not found

        Raises:
            ValidationError: If uei is invalid
        """
        return self._find_by_keyword(uei, "UEI")
