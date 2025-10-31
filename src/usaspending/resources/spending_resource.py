"""Spending resource implementation."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..queries.spending_search import SpendingSearch

logger = USASpendingLogger.get_logger(__name__)


class SpendingResource(BaseResource):
    """Resource for spending-related operations.

    Provides access to spending by category endpoints (recipient and district).
    """

    def search(self) -> "SpendingSearch":
        """Create a new spending search query builder.

        Returns:
            SpendingSearch query builder for chaining filters

        Example:
            >>> # Search spending by recipient
            >>> recipient_spending = client.spending.search()
            ...     .by_recipient()
            ...     .agency("National Aeronautics and Space Administration")
            ...     .fiscal_year(2024)
            ...     .limit(10)

            >>> # Search spending by district
            >>> district_spending = client.spending.search()
            ...     .by_district()
            ...     .spending_level("awards")
            ...     .place_of_performance_locations({"country_code": "USA", "state_code": "TX"))
            ...     .all()
        """
        logger.debug("Creating new SpendingSearch query builder")
        from ..queries.spending_search import SpendingSearch

        return SpendingSearch(self._client)
