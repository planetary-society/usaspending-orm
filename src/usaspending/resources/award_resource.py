"""Award resource implementation."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

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

    def find_by_generated_id(self, generated_award_id: str) -> "Award":
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

        return AwardQuery(self._client).find_by_generated_id(generated_award_id)

    def find_by_award_id(self, award_id: str) -> Optional["Award"]:
        """Find an award by its PIID or FAIN unique identifier.
        Args:
            award_id: Unique identifier for the award (PIID or FAIN)

        Returns:
            Award model instance if found, otherwise None
        """
        logger.debug(f"Finding award by ID: {award_id}")
        from ..queries.awards_search import AwardsSearch

        # Get counts by award type
        search_result = (
            AwardsSearch(self._client).with_award_ids(award_id).count_awards_by_type()
        )

        # Find which type has exactly one result
        matching_types = [
            (award_type, count)
            for award_type, count in search_result.items()
            if count == 1
        ]

        if len(matching_types) != 1:
            total_awards = sum(count for count in search_result.values() if count > 0)
            if total_awards == 0:
                logger.info(f"No awards found for ID {award_id}")
            else:
                logger.warning(
                    f"Expected exactly one award for ID {award_id}, found {total_awards} awards across {len(matching_types)} types"
                )
            logger.debug(f"Search result: {search_result}")
            return None

        award_type, _ = matching_types[0]
        logger.info(f"Found 1 award of type {award_type} for ID {award_id}")

        # Map API response keys to method names
        method_mapping = {
            "contracts": "contracts",
            "grants": "grants",
            "idvs": "idvs",
            "loans": "loans",
            "direct_payments": "direct_payments",
            "other": "other",
        }

        method_name = method_mapping.get(award_type)
        if not method_name:
            logger.error(f"Unknown award type from API: {award_type}")
            return None

        # Create search and apply the appropriate filter
        awards_search = AwardsSearch(self._client)
        if hasattr(awards_search, method_name):
            logger.debug(f"Calling .{method_name}() method on AwardsSearch")
            awards_search = getattr(awards_search, method_name)()
            return awards_search.with_award_ids(award_id).first()
        else:
            logger.error(f"Method {method_name} not found on AwardsSearch")
            return None

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
