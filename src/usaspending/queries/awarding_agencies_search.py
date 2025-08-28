
"""Agencies search query implementation for awarding agency/office autocomplete."""

from __future__ import annotations
from typing import TYPE_CHECKING
from .agencies_search import AgenciesSearch
from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)

class AwardingAgenciesSearch(AgenciesSearch):
    """ Search for awarding agencies and offices by name."""
    
    @property
    def _endpoint(self) -> str:
        """API endpoint for agency autocomplete."""
        return "/v2/autocomplete/awarding_agency_office/"
    
    def _clone(self) -> 'AwardingAgenciesSearch':
        """Create immutable copy for chaining."""
        clone = AwardingAgenciesSearch(self._client)
        clone._search_text = self._search_text
        clone._limit = self._limit
        clone._result_type = self._result_type
        # Copy parent attributes
        clone._filters = self._filters.copy()
        clone._filter_objects = self._filter_objects.copy()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        return clone