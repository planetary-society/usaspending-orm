"""NASA agency plugin."""

from __future__ import annotations
from typing import Dict, List, Optional

from .base import AgencyPlugin


class NASAPlugin(AgencyPlugin):
    """NASA-specific configuration and helpers.
    
    Provides NASA's TAS codes, subaccounts, and other
    agency-specific data for searches and analysis.
    """
    
    @property
    def agency_name(self) -> str:
        """Full agency name."""
        return "National Aeronautics and Space Administration"
    
    @property
    def agency_code(self) -> str:
        """Treasury Account Symbol (TAS) code."""
        return "080"
    
    @property
    def abbreviation(self) -> str:
        """Common abbreviation."""
        return "NASA"
    
    @property
    def subaccounts(self) -> Dict[str, str]:
        """NASA subaccount mapping.
        
        Returns:
            Dictionary mapping subaccount names to 4-digit codes
        """
        return {
            "Science": "0120",
            "Exploration": "0124",
            "Space Operations": "0115",
            "Space Technology": "0131",
            "Aeronautics": "0126",
            "STEM Education": "0128",
            "SSMS": "0122",  # Safety, Security, and Mission Services
            "Construction and Environmental Compliance and Restoration": "0130",
            "OIG": "0109"  # Office of Inspector General
        }
    
    def get_major_centers(self) -> List[Dict[str, str]]:
        """Get NASA's major centers.
        
        Returns:
            List of dictionaries with center information
        """
        return [
            {"name": "Ames Research Center", "code": "ARC", "state": "CA"},
            {"name": "Armstrong Flight Research Center", "code": "AFRC", "state": "CA"},
            {"name": "Glenn Research Center", "code": "GRC", "state": "OH"},
            {"name": "Goddard Space Flight Center", "code": "GSFC", "state": "MD"},
            {"name": "NASA Headquarters", "code": "HQ", "state": "DC"},
            {"name": "Jet Propulsion Laboratory", "code": "JPL", "state": "CA"},
            {"name": "Johnson Space Center", "code": "JSC", "state": "TX"},
            {"name": "Kennedy Space Center", "code": "KSC", "state": "FL"},
            {"name": "Langley Research Center", "code": "LaRC", "state": "VA"},
            {"name": "Marshall Space Flight Center", "code": "MSFC", "state": "AL"},
            {"name": "Stennis Space Center", "code": "SSC", "state": "MS"}
        ]
    
    def get_common_search_terms(self) -> List[str]:
        """Get common search terms for NASA contracts.
        
        Returns:
            List of search terms commonly used in NASA contracts
        """
        return [
            "spacecraft", "satellite", "launch", "propulsion",
            "avionics", "mission", "payload", "telescope",
            "research", "engineering", "analysis", "testing",
            "flight", "operations", "ground systems", "software"
        ]
    
    def get_fiscal_year_budget(self, fiscal_year: int) -> Optional[float]:
        """Get NASA's budget for a specific fiscal year.
        
        Args:
            fiscal_year: Federal fiscal year
            
        Returns:
            Budget in dollars or None if not available
        """
        # Known budgets (in billions)
        budgets = {
            2024: 24.875,
            2023: 25.384,
            2022: 23.953,
            2021: 23.271,
            2020: 22.629,
        }
        
        budget_billions = budgets.get(fiscal_year)
        return budget_billions * 1_000_000_000 if budget_billions else None
    
    def get_mission_directorates(self) -> Dict[str, List[str]]:
        """Get NASA's mission directorates and their subaccounts.
        
        Returns:
            Dictionary mapping directorate names to subaccount names
        """
        return {
            "Science Mission Directorate": ["Science"],
            "Exploration Systems Development": ["Exploration"],
            "Space Operations": ["Space Operations"],
            "Space Technology": ["Space Technology"],
            "Aeronautics Research": ["Aeronautics"],
            "STEM Engagement": ["STEM Education"],
            "Mission Support": ["SSMS", "Construction and Environmental Compliance and Restoration"],
            "Office of Inspector General": ["OIG"]
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive plugin information."""
        info = super().get_info()
        info.update({
            "centers": len(self.get_major_centers()),
            "mission_directorates": list(self.get_mission_directorates().keys()),
            "budget_years_available": [2020, 2021, 2022, 2023, 2024]
        })
        return info