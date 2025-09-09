"""Subawards resource implementation."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..queries.subawards_search import SubAwardsSearch

logger = USASpendingLogger.get_logger(__name__)


class SubAwardsResource(BaseResource):
    """Resource for subaward-related operations.

    Provides access to subaward search and retrieval endpoints. Subawards
    represent the secondary distribution of federal funds from prime recipients
    to subrecipients who carry out portions of the federal program.

    The resource supports searching for both contract subawards (subcontracts)
    and grant subawards, with filtering by time periods, award types, agencies,
    and recipients. Results include detailed information about the prime award,
    subrecipient, and the subaward transaction itself.

    Note: Subaward reporting is required for subawards of $30,000 or more under
    the Federal Funding Accountability and Transparency Act (FFATA).
    """

    def search(self) -> "SubAwardsSearch":
        """Create a subawards search query builder.

        Returns:
            SubAwardsSearch query builder for chaining filters

        Example:
            >>> subawards = client.subawards.search()
            ...     .with_award_types("A", "B", "C")
            ...     .in_time_period("2024-01-01", "2024-12-31")
            ...     .limit(50)
            >>> for sub in subawards:
            ...     print(f"{sub.sub_awardee_name}: ${sub.sub_award_amount:,.2f}")
        """
        logger.debug("Creating subawards search query builder")
        from ..queries.subawards_search import SubAwardsSearch

        return SubAwardsSearch(self._client)

    def for_award(self, award_id: str) -> "SubAwardsSearch":
        """Create a subawards search query for a specific award.

        This is a convenience method that chains search().for_award(award_id).

        Args:
            award_id: Unique award identifier

        Returns:
            SubAwardsSearch query builder for chaining filters

        Example:
            >>> subawards = client.subawards.for_award("CONT_AWD_123...")
            ...     .limit(50)
            >>> for sub in subawards:
            ...     print(f"{sub.sub_award_date}: {sub.sub_awardee_name}")
        """
        logger.debug(f"Creating subawards search for award: {award_id}")
        return self.search().for_award(award_id)
