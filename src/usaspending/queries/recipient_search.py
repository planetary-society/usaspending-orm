"""Recipient search query builder."""

from __future__ import annotations
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from ..models.recipient import Recipient


class RecipientSearch(QueryBuilder["Recipient"]):
    """Query builder for recipient searches."""
    
    def _endpoint(self) -> str:
        return "/search/spending_by_recipient/"
    
    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Build API payload for recipient search."""
        payload = {
            "filters": self._filters,
            "limit": self._limit,
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
    
    def for_agency(self, agency: str, account: Optional[str] = None) -> "RecipientSearch":
        """Filter recipients by funding agency.
        
        Reuses the same logic as AwardSearch for consistency.
        """
        # Same implementation as AwardSearch.for_agency()
        # (Could be extracted to a mixin for DRY)
        clone = self._clone()
        
        # Agency lookup logic (same as above)
        from ..plugins.base import AgencyPlugin
        agency_plugins = self._client.plugins.get_by_type(AgencyPlugin)
        
        agency_code = agency
        agency_name = agency
        account_code = None
        
        for plugin in agency_plugins.values():
            if agency.upper() in (
                plugin.agency_name.upper(),
                plugin.abbreviation.upper(),
                plugin.agency_code
            ):
                agency_code = plugin.agency_code
                agency_name = plugin.agency_name
                
                if account:
                    account_code = plugin.get_account_code(account)
                break
        
        clone._filters.setdefault("agencies", []).append({
            "type": "funding",
            "tier": "toptier",
            "toptier_code": agency_code,
            "name": agency_name,
        })
        
        if account_code:
            clone._filters.setdefault("tas_codes", []).append({
                "aid": agency_code,
                "main": account_code
            })
        
        return clone
    
    def with_business_type(self, *types: str) -> "RecipientSearch":
        """Filter by recipient business type.
        
        Args:
            *types: Business type codes or names
            
        Returns:
            New query builder with business type filter
        """
        clone = self._clone()
        clone._filters["recipient_type_names"] = list(types)
        return clone
    
    def top_recipients(self, num: int = 100) -> "RecipientSearch":
        """Get top recipients by total obligations.
        
        Args:
            num: Number of top recipients to return
            
        Returns:
            New query builder configured for top recipients
        """
        return self.limit(num).order_by("amount", "desc")