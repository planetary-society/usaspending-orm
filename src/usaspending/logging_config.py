"""Logging configuration for USASpending API client."""

from __future__ import annotations

import logging
import sys
from typing import Dict, Any, Optional


class USASpendingLogger:
    """Centralized logging configuration for USASpending API client."""

    _loggers: Dict[str, logging.Logger] = {}
    _configured = False

    @classmethod
    def configure(
        self,
        level: str = "INFO",
        log_format: Optional[str] = None,
        log_file: Optional[str] = None,
    ) -> None:
        """
        Configure logging for the USASpending API client.

        Args:
            level: Base logging level (DEBUG, INFO, WARNING, ERROR)
            log_format: Custom log format string
            log_file: Optional file to write logs to (in addition to console)
        """
        if self._configured:
            return

        # Set root logger level
        root_logger = logging.getLogger("usaspending")
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Create formatter
        if not log_format:
            if level.upper() == "DEBUG":
                log_format = (
                    "%(asctime)s - %(name)s - %(levelname)s - "
                    "%(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
                )
            else:
                log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        formatter = logging.Formatter(log_format)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Configure specific loggers for different components
        is_debug = level.upper() == "DEBUG"
        component_levels = {
            "usaspending.client": logging.DEBUG if is_debug else logging.INFO,
            "usaspending.queries": logging.DEBUG if is_debug else logging.INFO,
            "usaspending.models": logging.DEBUG if is_debug else logging.WARNING,
            "usaspending.utils.rate_limit": logging.DEBUG
            if is_debug
            else logging.WARNING,
            "usaspending.utils.retry": logging.DEBUG if is_debug else logging.WARNING,
            "usaspending.cache": logging.DEBUG if is_debug else logging.WARNING,
        }

        for logger_name, logger_level in component_levels.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(logger_level)
            # Prevent duplicate messages
            logger.propagate = True

        # Mark as configured
        self._configured = True

        # Log configuration
        config_logger = self.get_logger("usaspending.config")
        config_logger.info(f"Logging configured - Level: {level}")
        if log_file:
            config_logger.info(f"Logging to file: {log_file}")

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance for the given name.

        Args:
            name: Logger name (typically module name)

        Returns:
            Configured logger instance
        """
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]

    @classmethod
    def is_debug_enabled(cls) -> bool:
        """Check if debug logging is enabled."""
        root_logger = logging.getLogger("usaspending")
        return root_logger.isEnabledFor(logging.DEBUG)

    @classmethod
    def reset(cls) -> None:
        """Reset logging configuration (mainly for testing)."""
        cls._configured = False
        cls._loggers.clear()

        # Clear all handlers from our loggers
        for logger_name in [
            "usaspending",
            "usaspending.client",
            "usaspending.queries",
            "usaspending.models",
            "usaspending.utils",
            "usaspending.cache",
        ]:
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return USASpendingLogger.get_logger(name)


def log_api_request(
    logger: logging.Logger,
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an API request with appropriate detail level.

    Args:
        logger: Logger instance
        method: HTTP method
        url: Request URL
        params: Query parameters
        json_data: JSON payload
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"API Request: {method} {url}")
        if params:
            logger.debug(f"Query params: {params}")
        if json_data:
            logger.debug(f"JSON payload: {json_data}")
    else:
        logger.info(f"API Request: {method} {url}")


def log_api_response(
    logger: logging.Logger,
    status_code: int,
    response_size: Optional[int] = None,
    duration: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log an API response with appropriate detail level.

    Args:
        logger: Logger instance
        status_code: HTTP status code
        response_size: Response size in bytes
        duration: Request duration in seconds
        error: Error message if applicable
    """
    if error:
        logger.error(f"API Response: {status_code} - Error: {error}")
    elif status_code >= 400:
        logger.warning(f"API Response: {status_code}")
    else:
        msg_parts = [f"API Response: {status_code}"]
        if duration is not None:
            msg_parts.append(f"({duration:.3f}s)")
        if response_size is not None and logger.isEnabledFor(logging.DEBUG):
            msg_parts.append(f"- {response_size} bytes")

        if status_code >= 300:
            logger.warning(" ".join(msg_parts))
        else:
            logger.info(" ".join(msg_parts))


def log_query_execution(
    logger: logging.Logger,
    query_type: str,
    filters_count: int,
    endpoint: str,
    page: int = 1,
) -> None:
    """
    Log query execution details.

    Args:
        logger: Logger instance
        query_type: Type of query (e.g., "AwardsSearch")
        filters_count: Number of filters applied
        endpoint: API endpoint
        page: Page number
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Executing {query_type} query - {filters_count} filters, "
            f"endpoint: {endpoint}, page: {page}"
        )
    else:
        logger.info(f"Executing {query_type} query - {filters_count} filters")
