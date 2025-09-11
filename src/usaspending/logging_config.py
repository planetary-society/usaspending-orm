"""Logging configuration for USASpending API client.

For applications using this library:

#### Configure Only USASpending Logs

To control only the USASpending library logs without affecting other libraries:

```python
import logging
from usaspending import USASpendingClient

# Configure only the usaspending logger
usaspending_logger = logging.getLogger('usaspending')
usaspending_logger.setLevel(logging.DEBUG)

# Add a handler for usaspending logs
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
usaspending_logger.addHandler(handler)

client = USASpendingClient()
```

#### Silence USASpending Logs

To suppress USASpending log messages even if your application has logging configured:

```python
import logging
from usaspending import USASpendingClient

# Silence usaspending logs
logging.getLogger('usaspending').setLevel(logging.WARNING)

client = USASpendingClient()
```

#### Log to File

To write USASpending logs to a file:

```python
import logging
from usaspending import USASpendingClient

# Configure file logging for usaspending
usaspending_logger = logging.getLogger('usaspending')
usaspending_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('usaspending.log')
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
usaspending_logger.addHandler(file_handler)

client = USASpendingClient()
```

"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional


class USASpendingLogger:
    """Library logging manager.

    Example usage within the library:
        from usaspending.logging_config import USASpendingLogger
        
        logger = USASpendingLogger.get_logger(__name__)
        logger.info("Library message")
    
    Example usage by applications:
        import logging
        from usaspending import USASpendingClient
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        client = USASpendingClient()
    """

    _loggers: Dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance with proper library configuration.
        
        This method ensures that library loggers:
        - Have a NullHandler to prevent "No handlers found" warnings
        - Have propagation enabled so applications can control them
        - Are cached to avoid repeated configuration
        
        Args:
            name: Logger name (typically __name__ from the calling module)
            
        Returns:
            Configured logger instance suitable for library use
            
        Example:
            logger = USASpendingLogger.get_logger(__name__)
            logger.info("Library message")
        """
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            
            # Only add NullHandler if this is a library logger and has no handlers
            if name.startswith("usaspending") and not logger.handlers:
                # NullHandler prevents "No handler found" warnings while allowing
                # the application to control actual logging behavior
                logger.addHandler(logging.NullHandler())
                
                # Ensure propagation is enabled so parent loggers (configured by
                # the application) can handle our log records
                logger.propagate = True
            
            cls._loggers[name] = logger
        
        return cls._loggers[name]

    @classmethod
    def is_debug_enabled(cls) -> bool:
        """Check if debug logging is enabled for the library.
        
        This checks the effective level of the 'usaspending' logger to determine
        if debug messages would be processed. Useful for expensive debug operations.
        
        Returns:
            True if debug logging is enabled, False otherwise
            
        Example:
            if USASpendingLogger.is_debug_enabled():
                logger.debug(f"Expensive debug info: {expensive_operation()}")
        """
        usaspending_logger = logging.getLogger("usaspending")
        return usaspending_logger.isEnabledFor(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a library logger.
    
    This is a shortcut for USASpendingLogger.get_logger() that's commonly used
    throughout the library codebase.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        from usaspending.logging_config import get_logger
        
        logger = get_logger(__name__)
        logger.info("Library message")
    """
    return USASpendingLogger.get_logger(name)


def log_api_request(
    logger: logging.Logger,
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an API request with appropriate detail level.
    
    This helper function provides consistent formatting for API request logging
    throughout the library. The level of detail depends on the logger's effective level.
    
    Args:
        logger: Logger instance to use for output
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        params: Optional query parameters dict
        json_data: Optional JSON payload dict
        
    Example:
        log_api_request(logger, "POST", "https://api.example.com/search", 
                       json_data={"filters": {...}})
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
    """Log an API response with appropriate detail level.
    
    This helper function provides consistent formatting for API response logging
    throughout the library. The message format and level depend on the response status.
    
    Args:
        logger: Logger instance to use for output
        status_code: HTTP status code
        response_size: Optional response size in bytes
        duration: Optional request duration in seconds
        error: Optional error message for failed requests
        
    Example:
        log_api_response(logger, 200, response_size=1024, duration=0.543)
        log_api_response(logger, 500, error="Internal server error")
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
    """Log query execution details.
    
    This helper function provides consistent formatting for query execution logging
    throughout the library. Debug level includes additional endpoint and pagination info.
    
    Args:
        logger: Logger instance to use for output
        query_type: Type of query being executed (e.g., "AwardsSearch")
        filters_count: Number of filters applied to the query
        endpoint: API endpoint being called
        page: Page number for paginated requests (default: 1)
        
    Example:
        log_query_execution(logger, "AwardsSearch", 3, "/api/v2/search/spending_by_award/", 2)
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Executing {query_type} query - {filters_count} filters, "
            f"endpoint: {endpoint}, page: {page}"
        )
    else:
        logger.info(f"Executing {query_type} query - {filters_count} filters")