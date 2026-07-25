"""Transactions search query builder for USASpending data."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..models.transaction import Transaction
from ..utils.validations import parse_date_string
from .mixins import AwardScopedQuery
from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class TransactionsSearch(AwardScopedQuery, QueryBuilder["Transaction"]):
    """
    Builds and executes a transactions search query, allowing for filtering
    on transaction data. This class follows a fluent interface pattern.
    """

    _MAX_PAGE_SIZE: int = 5000

    # Valid sort fields per API documentation
    VALID_SORT_FIELDS = frozenset(
        {
            "modification_number",
            "action_date",
            "federal_action_obligation",
            "face_value_loan_guarantee",
            "original_loan_subsidy_cost",
            "action_type_description",
            "description",
        }
    )

    def __init__(self, client: USASpendingClient):
        """
        Initializes the TransactionsSearch query builder.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)
        # Client-side filters (not supported by API)
        self._client_filters: dict[str, Any] = {}

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/transactions/"

    def _clone(self) -> TransactionsSearch:
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._client_filters = self._client_filters.copy()
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload from the filter objects."""
        payload = {
            "award_id": self._require_award_id(),
            "limit": self._get_effective_page_size(),
            "page": page,
        }

        # Add sort parameters if specified
        if self._order_by:
            payload["sort"] = self._order_by
            payload["order"] = self._order_direction

        # Add any additional filters if they exist
        final_filters = self._aggregate_filters()
        if final_filters:
            payload.update(final_filters)

        return payload

    def _transform_result(self, result: dict[str, Any]) -> Transaction:
        """Transforms a single API result item into a Transaction model."""
        return Transaction(result)

    def _compute_raw_count(self) -> int:
        """Counts the number of transactions per a given award id."""
        # The count endpoint cannot know about client-side filters, so when any
        # are set the only correct count comes from iterating filtered results.
        if self._client_filters:
            logger.debug("Client-side filters present, counting by iterating all results")
            return self._count_via_paging()

        return self._count_via_endpoint(
            f"/awards/count/transaction/{self._require_award_id()}/", "transactions"
        )

    def __getitem__(self, key: int | slice) -> Transaction | list[Transaction]:
        """
        Retrieve specific transaction(s) by index or slice.

        Overrides QueryBuilder.__getitem__ to handle client-side filtering.
        When client filters are active, we must iterate to find the correct items.
        """
        if not self._client_filters:
            return super().__getitem__(key)

        # With client filters, we can't jump to a page. We must iterate.
        # This is inefficient but necessary for correctness.

        if isinstance(key, int):
            # Handle negative index by counting first
            if key < 0:
                total = self.count()
                key += total

            if key < 0:
                raise IndexError("Transaction index out of range")

            # Iterate until we find the item
            for i, item in enumerate(self):
                if i == key:
                    return item

            raise IndexError("Transaction index out of range")

        elif isinstance(key, slice):
            # Handle slicing - this fetches all matches then slices
            return list(self)[key]

        else:
            raise TypeError(f"indices must be integers or slices, not {type(key).__name__}")

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def since(self, date: str) -> TransactionsSearch:
        """
        Filter transactions to those on or after the specified date.

        Args:
            date: Date string in YYYY-MM-DD format.

        Returns:
            TransactionsSearch: A new instance with the date filter applied.

        Raises:
            ValidationError: If date format is not YYYY-MM-DD.

        Note:
            This filter is applied **client-side** because the /transactions/
            API endpoint doesn't support date filtering. All transactions are
            fetched and then filtered locally, which may be slower for awards
            with many transactions.

        Example:
            >>> # Get transactions from 2024 onwards
            >>> recent = award.transactions.since("2024-01-01").all()

            >>> # Combine with until() for a date range
            >>> q1_2024 = award.transactions.since("2024-01-01").until("2024-03-31").all()
        """
        # Validate date format (parse_date_string validates and returns a date object)
        parse_date_string(date, "since_date")

        clone = self._clone()
        clone._client_filters["since_date"] = date
        return clone

    def until(self, date: str) -> TransactionsSearch:
        """
        Filter transactions to those on or before the specified date.

        Args:
            date: Date string in YYYY-MM-DD format.

        Returns:
            TransactionsSearch: A new instance with the date filter applied.

        Raises:
            ValidationError: If date format is not YYYY-MM-DD.

        Note:
            This filter is applied **client-side** because the /transactions/
            API endpoint doesn't support date filtering. All transactions are
            fetched and then filtered locally.

        Example:
            >>> # Get historical transactions only
            >>> historical = award.transactions.until("2023-12-31").all()

            >>> # Combine with since() for a date range
            >>> fy2024 = award.transactions.since("2023-10-01").until("2024-09-30").all()
        """
        # Validate date format (parse_date_string validates and returns a date object)
        parse_date_string(date, "until_date")

        clone = self._clone()
        clone._client_filters["until_date"] = date
        return clone

    def order_by(self, field: str, direction: str = "desc") -> TransactionsSearch:
        """
        Set the sort order for transaction results.

        Args:
            field: The field to sort by (case-sensitive).
            direction: Sort direction - "asc" or "desc" (default: "desc").

        Valid Sort Fields:
            "modification_number": Transaction sequence/modification number
            "action_date": Date the transaction action occurred
            "federal_action_obligation": Dollar amount obligated
            "face_value_loan_guarantee": Face value of loan (loans only)
            "original_loan_subsidy_cost": Loan subsidy cost (loans only)
            "action_type_description": Description of the action type
            "description": Transaction description text

        Returns:
            TransactionsSearch: A new instance with the sort applied.

        Raises:
            ValidationError: If field is not in the valid list, or direction
                is not "asc" or "desc".

        Example:
            >>> # Sort by obligation amount, largest first
            >>> transactions = client.transactions.award_id("ABC123").order_by(
            ...     "federal_action_obligation", "desc"
            ... )

            >>> # Sort by date, oldest first
            >>> historical = award.transactions.order_by("action_date", "asc")

        Note:
            Loan-specific fields (face_value_loan_guarantee, original_loan_subsidy_cost)
            are only populated for loan award transactions.
        """
        if field not in self.VALID_SORT_FIELDS:
            raise ValidationError(
                f"Invalid sort field '{field}'. "
                f"Valid fields: {', '.join(sorted(self.VALID_SORT_FIELDS))}"
            )

        if direction not in ("asc", "desc"):
            raise ValidationError(f"Invalid sort direction '{direction}'. Must be 'asc' or 'desc'.")

        clone = self._clone()
        clone._order_by = field
        clone._order_direction = direction
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
            since_date = datetime.strptime(self._client_filters["since_date"], "%Y-%m-%d").date()
            if transaction.action_date and transaction.action_date < since_date:
                return False

        if "until_date" in self._client_filters:
            until_date = datetime.strptime(self._client_filters["until_date"], "%Y-%m-%d").date()
            if transaction.action_date and transaction.action_date > until_date:
                return False

        return True

    def __iter__(self) -> Iterator[Transaction]:
        """
        Override iteration to apply client-side filters.
        """
        for transaction in super().__iter__():
            if self._apply_client_filters(transaction):
                yield transaction
