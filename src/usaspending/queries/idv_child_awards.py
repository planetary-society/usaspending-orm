"""IDV child awards query builder for USASpending data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..utils.validations import validate_non_empty_string
from .mixins import SortableQuery
from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.award import Award

logger = USASpendingLogger.get_logger(__name__)


class IDVChildAwardsSearch(SortableQuery, QueryBuilder["Award"]):
    """Query builder for child awards (delivery/task orders) under an IDV.

    This class provides access to child awards associated with an Indefinite
    Delivery Vehicle (IDV). Child awards include delivery orders and task orders
    placed against the parent IDV contract.

    Example:
        >>> idv = client.awards.find_by_generated_id("CONT_IDV_...")
        >>> # Get all child awards
        >>> for child in idv.child_awards:
        ...     print(f"{child.piid}: ${child.obligated_amount:,.2f}")
        >>>
        >>> # Paginated access
        >>> idv.child_awards.limit(10).all()
        >>>
        >>> # Count child awards
        >>> idv.child_awards.count()
    """

    _sort_field: str = "obligated_amount"

    # Map user-friendly sort field names to API field names
    SORT_FIELD_MAP: ClassVar[dict[str, str]] = {
        "award_type": "award_type",
        "description": "description",
        "funding_agency": "funding_agency",
        "awarding_agency": "awarding_agency",
        "obligated_amount": "obligated_amount",
        "obligation": "obligated_amount",
        "start_date": "period_of_performance_start_date",
        "end_date": "period_of_performance_current_end_date",
        "piid": "piid",
        "last_date_to_order": "last_date_to_order",
    }

    def __init__(self, client: USASpendingClient, award_id: str):
        """Initialize the IDVChildAwardsSearch query builder.

        Args:
            client: The USASpending client instance.
            award_id: The generated_unique_award_id of the parent IDV.
        """
        super().__init__(client)
        self._award_id: str = validate_non_empty_string(award_id, "award_id")
        # IDV awards endpoint type filter for child award types
        self._idv_award_type: str = "child_awards"

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/idvs/awards/"

    def _new_instance(self) -> IDVChildAwardsSearch:
        """Reconstruct with the required award ID."""
        return self.__class__(self._client, self._award_id)

    def _clone(self) -> IDVChildAwardsSearch:
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._idv_award_type = self._idv_award_type
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload."""
        return {
            "award_id": self._award_id,
            "limit": self._get_effective_page_size(),
            "page": page,
            "type": self._idv_award_type,
            **self._sort_payload(),
        }

    def _transform_result(self, result: dict[str, Any]) -> Award:
        """Transforms a single API result item into an Award model.

        The child awards are contracts/delivery orders, so we use the
        award factory to create the appropriate Award subclass.
        """
        from ..models.award_factory import create_award

        return create_award(result, self._client)

    def _compute_raw_count(self) -> int:
        """Count the number of child awards for the IDV.

        Since the IDV awards endpoint doesn't provide a dedicated count API,
        we iterate through all pages to get the count.

        Returns:
            int: The total number of child awards.
        """
        return self._count_via_paging()

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def award_type(self, type_filter: str) -> IDVChildAwardsSearch:
        """Filter by award type.

        Args:
            type_filter: The type of awards to include:
                        - 'child_idvs' for child IDV awards only
                        - 'child_awards' for child contract awards only (default)
                        - 'grandchild_awards' for grandchild awards

        Returns:
            A new IDVChildAwardsSearch instance with the type filter applied.

        Raises:
            ValidationError: If the type filter is invalid.
        """
        valid_types = ["child_idvs", "child_awards", "grandchild_awards"]
        if type_filter.lower() not in valid_types:
            raise ValidationError(
                f"Invalid type filter: {type_filter}. Valid types are: {', '.join(valid_types)}"
            )

        clone = self._clone()
        clone._idv_award_type = type_filter.lower()
        return clone
