"""Agencies search query implementation for awarding agency/office autocomplete."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger
from .agencies_search import AgenciesSearch

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class AwardingAgenciesSearch(AgenciesSearch):
    """Search for awarding agencies and offices by name.

    Deprecated: Use AgenciesSearch().agency_type("awarding") instead.
    """

    def __init__(self, client: USASpendingClient, warn: bool = True):
        """Initialize AwardingAgenciesSearch with client.

        Args:
            client: USASpending client instance.
            warn: Whether to emit a deprecation warning.
        """
        if warn:
            warnings.warn(
                "AwardingAgenciesSearch is deprecated. "
                "Use AgenciesSearch().agency_type('awarding') instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        super().__init__(client, agency_type="awarding")

    def _clone(self) -> AwardingAgenciesSearch:
        """Create immutable copy for chaining without extra warnings."""
        clone = self.__class__(self._client, warn=False)
        clone._filter_objects = self._filter_objects.copy()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        clone._agency_type = self._agency_type
        clone._search_text = self._search_text
        clone._limit = self._limit
        clone._result_type = self._result_type
        return clone
