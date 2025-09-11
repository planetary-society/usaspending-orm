"""Subawards search query builder for USASpending data."""

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING, Optional

from ..exceptions import ValidationError
from ..models.subaward import SubAward
from .awards_search import AwardsSearch
from ..logging_config import USASpendingLogger
from ..models.award_types import get_category_for_code

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class SubAwardsSearch(AwardsSearch):
    """
    Builds and executes a subawards search query, allowing for complex
    filtering on subaward data. This class extends AwardsSearch to reuse
    filter logic while specializing for subawards.
    """

    def __init__(self, client: "USASpendingClient"):
        """
        Initializes the SubAwardsSearch query builder.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)
        self._award_id: Optional[str] = None

    def _clone(self) -> SubAwardsSearch:
        """Creates an immutable copy of the query builder."""
        clone = SubAwardsSearch(self._client)
        clone._filter_objects = self._filter_objects.copy()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        clone._award_id = self._award_id
        return clone

    def _build_payload(self, page: int) -> Dict[str, Any]:
        """
        Constructs the final API request payload for subawards.

        Overrides parent to always include subawards=true and spending_level=subawards.
        """
        payload = super()._build_payload(page)

        # Always search for subawards
        payload["subawards"] = True
        payload["spending_level"] = "subawards"

        # If filtering by specific award, add to filters
        if self._award_id:
            if "filters" not in payload:
                payload["filters"] = {}
            payload["filters"]["award_unique_id"] = self._award_id

        return payload

    def _transform_result(self, result: Dict[str, Any]) -> SubAward:
        """Transforms a single API result item into a SubAward model."""
        return SubAward(result, self._client)

    def _get_fields(self) -> list[str]:
        """
        Determines the list of fields to request based on award type filters.

        Returns different field sets depending on the award type codes:
        - Contracts: Contract subaward fields
        - Grants/Assistance: Grant subaward fields
        """
        # Get award type codes from filters
        award_types = self._get_award_type_codes()

        # Determine if we're dealing with contracts or grants
        is_contract = False
        is_grant = False

        # Check each award type code to determine categories
        for award_type in award_types:
            category = get_category_for_code(award_type)
            if category == "contracts":
                is_contract = True
            elif category == "grants":
                is_grant = True

        # Return appropriate field set
        if is_contract and not is_grant:
            return SubAward.CONTRACT_SUBAWARD_FIELDS.copy()
        elif is_grant and not is_contract:
            return SubAward.GRANT_SUBAWARD_FIELDS.copy()
        else:
            # If both or neither, return union of both field sets
            fields = set(SubAward.CONTRACT_SUBAWARD_FIELDS)
            fields.update(SubAward.GRANT_SUBAWARD_FIELDS)
            return list(fields)

    def count(self) -> int:
        """
        Get the total count of subawards.

        If filtering by a specific award, uses the efficient count endpoint.
        Otherwise falls back to parent implementation.
        """
        logger.debug(f"{self.__class__.__name__}.count() called")

        # If we have an award_id filter, use the efficient count endpoint
        if self._award_id:
            endpoint = f"/awards/count/subaward/{self._award_id}/"

            from ..logging_config import log_query_execution

            log_query_execution(logger, "SubAwardsSearch.count", [], endpoint)

            # Send the request to the count endpoint
            response = self._client._make_request("GET", endpoint)

            # Extract count from response
            total = response.get("subawards", 0)

            logger.info(
                f"{self.__class__.__name__}.count() = {total} subawards for award {self._award_id}"
            )
            return total

        # Fall back to parent implementation for general subaward counting
        # This is inefficient, but it's the only way to get the count
        # without a dedicated endpoint for subaward searches.
        # The parent's count() method will iterate through all pages.
        # return super().count()
        # For now, let's just iterate and count
        count = 0
        for _ in self:
            count += 1
        return count

    def count_awards_by_type(self) -> Dict[str, int]:
        """
        Override parent method to use subawards-specific count endpoint.

        Returns:
            A dictionary mapping award type categories to their subaward counts.
        """
        endpoint = "/search/spending_by_award_count/"
        final_filters = self._aggregate_filters()

        payload = {
            "filters": final_filters,
            "subawards": True,  # Always count subawards
            "spending_level": "subawards",
        }

        from ..logging_config import log_query_execution

        log_query_execution(
            logger,
            "SubAwardsSearch.count_awards_by_type",
            self._filter_objects,
            endpoint,
        )

        # Send the request to the count endpoint
        response = self._client._make_request("POST", endpoint, json=payload)

        # Extract and return aggregations
        return response.get("aggregations", {})

    def for_award(self, award_id: str) -> SubAwardsSearch:
        """
        Filter subawards for a specific prime award.

        Args:
            award_id: The unique generated award identifier.

        Returns:
            A new SubAwardsSearch instance with the award filter applied.

        Example:
            >>> subawards = client.subawards.for_award("CONT_AWD_123...")
            >>> for sub in subawards:
            ...     print(f"{sub.sub_awardee_name}: ${sub.sub_award_amount:,.2f}")
        """
        if not award_id:
            raise ValidationError("award_id cannot be empty")

        clone = self._clone()
        clone._award_id = str(award_id).strip()
        return clone
