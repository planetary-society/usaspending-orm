"""Agencies search query implementation for awarding agency/office autocomplete."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .agencies_search import AgenciesSearch
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class AwardingAgenciesSearch(AgenciesSearch):
    """Search for awarding agencies and offices by name."""

    @property
    def _endpoint(self) -> str:
        """API endpoint for agency autocomplete."""
        return "/autocomplete/awarding_agency_office/"
