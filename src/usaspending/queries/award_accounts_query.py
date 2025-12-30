"""Award accounts query builder for USASpending data."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from ..exceptions import ValidationError
from .query_builder import QueryBuilder
from ..logging_config import USASpendingLogger
from ..utils.validations import validate_non_empty_string

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.award_account import AwardAccount

logger = USASpendingLogger.get_logger(__name__)


class AwardAccountsQuery(QueryBuilder["AwardAccount"]):
    """Builds and executes an award accounts query.

    Retrieves federal accounts associated with a specific award,
    including funding agency information and obligated amounts.

    Example:
        >>> # Get accounts for an award
        >>> accounts = client.award_accounts.award_id("CONT_AWD_123...")
        >>> for account in accounts:
        ...     print(f"{account.code}: ${account.obligated_amount:,.2f}")
        >>>
        >>> # Get count
        >>> count = accounts.count()
        >>>
        >>> # Sort by amount
        >>> sorted_accounts = accounts.order_by("amount", "desc").all()
    """

    # Map user-friendly sort field names to API field names
    SORT_FIELD_MAP = {
        "account_title": "account_title",
        "title": "account_title",
        "agency": "agency",
        "federal_account": "federal_account",
        "account": "federal_account",
        "code": "federal_account",
        "amount": "total_transaction_obligated_amount",
        "obligated_amount": "total_transaction_obligated_amount",
        "total_transaction_obligated_amount": "total_transaction_obligated_amount",
    }

    def __init__(self, client: "USASpendingClient"):
        """Initialize the AwardAccountsQuery.

        Args:
            client: The USASpending client instance.
        """
        super().__init__(client)
        self._award_id: Optional[str] = None
        self._sort_field: str = "federal_account"
        self._sort_order: str = "desc"
        self._cached_count: Optional[int] = None

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/awards/accounts/"

    def _clone(self) -> "AwardAccountsQuery":
        """Creates an immutable copy of the query builder."""
        clone = super()._clone()
        clone._award_id = self._award_id
        clone._sort_field = self._sort_field
        clone._sort_order = self._sort_order
        clone._cached_count = self._cached_count
        return clone

    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Constructs the final API request payload."""
        if not self._award_id:
            raise ValidationError(
                "An award_id is required. Use the .award_id() method."
            )

        payload = {
            "award_id": self._award_id,
            "limit": self._get_effective_page_size(),
            "page": page,
            "sort": self._sort_field,
            "order": self._sort_order,
        }

        return payload

    def _transform_result(self, result: Dict[str, Any]) -> "AwardAccount":
        """Transforms a single API result item into an AwardAccount model."""
        from ..models.award_account import AwardAccount

        return AwardAccount(result, self._client)

    def count(self) -> int:
        """Count the number of accounts for the award.

        Uses page_metadata.count from the API response for efficiency
        rather than iterating through all results.

        Returns:
            int: Total count of accounts.

        Raises:
            ValidationError: If award_id is not set.
        """
        logger.debug(f"{self.__class__.__name__}.count() called")

        if not self._award_id:
            raise ValidationError(
                "An award_id is required. Use the .award_id() method."
            )

        # Return cached count if available
        if self._cached_count is not None:
            return self._cached_count

        # Fetch first page to get count from page_metadata
        payload = self._build_payload(page=1)
        response = self._client._make_request("POST", self._endpoint, json=payload)

        page_metadata = response.get("page_metadata", {})
        count = page_metadata.get("count", 0)

        # Cache the count
        self._cached_count = count

        logger.info(
            f"{self.__class__.__name__}.count() = {count} accounts "
            f"for award {self._award_id}"
        )
        return count

    # ==========================================================================
    # Filter Methods
    # ==========================================================================

    def award_id(self, award_id: str) -> "AwardAccountsQuery":
        """Filter accounts for a specific award.

        Args:
            award_id: The unique award identifier (generated_unique_award_id).

        Returns:
            A new AwardAccountsQuery instance with the award filter applied.
        """
        validated_id = validate_non_empty_string(award_id, "award_id")

        clone = self._clone()
        clone._award_id = validated_id
        clone._cached_count = None  # Clear cache for new award
        return clone

    def order_by(self, field: str, direction: str = "desc") -> "AwardAccountsQuery":
        """Set the sort order for results.

        Args:
            field: The field to sort by. Can be a user-friendly name or API field name.
                   User-friendly names include:
                   - 'account_title', 'title' - Sort by account title
                   - 'agency' - Sort by agency
                   - 'federal_account', 'account', 'code' - Sort by federal account code
                   - 'amount', 'obligated_amount' - Sort by obligated amount
            direction: Sort direction - 'asc' or 'desc' (default: 'desc')

        Returns:
            A new AwardAccountsQuery instance with the sort configuration applied.

        Raises:
            ValidationError: If direction or field is invalid.
        """
        # Validate direction
        if direction not in ["asc", "desc"]:
            raise ValidationError(
                f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'."
            )

        # Map user-friendly field names to API field names
        api_field = self.SORT_FIELD_MAP.get(field.lower(), field)

        # Validate that the field is supported by the API
        valid_api_fields = [
            "account_title",
            "agency",
            "federal_account",
            "total_transaction_obligated_amount",
        ]

        if api_field not in valid_api_fields:
            raise ValidationError(
                f"Invalid sort field: {field}. "
                f"Valid fields are: {', '.join(self.SORT_FIELD_MAP.keys())}"
            )

        clone = self._clone()
        clone._sort_field = api_field
        clone._sort_order = direction
        return clone
