"""Recipient search query builder."""

from __future__ import annotations
from typing import Dict, Any, Optional, TYPE_CHECKING

from .query_builder import QueryBuilder
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..models.recipient import Recipient

logger = USASpendingLogger.get_logger(__name__)


class SpendingByRecipientsSearch(QueryBuilder["Recipient"]):
    """Query builder for recipient searches."""

    @property
    def _endpoint(self) -> str:
        return "/search/spending_by_recipient/"

    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Build API payload for recipient search."""
        payload = {
            "filters": self._filters,
            "limit": self._get_effective_page_size(),
            "page": page,
            "category": "recipient",
            "subawards": False,
        }

        if self._order_by:
            payload["sort"] = self._order_by
            payload["order"] = self._order_direction

        return payload

    def _transform_result(self, data: Dict[str, Any]) -> "Recipient":
        """Transform result to Recipient model."""
        from ..models.recipient import Recipient

        return Recipient(data, client=self._client)

    def for_agency(
        self, agency: str, account: Optional[str] = None
    ) -> "SpendingByRecipientsSearch":
        """Filter recipients by funding agency.

        Args:
            agency: Agency code or name
            account: Optional account code

        Returns:
            New query builder with agency filter
        """
        clone = self._clone()

        # Use agency as provided - no plugin lookup
        agency_code = agency
        agency_name = agency

        clone._filters.setdefault("agencies", []).append(
            {
                "type": "funding",
                "tier": "toptier",
                "toptier_code": agency_code,
                "name": agency_name,
            }
        )

        if account:
            clone._filters.setdefault("tas_codes", []).append(
                {"aid": agency_code, "main": account}
            )

        return clone

    def with_business_type(self, *types: str) -> "SpendingByRecipientsSearch":
        """Filter by recipient business type.

        Args:
            *types: Business type codes or names

        Returns:
            New query builder with business type filter
        """
        clone = self._clone()
        clone._filters["recipient_type_names"] = list(types)
        return clone

    def top_recipients(self, num: int = 100) -> "SpendingByRecipientsSearch":
        """Get top recipients by total obligations.

        Args:
            num: Number of top recipients to return

        Returns:
            New query builder configured for top recipients
        """
        return self.page_size(min(num, 100)).limit(num).order_by("amount", "desc")

    def count(self) -> int:
        """Get total count of recipients.

        Since there's no dedicated count endpoint for recipients,
        this method counts by iterating through all results.

        Returns:
            Total number of matching recipients
        """
        logger.debug(f"{self.__class__.__name__}.count() called")

        count = 0
        for _ in self:
            count += 1

        logger.info(f"{self.__class__.__name__}.count() = {count} recipients")
        return count
