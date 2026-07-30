"""Global transaction search query builder for USASpending data.

This module wraps the ``/search/spending_by_transaction/`` endpoint, which
searches transactions across every award rather than within one. Its companion
``/search/spending_by_transaction_count/`` endpoint reports how many
transactions each award-type category holds under the same filters, and is what
:meth:`TransactionsSearch.count` reads.

Contrast with :class:`~usaspending.queries.award_transactions_search.AwardTransactionsSearch`,
which lists the transactions belonging to a single award and is reached as
``client.transactions.award_id(...)`` or ``award.transactions``. This builder is
reached as ``client.transactions.search()`` and takes the same rich filters the
award search does.

Example:
    ```python
    from usaspending import USASpendingClient

    client = USASpendingClient()

    transactions = (
        client.transactions.search()
        .contracts()
        .agency("National Aeronautics and Space Administration")
        .fiscal_year(2024)
        .order_by("transaction_amount", "desc")
        .limit(25)
    )

    for transaction in transactions:
        print(f"{transaction.action_date}: {transaction.amt}")
    ```

Note:
    Unlike the award search, this endpoint accepts award type codes from more
    than one category in a single query, so contracts and grants can be searched
    together.
"""

from __future__ import annotations

from typing import Any, ClassVar

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..models.award_types import categories_for_codes, validate_award_type_codes
from ..models.transaction import Transaction
from .mixins import SortableQuery
from .query_builder import SearchQueryBuilder

logger = USASpendingLogger.get_logger(__name__)


