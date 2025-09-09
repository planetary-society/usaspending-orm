"""USASpending Python Wrapper - Simplified access to federal award data.

An opinionated Python client for the USAspending.gov API that simplifies
access to federal spending data through intuitive interfaces and smart defaults.
"""

from __future__ import annotations

# Version information
try:
    from importlib.metadata import version

    __version__ = version("usaspending")
except ImportError:
    # Fallback for development/editable installs
    __version__ = "0.4.1"

__author__ = "Casey Dreier"
__email__ = "casey.dreier@planetary.org"

# Core client and configuration
from .client import USASpendingClient
from .config import config

# Exception classes for error handling
from .exceptions import (
    USASpendingError,
    APIError,
    HTTPError,
    RateLimitError,
    ValidationError,
    ConfigurationError,
    DownloadError,
)

# Model classes
from .models import (
    Award,
    Contract,
    Grant,
    IDV,
    Loan,
    Transaction,
    Recipient,
    Agency,
    Location,
    PeriodOfPerformance,
    SubAward,
)

# Query builder classes
from .queries import (
    AwardsSearch,
    TransactionsSearch,
    SpendingSearch,
    FundingSearch,
    SubAwardsSearch,
)

# Filter classes for building queries
from .queries.filters import (
    AgencyFilter,
    AwardAmountFilter,
    KeywordsFilter,
    LocationSpec,
    LocationFilter,
    LocationScopeFilter,
    TimePeriodFilter,
    TreasuryAccountComponentsFilter,
)

# Public API exports
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Core
    "USASpendingClient",
    "config",
    # Exceptions
    "USASpendingError",
    "APIError",
    "HTTPError",
    "RateLimitError",
    "ValidationError",
    "ConfigurationError",
    "DownloadError",
    # Models
    "Award",
    "Contract",
    "Grant",
    "IDV",
    "Loan",
    "Transaction",
    "Recipient",
    "Agency",
    "Location",
    "PeriodOfPerformance",
    "SubAward",
    # Query builders
    "AwardsSearch",
    "TransactionsSearch",
    "SpendingSearch",
    "FundingSearch",
    "SubAwardsSearch",
    # Filters
    "AgencyFilter",
    "AwardAmountFilter",
    "KeywordsFilter",
    "LocationSpec",
    "LocationFilter",
    "LocationScopeFilter",
    "TimePeriodFilter",
    "TreasuryAccountComponentsFilter",
]
