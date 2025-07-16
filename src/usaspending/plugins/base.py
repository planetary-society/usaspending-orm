"""Base plugin interfaces."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class Plugin(ABC):
    """Base class for USASpending plugins."""
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information.
        
        Returns:
            Dictionary with plugin metadata
        """
        pass


class AgencyPlugin(Plugin):
    """Base class for agency-specific plugins.
    
    Provides agency configuration data like TAS codes,
    subaccounts, and common search parameters to be used with agency-specific filtering.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Full agency name."""
        pass
    
    @property
    @abstractmethod
    def tas_code(self) -> str:
        """Treasury Account Symbol (TAS) code."""
        pass
    
    @property
    @abstractmethod
    def abbreviation(self) -> str:
        """Common abbreviation."""
        pass
    
    @property
    def accounts(self) -> Dict[str, str]:
        """Subaccount name to code mapping.
        
        Returns:
            Dictionary mapping subaccount names to codes
        """
        return {}
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information."""
        return {
            "type": "agency",
            "name": self.name,
            "code": self.code,
            "abbreviation": self.abbreviation,
            "subaccounts": list(self.accounts.keys())
        }
    
    def get_account_code(self, name: str) -> Optional[str]:
        """Get subaccount code by name.
        
        Args:
            name: Subaccount name
            
        Returns:
            Subaccount code or None if not found
        """
        return self.subaccounts.get(name)
    
    def get_search_filters(self, subaccount: Optional[str] = None) -> Dict[str, Any]:
        """Get common search filters for this agency.
        
        Args:
            subaccount: Optional subaccount name
            
        Returns:
            Dictionary of search filters
        """
        filters = {
            "agencies": [{
                "name": self.name
            }]
        }
        
        # Add subaccount filter if specified
        if subaccount and subaccount in self.subaccounts:
            filters["tas_codes"] = [{
                "aid": self.tas_code,
                "main": self.accounts[subaccount]
            }]
        
        return filters