"""Recipients search query builder for USASpending recipient search endpoint."""

from __future__ import annotations

from typing import Any, Optional, Literal, TYPE_CHECKING

from usaspending.client import USASpending
from usaspending.exceptions import ValidationError
from usaspending.queries.query_builder import QueryBuilder
from usaspending.logging_config import USASpendingLogger
from usaspending.queries.filters import SimpleListFilter

if TYPE_CHECKING:
    from usaspending.models.recipient import Recipient

logger = USASpendingLogger.get_logger(__name__)

# Valid award types for recipient searches
AwardType = Literal["all", "contracts", "grants", "loans", "direct_payments", "other_financial_assistance"]
# Valid sort fields
SortField = Literal["name", "duns", "amount"]
# Valid sort directions
SortDirection = Literal["asc", "desc"]


class RecipientsSearch(QueryBuilder["Recipient"]):
    """
    Builds and executes recipient search queries, allowing for complex
    filtering on recipient data. This class follows a fluent interface pattern.
    
    Supports filtering by keyword, award type, and sorting by various fields.
    """

    def __init__(self, client: USASpending):
        """
        Initializes the RecipientsSearch query builder.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)
        self._keyword: Optional[str] = None
        self._award_type: AwardType = "all"
        self._sort_field: SortField = "amount"
        self._sort_direction: SortDirection = "desc"

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/recipient/"

    def _clone(self) -> RecipientsSearch:
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._keyword = self._keyword
        clone._award_type = self._award_type
        clone._sort_field = self._sort_field
        clone._sort_direction = self._sort_direction
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload."""
        payload = {
            "page": page,
            "limit": self._get_effective_page_size(),
            "sort": self._sort_field,
            "order": self._sort_direction,
            "award_type": self._award_type,
        }

        # Add keyword filter if provided
        if self._keyword:
            payload["keyword"] = self._keyword

        return payload

    def _transform_result(self, result: dict[str, Any]) -> "Recipient":
        """Transforms a single API result item into a Recipient model."""
        from usaspending.models.recipient import Recipient
        if not result.get("recipient_id") and result.get("id"):
            result["recipient_id"] = result["id"]
        return Recipient(result, self._client)

    def count(self) -> int:
        """
        Get the total count of results using the dedicated count endpoint.
        
        Uses the /v2/recipient/count/ endpoint which takes the same filters
        but returns just a count value.

        Returns:
            The total number of matching recipients.
        """
        logger.debug(f"{self.__class__.__name__}.count() called")

        # Build payload for count endpoint (no pagination params needed)
        payload = {
            "award_type": self._award_type,
        }

        # Add keyword filter if provided
        if self._keyword:
            payload["keyword"] = self._keyword

        # Make API request to count endpoint
        count_endpoint = "/recipient/count/"
        response = self._client._make_request("POST", count_endpoint, json=payload)
        
        total_count = response.get("count", 0)
        logger.info(f"{self.__class__.__name__}.count() = {total_count}")
        return total_count

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def with_keyword(self, keyword: str) -> RecipientsSearch:
        """
        Filter by recipient name, UEI, or DUNS keyword.

        Args:
            keyword: The keyword to search for across recipient identifiers.

        Returns:
            A new RecipientsSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._keyword = keyword.strip() if keyword else None
        return clone

    def with_award_type(self, award_type: AwardType) -> RecipientsSearch:
        """
        Filter by award type.

        Args:
            award_type: The award type to filter by.

        Returns:
            A new RecipientsSearch instance with the filter applied.
        """
        clone = self._clone()
        clone._award_type = award_type
        return clone

    def order_by(self, field: SortField, direction: SortDirection = "desc") -> RecipientsSearch:
        """
        Set the sort field and direction.

        Args:
            field: The field to sort by (name, duns, amount).
            direction: The sort direction (asc or desc).

        Returns:
            A new RecipientsSearch instance with the sorting applied.
        """
        clone = self._clone()
        clone._sort_field = field
        clone._sort_direction = direction
        return clone