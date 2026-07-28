"""Agencies search query implementation for funding agency/office autocomplete."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger
from .agencies_search import AgenciesSearch

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class FundingAgenciesSearch(AgenciesSearch):
    """Search for funding agencies and offices by name.

    Deprecated: Use AgenciesSearch().agency_type("funding") instead.
    """

    def __init__(self, client: USASpendingClient, warn: bool = True):
        """Initialize FundingAgenciesSearch with client.

        Args:
            client: USASpending client instance.
            warn: Whether to emit a deprecation warning.
        """
        if warn:
            warnings.warn(
                "FundingAgenciesSearch is deprecated. "
                "Use AgenciesSearch().agency_type('funding') instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        super().__init__(client, agency_type="funding")

    def _new_instance(self) -> FundingAgenciesSearch:
        """Reconstruct without re-emitting the deprecation warning.

        Chaining clones the builder, so warning here would fire once per filter
        call rather than once per construction.
        """
        return self.__class__(self._client, warn=False)
