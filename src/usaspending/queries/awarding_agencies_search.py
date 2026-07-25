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

    def _new_instance(self) -> AwardingAgenciesSearch:
        """Reconstruct without re-emitting the deprecation warning.

        Chaining clones the builder, so warning here would fire once per filter
        call rather than once per construction.
        """
        return self.__class__(self._client, warn=False)
