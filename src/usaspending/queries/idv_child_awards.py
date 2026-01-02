"""IDV child awards query builder for USASpending data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..utils.validations import validate_non_empty_string
from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.award import Award

logger = USASpendingLogger.get_logger(__name__)


class IDVChildAwardsSearch(QueryBuilder["Award"]):
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
        self._sort_field: str = "obligated_amount"
        self._sort_order: str = "desc"
        # IDV awards endpoint type filter for child award types
        self._idv_award_type: str = "child_awards"

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/idvs/awards/"

    def _clone(self) -> IDVChildAwardsSearch:
        """Creates an immutable copy of the query builder."""
        clone = IDVChildAwardsSearch(self._client, self._award_id)
        clone._total_limit = self._total_limit
        clone._page_size = self._page_size
        clone._sort_field = self._sort_field
        clone._sort_order = self._sort_order
        clone._idv_award_type = self._idv_award_type
        return clone

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload."""
        payload = {
            "award_id": self._award_id,
            "limit": self._get_effective_page_size(),
            "page": page,
            "sort": self._sort_field,
            "order": self._sort_order,
            "type": self._idv_award_type,
        }
        return payload

    def _transform_result(self, result: dict[str, Any]) -> Award:
        """Transforms a single API result item into an Award model.

        The child awards are contracts/delivery orders, so we use the
        award factory to create the appropriate Award subclass.
        """
        from ..models.award_factory import create_award

        return create_award(result, self._client)

    def count(self) -> int:
        """Count the number of child awards for the IDV.

        Since the IDV awards endpoint doesn't provide a dedicated count API,
        we iterate through all pages to get the count.

        Returns:
            int: The total number of child awards.
        """
        logger.debug(f"{self.__class__.__name__}.count() called for {self._award_id}")

        # Iterate through all results to count
        count = 0
        for _ in self:
            count += 1

        logger.info(
            f"{self.__class__.__name__}.count() = {count} child awards for IDV {self._award_id}"
        )
        return count

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def order_by(self, field: str, direction: str = "desc") -> IDVChildAwardsSearch:
        """Set the sort order for results.

        Args:
            field: The field to sort by. Can be a user-friendly name or API field name.
                   User-friendly names include:
                   - 'award_type', 'description', 'funding_agency', 'awarding_agency'
                   - 'obligated_amount', 'obligation', 'start_date', 'end_date'
                   - 'piid', 'last_date_to_order'
            direction: Sort direction - 'asc' or 'desc' (default: 'desc')

        Returns:
            A new IDVChildAwardsSearch instance with the sort configuration applied.

        Raises:
            ValidationError: If the sort direction or field is invalid.
        """
        if direction not in ["asc", "desc"]:
            raise ValidationError(f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'.")

        # Map user-friendly field names to API field names
        api_field = self.SORT_FIELD_MAP.get(field.lower(), field)

        # Validate that the field is supported by the API
        valid_api_fields = list(self.SORT_FIELD_MAP.values())

        if api_field not in valid_api_fields:
            raise ValidationError(
                f"Invalid sort field: {field}. "
                f"Valid fields are: {', '.join(self.SORT_FIELD_MAP.keys())}"
            )

        clone = self._clone()
        clone._sort_field = api_field
        clone._sort_order = direction
        return clone

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
