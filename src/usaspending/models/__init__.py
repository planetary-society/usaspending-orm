"""Model classes for USASpending data structures."""

from __future__ import annotations

# Base classes
from .base_model import BaseModel, ClientAwareModel
from .lazy_record import LazyRecord

# Core models
from .award import Award
from .recipient import Recipient
from .location import Location
from .transaction import Transaction
from .period_of_performance import PeriodOfPerformance

# Common utilities and decorators
from .common import validate_kwargs

# Import relevant exceptions for convenience
from ..exceptions import (
    USASpendingError,
    APIError,
    HTTPError,
    RateLimitError,
    ValidationError,
    ConfigurationError,
)

__all__ = [
    # Base classes
    "BaseModel",
    "ClientAwareModel", 
    "LazyRecord",
    
    # Core models
    "Award",
    "Recipient",
    "Location",
    "Transaction",
    "PeriodOfPerformance",
        
    # Utilities
    "validate_kwargs",
    
    # Exceptions
    "USASpendingError",
    "APIError",
    "HTTPError",
    "RateLimitError",
    "ValidationError",
    "ConfigurationError",
]