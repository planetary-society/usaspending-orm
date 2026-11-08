"""Subawards search query builder for USASpending data."""

from __future__ import annotations

import datetime
from typing import Any, ClassVar

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..models.award_types import get_award_group
from ..models.subaward import SubAward
from ..utils.validations import validate_non_empty_string
from .awards_search import AwardsSearch
from .filters import SimpleStringFilter

logger = USASpendingLogger.get_logger(__name__)


class SubAwardsSearch(AwardsSearch):
    """
    Builds and executes a subawards search query, allowing for complex
    filtering on subaward data. This class extends AwardsSearch to reuse
    filter logic while specializing for subawards.
    """

    _SPENDING_LEVEL_PAYLOAD: ClassVar[dict[str, Any]] = {
        "subawards": True,
        "spending_level": "subawards",
    }

    def _transform_result(self, result: dict[str, Any]) -> SubAward:
        """Transforms a single API result item into a SubAward model."""
        return SubAward(result, self._client)

    def _get_fields(self) -> list[str]:
        """
        Determines the list of fields to request based on award type filters.

        Returns different field sets depending on the award type codes:
        - Contracts: Contract subaward fields
        - Grants/Assistance: Grant subaward fields
        """
        # Get award type codes from filters
        award_types = self._get_award_type_codes()

        # Determine if we're dealing with contracts or grants
        is_contract = False
        is_grant = False

        # Check each award type code to determine categories
        for award_type in award_types:
            group = get_award_group(award_type)
            if group == "contract":
                is_contract = True
            elif group == "grant":
                is_grant = True

        # Return appropriate field set
        if is_contract and not is_grant:
            return SubAward.CONTRACT_SUBAWARD_FIELDS.copy()
        elif is_grant and not is_contract:
            return SubAward.GRANT_SUBAWARD_FIELDS.copy()
        else:
            # If both or neither, return union of both field sets
            fields = set(SubAward.CONTRACT_SUBAWARD_FIELDS)
            fields.update(SubAward.GRANT_SUBAWARD_FIELDS)
            return list(fields)

    def _compute_raw_count(self) -> int:
        """Count matching subawards in one request, including every filter."""
        filters = self._aggregate_filters()
        # One prime award implies its type; only then may the type filter be absent.
        if "award_unique_id" not in filters and "award_type_codes" not in filters:
            self._require_award_type_filters()  # raises the shared missing-type error
        counts = self.count_awards_by_type(filters=filters)
        return counts.get("subcontracts", 0) + counts.get("subgrants", 0)

    def award_id(self, award_id: str) -> SubAwardsSearch:
        """
        Filter subawards for a specific prime award.

        Args:
            award_id: The unique generated award identifier.

        Returns:
            A new SubAwardsSearch instance with the award filter applied.

        Example:
            >>> subawards = client.subawards.award_id("CONT_AWD_123...")
            >>> for sub in subawards:
            ...     print(f"{sub.sub_awardee_name}: ${sub.sub_award_amount or 0:,.2f}")
        """
        return self._with_filter(
            SimpleStringFilter(
                key="award_unique_id", value=validate_non_empty_string(award_id, "award_id")
            )
        )

    def time_period(
        self,
        start_date: datetime.date | str,
        end_date: datetime.date | str,
        new_awards_only: bool = False,
        date_type: str | None = None,
    ) -> SubAwardsSearch:
        """
        Filter subawards by a specific date range.

        Per API documentation, subaward searches only support the following date types:
        - action_date (default)
        - last_modified_date

        Args:
            start_date: The start date of the period.
            end_date: The end date of the period.
            new_awards_only: NOT SUPPORTED for subawards. Will raise an error if True.
            date_type: The type of date to filter on. Only "action_date" or
                "last_modified_date" are valid for subawards.

        Returns:
            SubAwardsSearch: A new instance with the time period filter applied.

        Raises:
            ValidationError: If new_awards_only is True or date_type is invalid.

        Example:
            >>> subawards = client.subawards.contracts().time_period("2024-01-01", "2024-12-31")
        """
        # Validate subaward-specific restrictions
        if new_awards_only:
            raise ValidationError(
                "new_awards_only is not supported for subaward searches. "
                "This filter is only available for award searches."
            )

        # Validate date_type if provided
        if date_type:
            valid_subaward_date_types = {"action_date", "last_modified_date"}
            date_type_lower = date_type.lower().replace("_", "")
            normalized = (
                "action_date"
                if date_type_lower == "actiondate"
                else (
                    "last_modified_date"
                    if date_type_lower in ("lastmodified", "lastmodifieddate")
                    else None
                )
            )
            if normalized not in valid_subaward_date_types:
                raise ValidationError(
                    f"Invalid date_type '{date_type}' for subaward searches. "
                    "Only 'action_date' or 'last_modified_date' are supported."
                )

        # Call parent implementation with validated parameters
        return super().time_period(
            start_date=start_date,
            end_date=end_date,
            new_awards_only=False,
            date_type=date_type,
        )

    def object_classes(self, *object_classes: str) -> SubAwardsSearch:
        """
        Object class filtering is not supported for subaward searches.

        The USASpending API accepts the ``object_classes`` filter for award searches
        only, and returns HTTP 422 when it is combined with ``spending_level=subawards``.

        Raises:
            ValidationError: Always, because subaward searches do not support this filter.
        """
        raise ValidationError(
            "object_classes is not supported for subaward searches. "
            "This filter is only available for award searches."
        )
