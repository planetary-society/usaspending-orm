from __future__ import annotations

import os
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable

import cachier

from usaspending.exceptions import ConfigurationError
from usaspending.logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)
_CACHE_SETTINGS_OBSERVERS: list[Callable[[], None]] = []


def _resolve_version() -> str:
    """Resolve the installed package version for user agent reporting."""
    try:
        return version("usaspending-orm")
    except PackageNotFoundError:
        return "0.0.0"


def register_cache_settings_observer(observer: Callable[[], None]) -> None:
    """Register a callback to run after cache settings change."""
    if observer not in _CACHE_SETTINGS_OBSERVERS:
        _CACHE_SETTINGS_OBSERVERS.append(observer)


def _notify_cache_settings_observers() -> None:
    """Notify registered cache observers about configuration changes."""
    for observer in list(_CACHE_SETTINGS_OBSERVERS):
        observer()


class _Config:
    """
    A container for all library configuration settings.
    Do not instantiate this class directly. Instead, import and use the global `config` object.
    """

    def __init__(self):
        # Default settings are defined here as instance attributes
        self.base_url: str = "https://api.usaspending.gov/api/v2/"
        self.user_agent: str = f"usaspending-orm-python/{_resolve_version()}"
        self.timeout: int = 30
        self.max_retries: int = 3
        self.retry_delay: float = 10.0
        self.retry_backoff: float = 2.0

        # Global rate limit is roughly 1000 calls per 300 seconds
        self.rate_limit_calls: int = 1000
        self.rate_limit_period: int = 300

        # Session management for handling server-side session limits
        self.session_request_limit: int = 250  # Max requests per session before renewal
        self.session_reset_on_5xx_threshold: int = 1  # Reset session after N consecutive 5XX errors

        # Query result limits to prevent unbounded fetches
        # Set to None to disable the default limit (not recommended for production)
        self.default_result_limit: int | None = 10000

        # Warn when a query would return more than this many results
        self.warn_on_large_result_set: bool = False
        self.large_result_threshold: int = 5000

        # Caching via cachier
        self.cache_enabled: bool = False
        self.cache_backend: str = "file"  # Default file-based backend for cachier
        self.cache_namespace: str = "usaspending-orm"
        self.cache_dir: str = os.path.join(
            os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
            "usaspending",
        )
        self.cache_ttl: timedelta = timedelta(weeks=1)
        self.cache_timeout: int = 60  # Seconds to wait for processing cache entries

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
                logger.warning(f"Warning: Unknown configuration key '{key}' was ignored.")

        self.validate()
        self._apply_cachier_settings()

    def _cachier_params(self) -> dict[str, Any]:
        """Build the base cachier parameter dict from current settings.

        Returns:
            Dict of keyword arguments suitable for ``cachier.set_global_params``
            or ``cachier.cachier``.
        """
        backend = "memory" if self.cache_backend == "memory" else "pickle"
        params: dict[str, Any] = {
            "stale_after": self.cache_ttl,
            "wait_for_calc_timeout": self.cache_timeout,
            "backend": backend,
        }
        if backend == "pickle":
            params["cache_dir"] = self.cache_dir
        return params

    def _apply_cachier_settings(self):
        """Applies the current caching settings to the cachier library."""
        cachier.set_global_params(**self._cachier_params())

        if self.cache_enabled:
            cachier.enable_caching()
        else:
            cachier.disable_caching()

        _notify_cache_settings_observers()

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
        if self.cache_timeout <= 0:
            raise ConfigurationError("cache_timeout must be positive")
        if not isinstance(self.cache_namespace, str) or not self.cache_namespace.strip():
            raise ConfigurationError("cache_namespace must be a non-empty string")

        # Query limit validation
        if self.default_result_limit is not None and self.default_result_limit <= 0:
            raise ConfigurationError("default_result_limit must be positive or None")
        if self.large_result_threshold <= 0:
            raise ConfigurationError("large_result_threshold must be positive")


# Global configuration object
# This is the single instance that should be used throughout the library
config = _Config()
