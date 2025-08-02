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
from .funding import Funding
from .period_of_performance import PeriodOfPerformance
from .award_factory import create_award

# Spending models
from .spending import Spending
from .recipient_spending import RecipientSpending
from .district_spending import DistrictSpending

__all__ = [
    # Base classes
    "BaseModel",
    "ClientAwareModel",
    "LazyRecord",
    # Core models
    "Award",
    "Contract",
    "Grant",
    "IDV",
    "Loan",
    "Recipient",
    "Location",
    "Transaction",
    "Funding",
    "PeriodOfPerformance",
    # Spending models
    "Spending",
    "RecipientSpending",
    "DistrictSpending",
    # Factory
    "create_award",
]
