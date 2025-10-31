"""Funding resource implementation."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..queries.funding_search import FundingSearch

logger = USASpendingLogger.get_logger(__name__)


class FundingResource(BaseResource):
    """Resource for funding-related operations.

    Provides access to federal account funding data for awards.
    """

    def award_id(self, award_id: str) -> "FundingSearch":
        """Create a funding search query for a specific award.

        Args:
            award_id: Unique award identifier

        Returns:
            FundingSearch query builder for chaining filters

        Example:
            >>> funding = client.funding.award_id("CONT_AWD_123")
            ...     .order_by("fiscal_date", "asc")
            ...     .limit(50)
            >>> for record in funding:
            ...     print(f"{record.reporting_fiscal_year}-{record.reporting_fiscal_month}: "
            ...           f"${record.transaction_obligated_amount:,.2f}")
        """
        logger.debug(f"Creating funding search for award: {award_id}")
        from ..queries.funding_search import FundingSearch

        return FundingSearch(self._client).award_id(award_id)
