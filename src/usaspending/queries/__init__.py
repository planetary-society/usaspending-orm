"""Query builders for USASpending API operations.

This module provides query builders for constructing complex API requests
with filtering, pagination, and result transformation capabilities.

Base Classes:
    QueryBuilder: Abstract base class for chainable query operations
    
Award Queries:
    AwardQuery: Single award retrieval operations
    AwardsSearch: Complex award search with filtering and chaining
    
Agency Queries:
    AgencyQuery: Single agency retrieval operations
    AgencyAwardSummary: Agency award summary data retrieval
    
Recipient Queries:
    SpendingByRecipientsSearch: Recipient search with filtering and chaining

Example:
    >>> from usaspending.client import USASpending
    >>> client = USASpending()
    >>> 
    >>> # Single award retrieval
    >>> award = client.awards.get("CONT_AWD_123")
    >>> 
    >>> # Complex award search
    >>> awards = client.awards.search()\\
    ...     .for_agency("NASA")\\
    ...     .in_state("TX")\\
    ...     .fiscal_years(2023, 2024)\\
    ...     .limit(50)
    >>> 
    >>> for award in awards:
    ...     print(f"{award.recipient_name}: ${award.amount:,.2f}")
"""

# Import custom exceptions to make them available package-wide
from ..exceptions import (
    USASpendingError,
    APIError,
    HTTPError,
    ValidationError,
    RateLimitError,
    ConfigurationError,
)

from .query_builder import QueryBuilder
from .award_query import AwardQuery
from .awards_search import AwardsSearch
from .agency_query import AgencyQuery
from .funding_agencies_search import FundingAgenciesSearch
from .awarding_agencies_search import AwardingAgenciesSearch
from .agency_award_summary import AgencyAwardSummary
from .sub_agency_query import SubAgencyQuery
from .spending_by_recipients_search import SpendingByRecipientsSearch
from .transactions_search import TransactionsSearch
from .funding_search import FundingSearch
from .spending_search import SpendingSearch
from .subawards_search import SubAwardsSearch

__all__ = [
    # Core query classes
    "QueryBuilder",
    "AwardQuery",
    "AwardsSearch",
    "AgencyQuery",
    "FundingAgenciesSearch",
    "AwardingAgenciesSearch",
    "AgencyAwardSummary",
    "SubAgencyQuery",
    "SpendingByRecipientsSearch",
    "TransactionsSearch",
    "FundingSearch",
    "SpendingSearch",
    "SubAwardsSearch",
    "USASpendingError",
    "APIError",
    "HTTPError",
    "ValidationError",
    "RateLimitError",
    "ConfigurationError",
]
