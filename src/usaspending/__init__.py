"""USASpending Python Wrapper - Simplified access to federal award data.

An opinionated Python client for the USAspending.gov API that simplifies
access to federal spending data through intuitive interfaces and smart defaults.
"""

from __future__ import annotations

# Version information
try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("usaspending-orm")
except (ImportError, PackageNotFoundError):
    # Fallback for development/editable installs
    __version__ = "0.0.0"

__author__ = "Casey Dreier"
__email__ = "casey.dreier@planetary.org"

# Core client and configuration
from .client import USASpendingClient
from .config import config

# Exception classes for error handling
from .exceptions import (
    APIError,
    ConfigurationError,
    DownloadError,
    HTTPError,
    RateLimitError,
    USASpendingError,
    ValidationError,
)

# Model classes
from .models import (
    IDV,
    Agency,
    Award,
    Contract,
    DistrictSpending,
    Funding,
    Grant,
    Loan,
    Location,
    PeriodOfPerformance,
    Recipient,
    RecipientSpending,
    Spending,
    StateSpending,
    SubAward,
    SubTierAgency,
    Transaction,
)

# Query builder classes
from .queries import (
    AgenciesSearch,
    AwardingAgenciesSearch,
    AwardsSearch,
    FundingAgenciesSearch,
    FundingSearch,
    RecipientsSearch,
    SpendingSearch,
    SubAwardsSearch,
    TransactionsSearch,
)

# Filter classes for building queries
from .queries.filters import (
    AgencyFilter,
    AgencyTier,
    AgencyType,
    AwardAmountFilter,
    AwardDateType,
    KeywordsFilter,
    LocationFilter,
    LocationScope,
    LocationScopeFilter,
    LocationSpec,
    TimePeriodFilter,
    TreasuryAccountComponentsFilter,
)

# Public API exports
__all__ = [
    "IDV",
    "APIError",
    "AgenciesSearch",
    "Agency",
    "AgencyFilter",
    "AgencyTier",
    # Filters
    "AgencyType",
    # Models
    "Award",
    "AwardAmountFilter",
    "AwardDateType",
    "AwardingAgenciesSearch",
    # Query builders
    "AwardsSearch",
    "ConfigurationError",
    "Contract",
    "DistrictSpending",
    "DownloadError",
    "Funding",
    "FundingAgenciesSearch",
    "FundingSearch",
    "Grant",
    "HTTPError",
    "KeywordsFilter",
    "Loan",
    "Location",
    "LocationFilter",
    "LocationScope",
    "LocationScopeFilter",
    "LocationSpec",
    "PeriodOfPerformance",
    "RateLimitError",
    "Recipient",
    "RecipientSpending",
    "RecipientsSearch",
    "Spending",
    "SpendingSearch",
    "StateSpending",
    "SubAward",
    "SubAwardsSearch",
    "SubTierAgency",
    "TimePeriodFilter",
    "Transaction",
    "TransactionsSearch",
    "TreasuryAccountComponentsFilter",
    # Core
    "USASpendingClient",
    # Exceptions
    "USASpendingError",
    "ValidationError",
    "__author__",
    "__email__",
    # Version info
    "__version__",
    "config",
]
