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