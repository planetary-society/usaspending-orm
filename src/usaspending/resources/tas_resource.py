"""TAS resource implementation."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger
from .base_resource import BaseResource

if TYPE_CHECKING:
    from ..models.agency import Agency
    from ..queries.tas_agencies_query import TASAgenciesQuery

logger = USASpendingLogger.get_logger(__name__)


class TASResource(BaseResource):
    """Resource for TAS (Treasury Account Symbol) operations.

    Provides access to the TAS filter tree hierarchy, allowing discovery
    of agencies that have Treasury Account Symbols.

    Example:
        >>> # List all agencies with TAS
        >>> for agency in client.tas.agencies:
        ...     print(f"{agency.code}: {agency.name}")
        >>>
        >>> # Navigate to federal accounts from an agency
        >>> agency = client.agencies.find_by_toptier_code("080")
        >>> for account in agency.federal_accounts:
        ...     print(f"{account.code}: {account.title}")
    """

    ENDPOINT = "/references/filter_tree/tas/"

    @cached_property
    def _agencies_query(self) -> TASAgenciesQuery:
        """Query over the agencies that have Treasury Account Symbols.

        The query is what gets cached rather than its results: it fetches the
        level once and shares those results with every clone, so :attr:`agencies`
        can hand each caller its own list without re-requesting.

        Private for now. The query's ``code()``, ``codes()`` and ``description()``
        filters would be a genuine addition to this resource, but adding a public
        member is a deliberate act with tests and documentation behind it, not a
        side effect of fixing a caching bug.

        Returns:
            TASAgenciesQuery: Query over the TAS root level.
        """
        logger.debug("Creating TAS agencies query")
        from ..queries.tas_agencies_query import TASAgenciesQuery

        return TASAgenciesQuery(self._client)

    @property
    def agencies(self) -> list[Agency]:
        """List all agencies with TAS codes.

        Returns a list of Agency model instances for agencies that have
        at least one Treasury Account Symbol affiliated with them.

        Reading this repeatedly costs one request, not one per access, because the
        underlying query holds the fetched level. Each read returns a fresh list,
        so a caller that sorts or pops it cannot disturb the next one. The
        ``Agency`` models within it are shared between reads, as they were before,
        so mutating one is still visible to every reader.

        Returns:
            List of Agency model instances.

        Example:
            >>> agencies = client.tas.agencies
            >>> for agency in agencies:
            ...     print(
            ...         f"{agency.code}: {agency.name} ({agency.federal_accounts.count()} accounts)"
            ...     )
        """
        return self._agencies_query.all()
