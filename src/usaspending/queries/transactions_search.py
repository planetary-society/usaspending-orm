"""Transactions search query builder for USASpending data."""

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING, Iterator
from datetime import datetime

from ..exceptions import ValidationError
from ..models.transaction import Transaction
from .query_builder import QueryBuilder
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class TransactionsSearch(QueryBuilder["Transaction"]):
    """
    Builds and executes a transactions search query, allowing for filtering
    on transaction data. This class follows a fluent interface pattern.
    """

    def __init__(self, client: "USASpendingClient"):
        """
        Initializes the TransactionsSearch query builder.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)
        self._award_id: str = None
        # Client-side filters (not supported by API)
        self._client_filters = {}

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/transactions/"

    def _clone(self) -> TransactionsSearch:
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._filter_objects = self._filter_objects.copy()
        clone._award_id = self._award_id
        clone._client_filters = self._client_filters.copy()
        return clone

    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Constructs the final API request payload from the filter objects."""

        if not self._award_id:
            raise ValidationError(
                "An award_id is required. Use the .award_id() method."
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
        return Transaction(result)

    def count(self) -> int:
        """Counts the number of transactions per a given award id."""
        logger.debug(f"{self.__class__.__name__}.count() called")

        # If we have client-side filters, we need to fetch all results and count
        if self._client_filters:
            logger.debug(
                "Client-side filters present, counting by iterating all results"
            )
            count = 0
            for _ in self:
                count += 1
            return count

        # No client-side filters, use the efficient API count endpoint
        endpoint = f"/awards/count/transaction/{self._award_id}/"

        from ..logging_config import log_query_execution

        log_query_execution(logger, "TransactionsSearch.count", [], endpoint)

        # Send the request to the count endpoint
        response = self._client._make_request("GET", endpoint)

        # Extract count from the appropriate category
        total = response.get("transactions", 0)

        logger.info(
            f"{self.__class__.__name__}.count() = {total} transactions for award {self._award_id}"
        )
        return total

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def award_id(self, award_id: str) -> TransactionsSearch:
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

    def since(self, date: str) -> "TransactionsSearch":
        """
        Filter transactions to those on or after the specified date.

        Note: This filter is applied client-side as the API endpoint
        doesn't support date filtering for transactions.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            A new TransactionsSearch instance with the date filter applied

        Example:
            >>> transactions = award.transactions.since("2024-01-01").all()
        """
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValidationError("Date must be in YYYY-MM-DD format")

        clone = self._clone()
        clone._client_filters["since_date"] = date
        return clone

    def until(self, date: str) -> "TransactionsSearch":
        """
        Filter transactions to those on or before the specified date.

        Note: This filter is applied client-side as the API endpoint
        doesn't support date filtering for transactions.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            A new TransactionsSearch instance with the date filter applied

        Example:
            >>> transactions = award.transactions.until("2024-12-31").all()
        """
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValidationError("Date must be in YYYY-MM-DD format")

        clone = self._clone()
        clone._client_filters["until_date"] = date
        return clone

    def _apply_client_filters(self, transaction: Transaction) -> bool:
        """
        Apply client-side filters to a transaction.

        Args:
            transaction: The transaction to filter

        Returns:
            True if transaction passes all filters, False otherwise
        """
        # Apply date filters
        if "since_date" in self._client_filters:
            since_date = datetime.strptime(
                self._client_filters["since_date"], "%Y-%m-%d"
            ).date()
            if transaction.action_date and transaction.action_date.date() < since_date:
                return False

        if "until_date" in self._client_filters:
            until_date = datetime.strptime(
                self._client_filters["until_date"], "%Y-%m-%d"
            ).date()
            if transaction.action_date and transaction.action_date.date() > until_date:
                return False

        return True

    def __iter__(self) -> Iterator[Transaction]:
        """
        Override iteration to apply client-side filters.
        """
        for transaction in super().__iter__():
            if self._apply_client_filters(transaction):
                yield transaction
