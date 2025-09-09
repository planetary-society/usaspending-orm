"""Agency resource implementation."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..models.agency import Agency
    from ..queries.funding_agencies_search import FundingAgenciesSearch
    from ..queries.awarding_agencies_search import AwardingAgenciesSearch

logger = USASpendingLogger.get_logger(__name__)


class AgencyResource(BaseResource):
    """Resource for agency-related operations.

    Provides access to agency overview and detail endpoints.
    """

    def find_by_toptier_code(
        self, toptier_code: str, fiscal_year: Optional[int] = None
    ) -> "Agency":
        """Retrieve agency overview for a specific toptier code and fiscal year.

        Args:
            toptier_code: The toptier code of an agency (3-4 digit string)
            fiscal_year: Optional fiscal year for the data (defaults to current)

        Returns:
            Agency model instance with full details

        Raises:
            ValidationError: If toptier_code is invalid
            APIError: If agency not found

        Example:
            >>> agency = client.agencies.find_by_toptier_code("080")  # Get NASA for current fiscal year
            >>> print(agency.name, agency.mission)
            >>>
            >>> agency_2023 = client.agencies.find_by_toptier_code("080", fiscal_year=2023)  # Get NASA for FY 2023
            >>> print(agency_2023.fiscal_year, agency_2023.def_codes)
        """
        logger.debug(
            f"Retrieving agency overview for toptier_code: {toptier_code}, "
            f"fiscal_year: {fiscal_year}"
        )

        from ..queries.agency_query import AgencyQuery

        return AgencyQuery(self._client).find_by_id(toptier_code, fiscal_year)

    def find_all_funding_agencies_by_name(self, name: str) -> "FundingAgenciesSearch":
        """Search for funding agencies and offices by name.

        Args:
            name: Search text to match against agency/office names

        Returns:
            FundingAgenciesSearch query builder for iteration and filtering

        Example:
            >>> # Get all matches (agencies, subtiers, offices)
            >>> all_results = list(client.agencies.find_all_funding_agencies_by_name("NASA"))
            >>>
            >>> # Get only toptier agencies
            >>> agencies = list(client.agencies.find_all_funding_agencies_by_name("NASA").toptier())
            >>>
            >>> # Get only subtier agencies
            >>> subtiers = list(client.agencies.find_all_funding_agencies_by_name("NASA").subtier())
            >>>
            >>> # Get only offices
            >>> offices = list(client.agencies.find_all_funding_agencies_by_name("NASA").office())
        """
        from ..queries.funding_agencies_search import FundingAgenciesSearch

        return FundingAgenciesSearch(self._client).with_search_text(name)

    def find_all_awarding_agencies_by_name(self, name: str) -> "AwardingAgenciesSearch":
        """Search for funding agencies and offices by name.

        Args:
            name: Search text to match against agency/office names

        Returns:
            AwardingAgenciesSearch query builder for iteration and filtering

        Example:
            >>> # Get all matches (agencies, subtiers, offices)
            >>> all_results = list(client.agencies.find_all_awarding_agencies_by_name("NASA"))
            >>>
            >>> # Get only toptier agencies
            >>> agencies = list(client.agencies.find_all_awarding_agencies_by_name("NASA").toptier())
            >>>
            >>> # Get only subtier agencies
            >>> subtiers = list(client.agencies.find_all_awarding_agencies_by_name("NASA").subtier())
            >>>
            >>> # Get only offices
            >>> offices = list(client.agencies.find_all_awarding_agencies_by_name("NASA").office())
        """
        from ..queries.awarding_agencies_search import AwardingAgenciesSearch

        return AwardingAgenciesSearch(self._client).with_search_text(name)
