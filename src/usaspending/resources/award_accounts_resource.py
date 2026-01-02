"""Award accounts resource implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger
from .base_resource import BaseResource

if TYPE_CHECKING:
    from ..queries.award_accounts_query import AwardAccountsQuery

logger = USASpendingLogger.get_logger(__name__)


class AwardAccountsResource(BaseResource):
    """Resource for award-related federal account operations.

    Provides access to federal accounts associated with specific awards,
    including funding agency information and obligated amounts.
    """

    def award_id(self, award_id: str) -> AwardAccountsQuery:
        """Create an accounts query for a specific award.

        Args:
            award_id: Unique award identifier (generated_unique_award_id).

        Returns:
            AwardAccountsQuery query builder for chaining filters.

        Example:
            >>> accounts = client.award_accounts.award_id("CONT_AWD_123...")
            >>> for account in accounts:
            ...     print(f"{account.code}: ${account.obligated_amount:,.2f}")
            ...     print(f"  Agency: {account.funding_agency_name}")
        """
        logger.debug(f"Creating award accounts query for award: {award_id}")
        from ..queries.award_accounts_query import AwardAccountsQuery

        return AwardAccountsQuery(self._client).award_id(award_id)
