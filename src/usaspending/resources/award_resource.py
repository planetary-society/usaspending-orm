"""Award resource implementation."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..queries.awards_search import AwardsSearch
    from ..models.award import Award

logger = USASpendingLogger.get_logger(__name__)


class AwardResource(BaseResource):
    """Resource for award-related operations.

    Provides access to award search and retrieval endpoints.
    """

    def get(self, generated_award_id: str) -> "Award":
        """Retrieve a single award by the system's internally generated
        award entry ID (e.g. "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-")

        Args:
            generated_award_id: Unique award identifier

        Returns:
            Award model instance

        Raises:
            : If generated_award_id is invalid
            APIError: If award not found
        """
        logger.debug(f"Retrieving award by ID: {generated_award_id}")
        from ..queries.award_query import AwardQuery

        return AwardQuery(self._client).get_by_id(generated_award_id)

    def search(self) -> AwardsSearch:
        """Create a new award search query builder.

        Returns:
            AwardSearch query builder for chaining filters

        Example:
            >>> awards = client.awards.search()
            ...     .for_agency("NASA")
            ...     .in_state("TX")
            ...     .fiscal_years(2023, 2024)
            ...     .limit(10)
        """
        logger.debug("Creating new AwardsSearch query builder")
        from ..queries.awards_search import AwardsSearch

        return AwardsSearch(self._client)
