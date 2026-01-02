"""Query builders for USASpending API operations.

This module provides query builders for constructing complex API requests
with filtering, pagination, and result transformation capabilities.

Base Classes:
    BaseQuery: Shared base class for query builders
    QueryBuilder: Abstract base class for chainable query operations
    ClientSideQueryBuilder: In-memory query builder for non-API relationships

Award Queries:
    AwardQuery: Single award retrieval operations
    AwardsSearch: Complex award search with filtering and chaining

Agency Queries:
    AgencyQuery: Single agency retrieval operations
    AgencyAwardSummary: Agency award summary data retrieval

Recipient Queries:
    SpendingByRecipientsSearch: Recipient search with filtering and chaining

Example:
    >>> from ..client import USASpendingClient
    >>> client = USASpendingClient()
    >>> # Single award retrieval
    >>> award = client.awards.find_by_generated_id("CONT_AWD_123")
    >>> # Complex award search
    >>> awards = (
    ...     client.awards.search()
    ...     .agency("National Aeronautics and Space Administration")
    ...     .place_of_performance_locations({"state_code": "TX", "country_code": "USA"})
    ...     .fiscal_year(2024)
    ...     .limit(50)
    ... )
    >>> for award in awards:
    ...     print(f"{award.award_identifier}: ${award.total_obligation:,.2f}")
"""

from __future__ import annotations

# Import custom exceptions to make them available package-wide
from ..exceptions import (
    APIError,
    ConfigurationError,
    HTTPError,
    RateLimitError,
    USASpendingError,
    ValidationError,
)
from .agencies_search import AgenciesSearch
from .agency_award_summary import AgencyAwardSummary
from .agency_query import AgencyQuery
from .award_accounts_query import AwardAccountsQuery
from .award_query import AwardQuery
from .awarding_agencies_search import AwardingAgenciesSearch
from .awards_search import AwardsSearch
from .base_query import BaseQuery
from .client_side_query_builder import ClientSideQueryBuilder
from .federal_accounts_query import FederalAccountsQuery
from .funding_agencies_search import FundingAgenciesSearch
from .funding_search import FundingSearch
from .idv_child_awards import IDVChildAwardsSearch
from .query_builder import QueryBuilder
from .recipient_query import RecipientQuery
from .recipients_search import RecipientsSearch
from .spending_search import SpendingSearch
from .sub_agency_query import SubAgencyQuery
from .subawards_search import SubAwardsSearch
from .tas_codes_query import TASCodesQuery
from .transactions_search import TransactionsSearch

__all__ = [
    "APIError",
    "AgenciesSearch",
    "AgencyAwardSummary",
    "AgencyQuery",
    "AwardAccountsQuery",
    "AwardQuery",
    "AwardingAgenciesSearch",
    "AwardsSearch",
    # Core query classes
    "BaseQuery",
    "ClientSideQueryBuilder",
    "ConfigurationError",
    "FederalAccountsQuery",
    "FundingAgenciesSearch",
    "FundingSearch",
    "HTTPError",
    "IDVChildAwardsSearch",
    "QueryBuilder",
    "RateLimitError",
    "RecipientQuery",
    "RecipientsSearch",
    "SpendingSearch",
    "SubAgencyQuery",
    "SubAwardsSearch",
    "TASCodesQuery",
    "TransactionsSearch",
    "USASpendingError",
    "ValidationError",
]
