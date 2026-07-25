"""Agency award summary query implementation for retrieving award aggregations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..utils.validations import validate_toptier_code

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class AgencyAwardSummary:
    """Retrieve agency award summary data from the USAspending API.

    This query class handles fetching aggregated award information including
    transaction counts and obligations filtered by fiscal year, agency type,
    and award type codes.

    Note:
        Deliberately not a ``SingleResourceBase``. That base exists for
        "fetch one model by id" endpoints, and this one returns an aggregate
        dictionary rather than a resource, so it satisfied the base's
        ``find_by_id`` contract only by raising ``NotImplementedError``. It uses
        nothing else from the base, so composing a client directly is both
        simpler and honest about what this is.
    """

    def __init__(self, client: USASpendingClient):
        """Initialize AgencyAwardSummary with client.

        Args:
            client: USASpendingClient client instance
        """
        self._client = client
        logger.debug("AgencyAwardSummary initialized with client: %s", client)

    def get_awards_summary(
        self,
        toptier_code: str,
        fiscal_year: int | None = None,
        agency_type: str = "awarding",
        award_type_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve agency award summary with optional filters.

        Args:
            toptier_code: The toptier code of an agency (3-4 digit string)
            fiscal_year: Optional fiscal year for the data (defaults to current)
            agency_type: "awarding" or "funding" (defaults to "awarding")
            award_type_codes: Optional list of award type codes to filter by

        Returns:
            Dictionary containing:
                - toptier_code: Agency toptier code
                - fiscal_year: Fiscal year of data
                - latest_action_date: Latest transaction date
                - transaction_count: Number of transactions
                - obligations: Total obligations amount
                - messages: Any API messages

        Raises:
            ValidationError: If toptier_code is invalid or agency_type is invalid
            APIError: If API request fails
        """
        toptier_code = validate_toptier_code(toptier_code)

        # Validate agency_type
        if agency_type not in ["awarding", "funding"]:
            raise ValidationError(
                f"Invalid agency_type: {agency_type}. Must be 'awarding' or 'funding'"
            )

        logger.debug(
            "Fetching award summary for toptier_code: %s, fiscal_year: %s, "
            "agency_type: %s, award_type_codes: %s",
            toptier_code,
            fiscal_year,
            agency_type,
            award_type_codes,
        )

        # Build params
        params = {"agency_type": agency_type}

        if fiscal_year is not None:
            params["fiscal_year"] = fiscal_year

        if award_type_codes:
            # Convert to list if needed and filter out None/empty values
            if isinstance(award_type_codes, (set, frozenset)):
                award_type_codes = list(award_type_codes)
            award_type_codes = [code for code in award_type_codes if code]

            if award_type_codes:
                # API expects award_type_codes as array parameter
                params["award_type_codes"] = award_type_codes

        endpoint = f"/agency/{toptier_code}/awards/"

        return self._client._make_request("GET", endpoint, params=params)
