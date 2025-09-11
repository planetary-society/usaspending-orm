from __future__ import annotations
from datetime import timedelta
from typing import Optional
from usaspending.logging_config import USASpendingLogger
from usaspending.exceptions import ConfigurationError
import os
import cachier

logger = USASpendingLogger.get_logger(__name__)


class _Config:
    """
    A container for all library configuration settings.
    Do not instantiate this class directly. Instead, import and use the global `config` object.
    """

    def __init__(self):
        # Default settings are defined here as instance attributes
        self.base_url: str = "https://api.usaspending.gov/api/v2/"
        self.user_agent: str = "usaspending-orm-python/0.4.1"
        self.timeout: int = 30
        self.max_retries: int = 3
        self.retry_delay: float = 1.0
        self.retry_backoff: float = 2.0

        # Global rate limit is 1000 calls per 300 seconds
        self.rate_limit_calls: int = 1000
        self.rate_limit_period: int = 300

        # Session management for handling server-side session limits
        self.session_request_limit: int = 900 # Max requests per session before renewal
        self.session_reset_on_5xx_threshold: int = 1  # Reset session after N consecutive 5XX errors

        # Caching via cachier
        self.cache_enabled: bool = True
        self.cache_backend: str = "file"  # Default file-based backend for cachier
        self.cache_dir: str = os.path.join(
            os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
            "usaspending",
        )
        self.cache_ttl: timedelta = timedelta(weeks=1)

        # Apply the initial default settings when the object is created
        self._apply_cachier_settings()

    def configure(self, **kwargs):
        """
        Updates configuration settings and applies them across the library.

        This is the primary method for users to modify the library's behavior.
        Any keyword argument passed will overwrite the existing configuration value.

        Args:
            **kwargs: Configuration keys and their new values.

        Raises:
            ConfigurationError: If any provided configuration value is invalid.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == "cache_ttl" and isinstance(value, (int, float)):
                    self.cache_ttl = timedelta(seconds=value)
                else:
                    setattr(self, key, value)
            else:
                logger.warning(
                    f"Warning: Unknown configuration key '{key}' was ignored."
                )

        self.validate()
        self._apply_cachier_settings()

    def _apply_cachier_settings(self):
        """Applies the current caching settings to the cachier library."""
        if self.cache_enabled:
            if self.cache_backend == "file":
                cache_backend = "pickle"  # cachier uses 'pickle' for file caching
            else:
                cache_backend = self.cache_backend
            cachier.set_global_params(
                stale_after=self.cache_ttl,
                cache_dir=self.cache_dir,
                backend=cache_backend,
            )
            cachier.enable_caching()
        else:
            cachier.disable_caching()


    def validate(self) -> None:
        """Validate the current configuration values."""
        if self.timeout <= 0:
            raise ConfigurationError("timeout must be positive")
        if self.max_retries < 0:
            raise ConfigurationError("max_retries must be non-negative")
        if self.rate_limit_calls <= 0:
            raise ConfigurationError("rate_limit_calls must be positive")
        if self.session_request_limit <= 0:
            raise ConfigurationError("session_request_limit must be positive")
        if self.session_reset_on_5xx_threshold < 0:
            raise ConfigurationError("session_reset_on_5xx_threshold must be non-negative")


        valid_backends = {"file", "memory"}
        if self.cache_enabled and (self.cache_backend not in valid_backends):
            raise ConfigurationError(f"cache_backend must be one of: {valid_backends}")


# Global configuration object
# This is the single instance that should be used throughout the library
config = _Config()
