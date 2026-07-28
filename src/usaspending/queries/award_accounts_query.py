"""Award accounts query builder for USASpending data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ..logging_config import USASpendingLogger
from .mixins import AwardScopedQuery, SortableQuery
from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from ..models.award_account import AwardAccount

logger = USASpendingLogger.get_logger(__name__)


class AwardAccountsQuery(AwardScopedQuery, SortableQuery, QueryBuilder["AwardAccount"]):
    """Builds and executes an award accounts query.

    Retrieves federal accounts associated with a specific award,
    including funding agency information and obligated amounts.

    Example:
        >>> # Get accounts for an award
        >>> accounts = client.award_accounts.award_id("CONT_AWD_123...")
        >>> for account in accounts:
        ...     print(f"{account.code}: ${account.obligated_amount or 0:,.2f}")
        >>>
        >>> # Get count
        >>> count = accounts.count()
        >>>
        >>> # Sort by amount
        >>> sorted_accounts = accounts.order_by("amount", "desc").all()
    """

    _sort_field: str = "federal_account"

    # Map user-friendly sort field names to API field names
    SORT_FIELD_MAP: ClassVar[dict[str, str]] = {
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

    @property
    def _endpoint(self) -> str:
        """The API endpoint for this query."""
        return "/awards/accounts/"

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Constructs the final API request payload."""
        return {
            "award_id": self._require_award_id(),
            "limit": self._get_effective_page_size(),
            "page": page,
            **self._sort_payload(),
        }

    def _transform_result(self, result: dict[str, Any]) -> AwardAccount:
        """Transforms a single API result item into an AwardAccount model."""
        from ..models.award_account import AwardAccount

        return AwardAccount(result, self._client)

    def _compute_raw_count(self) -> int:
        """Count the number of accounts for the award.

        Uses page_metadata.count from the API response for efficiency
        rather than iterating through all results.

        Returns:
            int: Total count of accounts.

        Raises:
            ValidationError: If award_id is not set.
        """
        self._require_award_id()

        return self._count_via_page_metadata("count")
