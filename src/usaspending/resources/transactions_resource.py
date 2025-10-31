"""Transactions resource implementation."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..queries.transactions_search import TransactionsSearch

logger = USASpendingLogger.get_logger(__name__)


class TransactionsResource(BaseResource):
    """Resource for transaction-related operations.

    Provides access to transaction search and retrieval endpoints.
    """

    def award_id(self, award_id: str) -> "TransactionsSearch":
        """Create a transactions search query for a specific award.

        Args:
            award_id: Unique award identifier

        Returns:
            TransactionsSearch query builder for chaining filters

        Example:
            >>> transactions = client.transactions.award_id("CONT_AWD_123")
            ...     .limit(50)
            >>> for txn in transactions:
            ...     print(f"{txn.action_date}: ${txn.federal_action_obligation:,.2f}")
        """
        logger.debug(f"Creating transactions search for award: {award_id}")
        from ..queries.transactions_search import TransactionsSearch

        return TransactionsSearch(self._client).award_id(award_id)
