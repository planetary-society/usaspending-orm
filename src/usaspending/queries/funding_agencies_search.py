
"""Agencies search query implementation for funding agency/office autocomplete."""

from __future__ import annotations
from typing import TYPE_CHECKING
from .agencies_search import AgenciesSearch
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    pass

logger = USASpendingLogger.get_logger(__name__)

class FundingAgenciesSearch(AgenciesSearch):
    """ Search for funding agencies and offices by name."""
    
    @property
    def _endpoint(self) -> str:
        """API endpoint for agency autocomplete."""
        return "/autocomplete/funding_agency_office/"