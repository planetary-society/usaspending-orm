"""Agency resource implementation."""

from __future__ import annotations

import warnings
from itertools import chain
from typing import TYPE_CHECKING

from ..config import config
from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..utils.validations import validate_toptier_code
from .base_resource import BaseResource

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..models.agency import Agency
    from ..queries.agencies_search import AgenciesSearch
    from ..queries.sub_agency_query import SubAgencyQuery

logger = USASpendingLogger.get_logger(__name__)


class AgencyResource(BaseResource):
    """Resource for agency-related operations.

    Provides access to agency overview and detail endpoints.
    """

    def __init__(self, client: USASpendingClient):
        """Initialize the resource with an empty agency-code crosswalk cache.

        Args:
            client: USASpendingClient client instance.
        """
        super().__init__(client)
        self._toptier_codes: dict[str, dict[str, str]] = {}

    def _toptier_code_for_id(self, agency_id: str | int) -> str | None:
        """Resolve a top-tier database ID without confusing it with a Treasury code."""
        codes = self._toptier_codes.get(config.base_url)
        if codes is None:
            codes = {}
            for agency_type in ("award_agencies", "account_agencies"):
                agencies = self._client._make_request(
                    "POST", "/bulk_download/list_agencies/", json={"type": agency_type}
                )["agencies"]
                for agency in chain(agencies["cfo_agencies"], agencies["other_agencies"]):
                    # One malformed upstream row must not make every ID unresolvable.
                    try:
                        code = validate_toptier_code(agency.get("toptier_code"))
                    except ValidationError:
                        logger.warning(f"Skipping agency with invalid toptier code: {agency}")
                        continue
                    codes[str(agency["toptier_agency_id"])] = code
            # Publish only the complete crosswalk so a failed fetch remains retryable.
            self._toptier_codes[config.base_url] = codes
        return codes.get(str(agency_id))

    def search(self) -> AgenciesSearch:
        """Create a new agency autocomplete query builder.

        Returns:
            AgenciesSearch query builder for chaining filters

        Example:
            >>> agencies = (
            ...     client.agencies.search()
            ...     .name("National Aeronautics and Space Administration")
            ...     .agency_type("funding")
            ... )
            >>> offices = (
            ...     client.agencies.search()
            ...     .name("National Aeronautics and Space Administration")
            ...     .agency_type("awarding")
            ...     .office()
            ... )
        """
        from ..queries.agencies_search import AgenciesSearch

        return AgenciesSearch(self._client)

    def find_by_toptier_code(self, toptier_code: str, fiscal_year: int | None = None) -> Agency:
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
            >>> agency = client.agencies.find_by_toptier_code(
            ...     "080"
            ... )  # Get NASA for current fiscal year
            >>> print(agency.name, agency.mission)
            >>>
            >>> agency_2023 = client.agencies.find_by_toptier_code(
            ...     "080", fiscal_year=2023
            ... )  # Get NASA for FY 2023
            >>> print(agency_2023.fiscal_year, agency_2023.def_codes)
        """
        logger.debug(
            f"Retrieving agency overview for toptier_code: {toptier_code}, "
            f"fiscal_year: {fiscal_year}"
        )

        from ..queries.agency_query import AgencyQuery

        return AgencyQuery(self._client).find_by_id(toptier_code, fiscal_year)

    def subagencies(self, toptier_code: str) -> SubAgencyQuery:
        """Create a SubAgencyQuery builder for the given toptier agency.

        Args:
            toptier_code: The toptier code of the agency (3-4 digit string).

        Returns:
            SubAgencyQuery builder for chaining filters and iteration.

        Example:
            >>> # Get all subagencies for NASA
            >>> subagencies = client.agencies.subagencies("080").all()
            >>>
            >>> # Get subagencies with filters
            >>> results = (
            ...     client.agencies.subagencies("080")
            ...     .fiscal_year(2024)
            ...     .order_by("name", "asc")
            ...     .all()
            ... )
        """
        from ..queries.sub_agency_query import SubAgencyQuery

        return SubAgencyQuery(self._client, toptier_code)

    def find_all_funding_agencies_by_name(self, name: str) -> AgenciesSearch:
        """Search for funding agencies and offices by name.

        Deprecated: Use search().name(name).agency_type("funding") instead.

        Args:
            name: Search text to match against agency/office names

        Returns:
            AgenciesSearch query builder for iteration and filtering

        Example:
            >>> # Get all matches (agencies, subtiers, offices)
            >>> all_results = client.agencies.find_all_funding_agencies_by_name(
            ...     "National Aeronautics and Space Administration"
            ... ).all()
            >>>
            >>> # Get only toptier agencies
            >>> agencies = (
            ...     client.agencies.find_all_funding_agencies_by_name(
            ...         "National Aeronautics and Space Administration"
            ...     )
            ...     .toptier()
            ...     .all()
            ... )
            >>>
            >>> # Get only subtier agencies
            >>> subtiers = (
            ...     client.agencies.find_all_funding_agencies_by_name(
            ...         "National Aeronautics and Space Administration"
            ...     )
            ...     .subtier()
            ...     .all()
            ... )
            >>>
            >>> # Get only offices
            >>> offices = (
            ...     client.agencies.find_all_funding_agencies_by_name(
            ...         "National Aeronautics and Space Administration"
            ...     )
            ...     .office()
            ...     .all()
            ... )
        """
        warnings.warn(
            "find_all_funding_agencies_by_name is deprecated. "
            "Use search().name(name).agency_type('funding') instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        return self.search().name(name).agency_type("funding")

    def find_all_awarding_agencies_by_name(self, name: str) -> AgenciesSearch:
        """Search for funding agencies and offices by name.

        Deprecated: Use search().name(name).agency_type("awarding") instead.

        Args:
            name: Search text to match against agency/office names

        Returns:
            AgenciesSearch query builder for iteration and filtering

        Example:
            >>> # Get all matches (agencies, subtiers, offices)
            >>> all_results = client.agencies.find_all_awarding_agencies_by_name(
            ...     "National Aeronautics and Space Administration"
            ... ).all()
            >>>
            >>> # Get only toptier agencies
            >>> agencies = (
            ...     client.agencies.find_all_awarding_agencies_by_name(
            ...         "National Aeronautics and Space Administration"
            ...     )
            ...     .toptier()
            ...     .all()
            ... )
            >>>
            >>> # Get only subtier agencies
            >>> subtiers = (
            ...     client.agencies.find_all_awarding_agencies_by_name(
            ...         "National Aeronautics and Space Administration"
            ...     )
            ...     .subtier()
            ...     .all()
            ... )
            >>>
            >>> # Get only offices
            >>> offices = (
            ...     client.agencies.find_all_awarding_agencies_by_name(
            ...         "National Aeronautics and Space Administration"
            ...     )
            ...     .office()
            ...     .all()
            ... )
        """
        warnings.warn(
            "find_all_awarding_agencies_by_name is deprecated. "
            "Use search().name(name).agency_type('awarding') instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        return self.search().name(name).agency_type("awarding")
