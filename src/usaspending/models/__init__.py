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

__all__ = [

    # Core models
    "Award",
    "Recipient",
    "Location",
    "Transaction",
    "PeriodOfPerformance",
]