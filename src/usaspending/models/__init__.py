"""Model classes for USASpending data structures."""

from __future__ import annotations

from .agency import Agency

# Core models
from .award import Award
from .award_account import AwardAccount
from .award_factory import create_award

# Award type constants
from .award_types import (
    ALL_AWARD_CODES,
    AWARD_TYPE_DESCRIPTIONS,
    AWARD_TYPE_GROUPS,
    CONTRACT_CODES,
    DIRECT_PAYMENT_CODES,
    GRANT_CODES,
    IDV_CODES,
    LOAN_CODES,
    OTHER_CODES,
    get_award_group,
    get_description,
    is_valid_award_type,
)

# Base classes
from .base_model import BaseModel, ClientAwareModel
from .contract import Contract
from .district_spending import DistrictSpending
from .federal_account import FederalAccount
from .funding import Funding
from .grant import Grant
from .idv import IDV
from .lazy_record import LazyRecord
from .loan import Loan
from .location import Location
from .period_of_performance import PeriodOfPerformance
from .recipient import Recipient
from .recipient_spending import RecipientSpending

# Spending models
from .spending import Spending
from .state_spending import StateSpending
from .subaward import SubAward
from .subtier_agency import SubTierAgency
from .transaction import Transaction
from .treasury_account_symbol import TreasuryAccountSymbol

__all__ = [
    "ALL_AWARD_CODES",
    "AWARD_TYPE_DESCRIPTIONS",
    # Award type constants
    "AWARD_TYPE_GROUPS",
    "CONTRACT_CODES",
    "DIRECT_PAYMENT_CODES",
    "GRANT_CODES",
    "IDV",
    "IDV_CODES",
    "LOAN_CODES",
    "OTHER_CODES",
    "Agency",
    # Core models
    "Award",
    "AwardAccount",
    # Base classes
    "BaseModel",
    "ClientAwareModel",
    "Contract",
    "DistrictSpending",
    "FederalAccount",
    "Funding",
    "Grant",
    "LazyRecord",
    "Loan",
    "Location",
    "PeriodOfPerformance",
    "Recipient",
    "RecipientSpending",
    # Spending models
    "Spending",
    "StateSpending",
    "SubAward",
    "SubTierAgency",
    "Transaction",
    "TreasuryAccountSymbol",
    # Factory
    "create_award",
    "get_award_group",
    "get_description",
    "is_valid_award_type",
]
