"""Transactions search query builder for USASpending data."""

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

from ..exceptions import ValidationError
from ..models.transaction import Transaction
from .query_builder import QueryBuilder
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..client import USASpending

logger = USASpendingLogger.get_logger(__name__)


class TransactionsSearch(QueryBuilder["Transaction"]):
    """
    Builds and executes a transactions search query, allowing for filtering
    on transaction data. This class follows a fluent interface pattern.
    """

    def __init__(self, client: "USASpending"):
        """
        Initializes the TransactionsSearch query builder.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)
        self._award_id: str = None

    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/v2/transactions/"

    def _clone(self) -> TransactionsSearch:
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._filter_objects = self._filter_objects.copy()
        clone._award_id = self._award_id
        return clone

    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Constructs the final API request payload from the filter objects."""
        
        if not self._award_id:
            raise ValidationError(
                "An award_id is required. Use the .for_award() method."
            )

        payload = {
            "award_id": self._award_id,
            "limit": self._get_effective_page_size(),
            "page": page,
        }
        
        # Add any additional filters if they exist
        final_filters = self._aggregate_filters()
        if final_filters:
            payload.update(final_filters)
        
        return payload

    def _transform_result(self, result: Dict[str, Any]) -> Transaction:
        """Transforms a single API result item into a Transaction model."""
        return Transaction(_raw=result)

    def count(self) -> int:
        """ Counts the number of transactions per a given award id."""
        logger.debug(f"{self.__class__.__name__}.count() called")
        
        endpoint = f"/v2/awards/count/transaction/{self._award_id}/"
        
        from ..logging_config import log_query_execution
        log_query_execution(logger, 'TransactionsSearch.count', 1, endpoint)
        
        # Send the request to the count endpoint
        response = self._client._make_request("GET", endpoint)
        
        # Extract count from the appropriate category
        total = response.get("transactions", 0)
        
        logger.info(f"{self.__class__.__name__}.count() = {total} transactions for award {self._award_id}")
        return total

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def for_award(self, award_id: str) -> TransactionsSearch:
        """
        Filter transactions for a specific award.

        Args:
            award_id: The unique award identifier.

        Returns:
            A new `TransactionsSearch` instance with the award filter applied.
        """
        if not award_id:
            raise ValidationError("award_id cannot be empty")
        
        clone = self._clone()
        clone._award_id = str(award_id).strip()
        return clone