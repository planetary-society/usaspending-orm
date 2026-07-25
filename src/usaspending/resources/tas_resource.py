"""TAS resource implementation."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger
from .base_resource import BaseResource

if TYPE_CHECKING:
    from ..models.agency import Agency

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
    def agencies(self) -> list[Agency]:
        """List all agencies with TAS codes.

        Returns a list of Agency model instances for agencies that have
        at least one Treasury Account Symbol affiliated with them.

        Cached, because reading an attribute should not issue a request every
        time it is touched. The list is a reference table that changes rarely,
        and the resource itself lives as long as the client.

        Returns:
            List of Agency model instances.

        Example:
            >>> agencies = client.tas.agencies
            >>> for agency in agencies:
            ...     print(
            ...         f"{agency.code}: {agency.name} ({agency.federal_accounts.count()} accounts)"
            ...     )
        """
        logger.debug("Fetching TAS agencies")
        from ..queries.tas_agencies_query import TASAgenciesQuery

        return TASAgenciesQuery(self._client).all()