class TransactionsSearch(SortableQuery, SearchQueryBuilder["Transaction"]):
    """Builds and executes a global transaction search across all awards.

    Every filter method returns a new instance, so a query is built up
    immutably. The API requires an ``award_type_codes`` filter, a field list, a
    sort field and a sort direction, so this builder always sends all four:
    the fields are :attr:`~usaspending.models.transaction.Transaction.SEARCH_FIELDS`,
    the sort defaults to the endpoint's own default of "Transaction Amount"
    descending, and the award type codes must be supplied by the caller.

    Attributes:
        SORT_FIELD_MAP: Friendly sort names mapped to the API's display-name
            fields.

    Example:
        >>> transactions = (
        ...     client.transactions.search().contracts().keywords("space exploration").limit(10)
        ... )

    Note:
        The API serves at most its first 50,000 matching rows; iterating past
        that point raises :class:`~usaspending.exceptions.APIError` rather than
        silently truncating. Narrow the filters, set :meth:`limit`, or use the
        bulk download endpoints for larger result sets. ``count()`` is not
        subject to the window.

    Note:
        With a :meth:`program_activities` filter set, ``count()`` and ``len()``
        raise :class:`~usaspending.exceptions.ValidationError`: the count
        endpoint silently ignores that filter, so passing it through would
        report a wrong count. Iteration, ``all()``, ``first()`` and ``bool()``
        work regardless; ``list(query)``, indexing and slicing consult the
        count and so raise too.
    """

    #: The endpoint's own default sort. Sent on every request, because the API
    #: requires both ``sort`` and ``order``.
    _sort_field: str = "Transaction Amount"

    # Map user-friendly sort field names to the API's display-name fields. Every
    # value is a member of Transaction.SEARCH_FIELDS, which the API requires:
    # it rejects a sort field that was not requested.
    SORT_FIELD_MAP: ClassVar[dict[str, str]] = {
        "modification_number": "Mod",
        "award_id": "Award ID",
        # Alias matching the model property of the same name.
        "award_identifier": "Award ID",
        "recipient_name": "Recipient Name",
        "recipient_uei": "Recipient UEI",
        "action_date": "Action Date",
        "action_type": "Action Type",
        "award_type": "Award Type",
        "transaction_amount": "Transaction Amount",
        # Aliases matching the model properties that read these columns.
        "federal_action_obligation": "Transaction Amount",
        "type_description": "Award Type",
        "transaction_description": "Transaction Description",
        "awarding_agency": "Awarding Agency",
        "awarding_sub_agency": "Awarding Sub Agency",
        "funding_agency": "Funding Agency",
        "funding_sub_agency": "Funding Sub Agency",
        "loan_value": "Loan Value",
        "face_value_loan_guarantee": "Loan Value",
        "subsidy_cost": "Subsidy Cost",
        "original_loan_subsidy_cost": "Subsidy Cost",
        "issued_date": "Issued Date",
        "last_date_to_order": "Last Date to Order",
        "recipient_location": "Recipient Location",
        "place_of_performance": "Primary Place of Performance",
        "naics": "NAICS",
        "psc": "PSC",
        "assistance_listing": "Assistance Listing",
    }

    @property
    def _endpoint(self) -> str:
        """Return the API endpoint for global transaction searches.

        Returns:
            str: The endpoint path '/search/spending_by_transaction/'.
        """
        return "/search/spending_by_transaction/"

    def _build_payload(self, page: int) -> dict[str, Any]:
        """Construct the API request payload from the applied filters.

        Args:
            page: The page number to retrieve (1-indexed).

        Returns:
            dict[str, Any]: The complete payload for the API request.

        Raises:
            ValidationError: If no ``award_type_codes`` filter is set.
        """
        payload = {
            "filters": self._require_award_type_filters(),
            "fields": list(Transaction.SEARCH_FIELDS),
            "limit": self._get_effective_page_size(),
            "page": page,
        }
        payload.update(self._sort_payload())
        return payload

    def _transform_result(self, result: dict[str, Any]) -> Transaction:
        """Transform a single API result into a Transaction model instance.

        Args:
            result: A single result dictionary from the API response.

        Returns:
            Transaction: The model wrapping that row.
        """
        return Transaction(result)

    def award_type_codes(self, *award_codes: str) -> TransactionsSearch:
        """Filter by one or more award type codes.

        **This filter is required** - the API rejects a request without it.

        Unlike the award search, this endpoint supports MIXED award-type
        categories, so contracts and grants can be requested together in one
        query rather than needing a query each.

        Args:
            *award_codes: One or more award type codes, such as "A" or "02".

        Returns:
            TransactionsSearch: A new instance with the award type filter applied.

        Raises:
            ValidationError: If no code is supplied, or if any code is not a
                valid award type code.

        Example:
            >>> # Contracts and grants together, which award search cannot do
            >>> mixed = client.transactions.search().award_type_codes(
            ...     "A", "B", "C", "D", "02", "03", "04", "05"
            ... )
        """
        if not award_codes:
            raise ValidationError("At least one award type code is required")

        validate_award_type_codes(award_codes)

        return super().award_type_codes(*award_codes)

    def _compute_raw_count(self) -> int:
        """Return how many transactions match, from the dedicated count endpoint.

        The endpoint reports one bucket per award-type category, so the total
        is the sum of the buckets for the categories this query selected. The
        categories are derived from the aggregated filters, which merge the
        codes of every award-type filter the chain added, so a mixed-category
        query such as ``.contracts().grants()`` counts every selected category.

        Returns:
            int: Total matching transactions, before :meth:`count` applies the
            caller's own bounds.

        Raises:
            ValidationError: If no ``award_type_codes`` filter is set, or if a
                ``program_activities`` filter is present, which the count
                endpoint does not accept.
        """
        filters = self._require_award_type_filters()

        # The count endpoint's validator silently discards this one filter
        # rather than rejecting it, so passing it through would return a
        # confidently wrong count, and paging out a count instead would both
        # misreport any result set past the endpoint's window and cost a
        # request per page. Iteration does not need a count, so it still works.
        if "program_activities" in filters:
            raise ValidationError(
                "The spending_by_transaction_count endpoint silently ignores the "
                "program_activities filter, so this query cannot report an exact "
                "count. Iterate the query or call .all(), which do not count. "
                "Note that list(query), indexing and slicing also require a count."
            )

        categories = categories_for_codes(set(filters["award_type_codes"]))
        return self._count_via_bucketed_endpoint(
            "/search/spending_by_transaction_count/",
            filters,
            (category.api_count_key for category in categories),
        )
