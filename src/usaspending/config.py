from __future__ import annotations
from dataclasses import dataclass
from typing import Optional



@dataclass
class Config:
    """Configuration for USASpending client.
    
    Attributes:
        base_url: Base URL for USASpending API
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        retry_backoff: Backoff multiplier for retries
        rate_limit_calls: Number of calls allowed per period
        rate_limit_period: Period in seconds for rate limiting
        cache_backend: Cache backend type ("file" or "memory")
        cache_dir: Directory for file-based cache
        cache_ttl: Cache time-to-live in seconds
        user_agent: User agent string for requests
        logging_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        debug_mode: Enable verbose debug logging
        log_file: Optional file path for log output
    """
    
    base_url: str = "https://api.usaspending.gov/api/v2"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    rate_limit_calls: int = 30
    rate_limit_period: int = 1
    cache_backend: str = "file"
    cache_dir: str = ".usaspending_cache"
    cache_ttl: int = 3600  # 1 hour
    user_agent: str = "usaspendingapi-python/0.1.0"
    logging_level: str = "INFO"
    debug_mode: bool = False
    log_file: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.rate_limit_calls <= 0:
            raise ValueError("rate_limit_calls must be positive")
        if self.cache_backend not in ("file", "memory"):
            raise ValueError("cache_backend must be 'file' or 'memory'")
        if self.logging_level.upper() not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError("logging_level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")

# In src/usaspendingapi/config.py

AWARD_TYPE_GROUPS = {
    "contracts": {
        "A": "BPA Call",
        "B": "Purchase Order",
        "C": "Delivery Order",
        "D": "Definitive Contract"
    },
    "loans": {
        "07": "Direct Loan",
        "08": "Guaranteed/Insured Loan"
    },
    "idvs": {
        "IDV_A": "GWAC Government Wide Acquisition Contract",
        "IDV_B": "IDC Multi-Agency Contract, Other Indefinite Delivery Contract",
        "IDV_B_A": "IDC Indefinite Delivery Contract / Requirements",
        "IDV_B_B": "IDC Indefinite Delivery Contract / Indefinite Quantity",
        "IDV_B_C": "IDC Indefinite Delivery Contract / Definite Quantity",
        "IDV_C": "FSS Federal Supply Schedule",
        "IDV_D": "BOA Basic Ordering Agreement",
        "IDV_E": "BPA Blanket Purchase Agreement"
    },
    "grants": {
        "02": "Block Grant",
        "03": "Formula Grant",
        "04": "Project Grant",
        "05": "Cooperative Agreement"
    },
    "direct_payments": {
        "06": "Direct Payment for Specified Use",
        "10": "Direct Payment with Unrestricted Use"
    },
    "other_assistance": {
        "09": "Insurance",
        "11": "Other Financial Assistance",
        "-1": "Not Specified"
    }
}

# Create a flattened map for easy description lookups
AWARD_TYPE_DESCRIPTIONS = {
    code: description
    for group in AWARD_TYPE_GROUPS.values()
    for code, description in group.items()
}

# Regenerate frozensets from this single source of truth
CONTRACT_CODES = frozenset(AWARD_TYPE_GROUPS["contracts"].keys())
IDV_CODES = frozenset(AWARD_TYPE_GROUPS["idvs"].keys())
LOAN_CODES = frozenset(AWARD_TYPE_GROUPS["loans"].keys())
GRANT_CODES = frozenset(AWARD_TYPE_GROUPS["grants"].keys())
DIRECT_PAYMENT_CODES = frozenset(AWARD_TYPE_GROUPS["direct_payments"].keys())
OTHER_CODES = frozenset(AWARD_TYPE_GROUPS["other_assistance"].keys())