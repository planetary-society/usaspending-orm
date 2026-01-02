"""TAS resource implementation."""

from __future__ import annotations

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

    @property
    def agencies(self) -> list[Agency]:
        """List all agencies with TAS codes.

        Returns a list of Agency model instances for agencies that have
        at least one Treasury Account Symbol affiliated with them.

        Returns:
            List of Agency model instances.

        Example:
            >>> agencies = client.tas.agencies
            >>> for agency in agencies:
            ...     print(f"{agency.code}: {agency.name} ({agency.federal_accounts.count()} accounts)")
        """
        logger.debug("Fetching TAS agencies")

        response = self._client._make_request("GET", self.ENDPOINT)
        results = response.get("results", [])

        from ..models.agency import Agency

        agencies = []
        for data in results:
            if not isinstance(data, dict):
                continue

            # Transform filter tree node data to Agency-compatible format
            agency_data = {
                "toptier_code": data.get("id"),
                "code": data.get("id"),
                "name": data.get("description"),
                # Include the TAS count for reference
                "_tas_count": data.get("count", 0),
            }

            agencies.append(Agency(agency_data, self._client))

        logger.debug("Fetched %d TAS agencies", len(agencies))

        return agencies
