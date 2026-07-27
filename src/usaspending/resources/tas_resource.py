"""TAS resource implementation."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger
from .base_resource import BaseResource

if TYPE_CHECKING:
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
    def agencies(self) -> TASAgenciesQuery:
        """Agencies that have Treasury Account Symbols.

        Returns a query rather than a list, matching the two levels below it in
        the same tree: :attr:`Agency.federal_accounts` and
        :attr:`FederalAccount.tas_codes` are both queries. Iteration, ``len()``,
        indexing and slicing all work directly on it, and ``all()`` gives a list
        when one is wanted.

        Handing back a query also means there is no shared list to corrupt. The
        query holds the fetched level, so filtering and repeated reads cost no
        further requests, while every ``all()`` builds a fresh list.

        Returns:
            TASAgenciesQuery: Query supporting ``code()``, ``codes()`` and
            ``description()``.

        Example:
            >>> for agency in client.tas.agencies:
            ...     print(f"{agency.code}: {agency.name}")
            >>> len(client.tas.agencies)
            91
            >>> nasa = client.tas.agencies.code("080").first()
            >>> universities = client.tas.agencies.description("university").all()
        """
        logger.debug("Creating TAS agencies query")
        from ..queries.tas_agencies_query import TASAgenciesQuery

        return TASAgenciesQuery(self._client)
