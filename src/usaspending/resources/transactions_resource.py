"""Transactions resource implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger
from .base_resource import BaseResource

if TYPE_CHECKING:
    from ..queries.award_transactions_search import AwardTransactionsSearch
    from ..queries.transactions_search import TransactionsSearch

logger = USASpendingLogger.get_logger(__name__)


class TransactionsResource(BaseResource):
    """Resource for transaction-related operations.

    Provides access to transaction search and retrieval endpoints.
    """

    def award_id(self, award_id: str) -> AwardTransactionsSearch:
        """Create a transactions search query for a specific award.

        Args:
            award_id: Unique award identifier

        Returns:
            AwardTransactionsSearch query builder for chaining filters

        Example:
            >>> transactions = client.transactions.award_id("CONT_AWD_123").limit(50)
            >>> for txn in transactions:
            ...     print(f"{txn.action_date}: ${txn.federal_action_obligation or 0:,.2f}")
        """
        logger.debug(f"Creating transactions search for award: {award_id}")
        from ..queries.award_transactions_search import AwardTransactionsSearch

        return AwardTransactionsSearch(self._client).award_id(award_id)

    def search(self) -> TransactionsSearch:
        """Create a transaction search query across all awards.

        Unlike :meth:`award_id`, which lists the transactions of one award, this
        searches every transaction the API holds, using the same rich filters
        the award search offers. The API requires an award type filter, so a
        query must set one before it can be run.

        Returns:
            TransactionsSearch query builder for chaining filters

        Example:
            >>> transactions = (
            ...     client.transactions.search().contracts().keywords("space exploration").limit(10)
            ... )
            >>> for txn in transactions:
            ...     print(f"{txn.action_date}: ${txn.amt or 0:,.2f}")
        """
        logger.debug("Creating global transactions search")
        from ..queries.transactions_search import TransactionsSearch

        return TransactionsSearch(self._client)
