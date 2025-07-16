"""Award search query builder."""

from __future__ import annotations
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from .query_builder import QueryBuilder
from ..exceptions import ValidationError

if TYPE_CHECKING:
    from ..models.award import Award
    from ..plugins.base import AgencyPlugin

class AwardsSearch(QueryBuilder["Award"]):
    """Query builder for award searches."""
    
    @property
    def _endpoint(self) -> str:
        return "/search/spending_by_award/"
    
    def _build_payload(self, page: int) -> Dict[str, Any]:
        """Build API payload for award search."""
        payload = {
            "filters": self._filters,
            "limit": self._limit,
            "page": page,
            "fields": [
                "Award ID",
                "Recipient Name", 
                "Start Date",
                "End Date",
                "Award Amount",
                "Description",
                "generated_unique_award_id",
                "recipient_id",
            ],
        }
        
        if self._order_by:
            payload["sort"] = self._order_by
            payload["order"] = self._order_direction
            
        return payload
    
    def _transform_result(self, data: Dict[str, Any]) -> "Award":
        """Transform result to Award model."""
        from ..models.award import Award
        return Award(data, client=self._client)
    
    def for_agency(self, agency: str, account: Optional[str] = None) -> "AwardsSearch":
        """Filter by funding agency with optional account.
        
        Args:
            agency: Agency name, abbreviation, or TAS code
            account: Optional account name (e.g., "Science", "Exploration")
            
        Returns:
            New query builder with agency filter
            
        Example:
            >>> # Using plugin data
            >>> awards = client.awards.search().for_agency("NASA", account="Science")
            >>> 
            >>> # Or directly with codes
            >>> awards = client.awards.search().for_agency("080")
        """
        clone = self._clone()
        
        # Try to get agency info from plugins
        agency_code = agency
        agency_name = agency
        account_code = None
        
        # Check all registered agency plugins
        from ..plugins.base import AgencyPlugin
        agency_plugins = self._client.plugins.get_by_type(AgencyPlugin)
        
        for plugin in agency_plugins.values():
            # Match by name, abbreviation, or code
            if agency.upper() in (
                plugin.agency_name.upper(),
                plugin.abbreviation.upper(),
                plugin.agency_code
            ):
                agency_code = plugin.agency_code
                agency_name = plugin.agency_name
                
                # Get account code if specified
                if account:
                    account_code = plugin.get_account_code(account)
                    if not account_code:
                        raise ValidationError(
                            f"Unknown account '{account}' for {plugin.abbreviation}"
                        )
                break
        
        # Add agency filter
        clone._filters.setdefault("agencies", []).append({
            "type": "funding",
            "tier": "toptier",
            "toptier_code": agency_code,
            "name": agency_name,
        })
        
        # Add account filter if specified
        if account_code:
            clone._filters.setdefault("tas_codes", []).append({
                "aid": agency_code,
                "main": account_code
            })
        
        return clone
    
    def in_state(self, state: str) -> "AwardsSearch":
        """Filter by state.
        
        Args:
            state: Two-letter state code
            
        Returns:
            New query builder with state filter
        """
        clone = self._clone()
        clone._filters.setdefault("place_of_performance_locations", []).append({
            "country": "USA",
            "state": state.upper(),
        })
        return clone
    
    def in_district(self, district: str) -> "AwardsSearch":
        """Add congressional district to state filter.
        
        Args:
            district: Two-digit district code
            
        Returns:
            New query builder with district filter
            
        Note:
            Must be called after in_state()
        """
        clone = self._clone()
        locations = clone._filters.get("place_of_performance_locations", [])
        
        if not locations:
            raise ValidationError("Must call in_state() before in_district()")
        
        # Add district to the last location filter
        locations[-1]["congressional_code"] = district
        return clone
    
    def near_nasa_center(self, center_code: str) -> "AwardsSearch":
        """Filter by proximity to a NASA center.
        
        Args:
            center_code: NASA center code (e.g., "JSC", "KSC", "JPL")
            
        Returns:
            New query builder filtered by center's state
        """
        clone = self._clone()
        
        # Get NASA plugin
        nasa_plugin = self._client.get_plugin("nasa")
        if not nasa_plugin:
            raise ValidationError("NASA plugin not registered")
        
        # Find center
        centers = nasa_plugin.get_major_centers()
        center = next(
            (c for c in centers if c["code"].upper() == center_code.upper()),
            None
        )
        
        if not center:
            raise ValidationError(f"Unknown NASA center: {center_code}")
        
        # Filter by center's state
        return clone.in_state(center["state"])
    
    def fiscal_years(self, *years: int) -> "AwardsSearch":
        """Filter by fiscal years.
        
        Args:
            *years: One or more fiscal years
            
        Returns:
            New query builder with fiscal year filter
        """
        clone = self._clone()
        time_periods = []
        
        for year in years:
            time_periods.append({
                "start_date": f"{year-1}-10-01",
                "end_date": f"{year}-09-30",
            })
        
        clone._filters["time_period"] = time_periods
        return clone
    
    def award_type(self, *types: str) -> "AwardsSearch":
        """Filter by award type.
        
        Args:
            *types: Award types ("contracts", "grants", "loans", etc.)
            
        Returns:
            New query builder with award type filter
        """
        clone = self._clone()
        
        # Map friendly names to codes
        type_mapping = {
            "contracts": ["A", "B", "C", "D"],
            "grants": ["02", "03", "04", "05"],
            "loans": ["07", "08"],
            "direct_payments": ["06", "10"],
        }
        
        codes = []
        for t in types:
            if t in type_mapping:
                codes.extend(type_mapping[t])
            else:
                codes.append(t)  # Assume it's already a code
        
        clone._filters["award_type_codes"] = codes
        return clone