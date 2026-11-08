"""TAS resource implementation."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from ..config import config
from ..logging_config import USASpendingLogger
from .base_resource import BaseResource

if TYPE_CHECKING:
    from ..client import USASpendingClient
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

    def __init__(self, client: USASpendingClient):
        """Initialize the resource with an empty account-parent cache.

        Args:
            client: USASpendingClient client instance.
        """
        super().__init__(client)
        self._parent_codes: dict[str, dict[str, str | None]] = {}

    def _parent_code_for_account(self, account_code: str) -> str | None:
        """Read an account's actual parent; its prefix need not be that agency's code."""
        parents = self._parent_codes.setdefault(config.base_url, {})
        if account_code not in parents:
            response = self._client._make_request(
                "GET", self.ENDPOINT, params={"filter": account_code, "depth": 1}
            )
            # The text filter also returns neighboring accounts; remember them too.
            for agency in response["results"]:
                for account in agency.get("children") or []:
                    parents.setdefault(account["id"], agency["id"])
            parents.setdefault(account_code, None)
        return parents[account_code]

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
