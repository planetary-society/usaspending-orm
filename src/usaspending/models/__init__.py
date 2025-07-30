"""Model classes for USASpending data structures."""

from __future__ import annotations

# Base classes
from .base_model import BaseModel, ClientAwareModel
from .lazy_record import LazyRecord

# Core models
from .award import Award
from .contract import Contract
from .grant import Grant
from .idv import IDV
from .loan import Loan
from .recipient import Recipient
from .location import Location
from .transaction import Transaction
from .period_of_performance import PeriodOfPerformance
from .award_factory import create_award

__all__ = [

    # Core models
    "Award",
    "Contract", 
    "Grant",
    "IDV",
    "Loan",
    "Recipient",
    "Location",
    "Transaction",
    "PeriodOfPerformance",
    
    # Factory
    "create_award",
]