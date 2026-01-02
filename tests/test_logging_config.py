# tests/test_logging_config.py
"""Tests for logging configuration module."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

from usaspending.logging_config import (
    USASpendingLogger,
    get_logger,
    log_api_request,
    log_api_response,
    log_query_execution,
)


class TestUSASpendingLogger:
    """Tests for USASpendingLogger class."""

    def setup_method(self):
        """Clear logger cache before each test."""
        USASpendingLogger._loggers.clear()

    def test_get_logger_returns_logger(self):
        """get_logger should return a logging.Logger instance."""
        logger = USASpendingLogger.get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_caches_loggers(self):
        """get_logger should cache and return same logger for same name."""
        logger1 = USASpendingLogger.get_logger("usaspending.test")
        logger2 = USASpendingLogger.get_logger("usaspending.test")
        assert logger1 is logger2

    def test_get_logger_different_names_different_loggers(self):
        """get_logger should return different loggers for different names."""
        logger1 = USASpendingLogger.get_logger("usaspending.module1")
        logger2 = USASpendingLogger.get_logger("usaspending.module2")
        assert logger1 is not logger2

    def test_usaspending_logger_has_null_handler(self):
        """usaspending loggers should have NullHandler attached."""
        logger = USASpendingLogger.get_logger("usaspending.test.null_handler")
        assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)

    def test_usaspending_logger_propagation_enabled(self):
        """usaspending loggers should have propagation enabled."""
        logger = USASpendingLogger.get_logger("usaspending.test.propagation")
        assert logger.propagate is True

    def test_non_usaspending_logger_no_null_handler(self):
        """Non-usaspending loggers should not get NullHandler added."""
        # Clear handlers first
        external_logger = logging.getLogger("external.module")
        original_handlers = list(external_logger.handlers)

        logger = USASpendingLogger.get_logger("external.module")

        # Should have same handlers as before (no NullHandler added)
        new_null_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.NullHandler) and h not in original_handlers
        ]
        assert len(new_null_handlers) == 0

    def test_is_debug_enabled_false_by_default(self):
        """is_debug_enabled should return False by default."""
        # Reset usaspending logger level
        usaspending_logger = logging.getLogger("usaspending")
        original_level = usaspending_logger.level
        usaspending_logger.setLevel(logging.WARNING)

        try:
            assert USASpendingLogger.is_debug_enabled() is False
        finally:
            usaspending_logger.setLevel(original_level)

    def test_is_debug_enabled_true_when_debug(self):
        """is_debug_enabled should return True when DEBUG level set."""
        usaspending_logger = logging.getLogger("usaspending")
        original_level = usaspending_logger.level

        try:
            usaspending_logger.setLevel(logging.DEBUG)
            assert USASpendingLogger.is_debug_enabled() is True
        finally:
            usaspending_logger.setLevel(original_level)


class TestGetLoggerFunction:
    """Tests for the convenience get_logger function."""

    def setup_method(self):
        """Clear logger cache before each test."""
        USASpendingLogger._loggers.clear()

    def test_get_logger_function_returns_logger(self):
        """get_logger function should return a logger instance."""
        logger = get_logger("test.convenience")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_function_delegates_to_class(self):
        """get_logger function should use USASpendingLogger.get_logger()."""
        logger1 = get_logger("usaspending.test.delegate")
        logger2 = USASpendingLogger.get_logger("usaspending.test.delegate")
        assert logger1 is logger2


class TestLogApiRequest:
    """Tests for log_api_request function."""

    def test_logs_method_and_url_at_info(self):
        """Should log method and URL at INFO level."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False

        log_api_request(mock_logger, "GET", "https://api.example.com/test")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "GET" in call_args
        assert "https://api.example.com/test" in call_args

    def test_logs_details_at_debug(self):
        """Should log params and JSON payload at DEBUG level."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = True

        log_api_request(
            mock_logger,
            "POST",
            "https://api.example.com/search",
            params={"limit": 100},
            json_data={"filters": {"award_type": "contract"}},
        )

        # Should call debug multiple times (request, params, json)
        assert mock_logger.debug.call_count == 3

    def test_no_params_or_json_at_debug(self):
        """Should not log params/json if not provided, even at DEBUG."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = True

        log_api_request(mock_logger, "GET", "https://api.example.com/simple")

        # Only one debug call (the request itself)
        assert mock_logger.debug.call_count == 1


class TestLogApiResponse:
    """Tests for log_api_response function."""

    def test_success_response_logs_debug(self):
        """Successful responses (2xx) should log at DEBUG level."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = True

        log_api_response(mock_logger, 200, duration=0.5)

        mock_logger.debug.assert_called_once()
        assert "200" in mock_logger.debug.call_args[0][0]

    def test_error_response_logs_error(self):
        """Responses with error message should log at ERROR level."""
        mock_logger = MagicMock()

        log_api_response(mock_logger, 500, error="Internal server error")

        mock_logger.error.assert_called_once()
        assert "500" in mock_logger.error.call_args[0][0]
        assert "Internal server error" in mock_logger.error.call_args[0][0]

    def test_client_error_logs_warning(self):
        """4xx responses should log at WARNING level."""
        mock_logger = MagicMock()

        log_api_response(mock_logger, 404)

        mock_logger.warning.assert_called_once()
        assert "404" in mock_logger.warning.call_args[0][0]

    def test_redirect_logs_warning(self):
        """3xx responses should log at WARNING level."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False

        log_api_response(mock_logger, 301)

        mock_logger.warning.assert_called_once()

    def test_includes_duration_when_provided(self):
        """Should include duration in message when provided."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = True

        log_api_response(mock_logger, 200, duration=1.234)

        call_args = mock_logger.debug.call_args[0][0]
        assert "1.234" in call_args

    def test_includes_size_at_debug(self):
        """Should include response size at DEBUG level."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = True

        log_api_response(mock_logger, 200, response_size=4096)

        call_args = mock_logger.debug.call_args[0][0]
        assert "4096" in call_args


class TestLogQueryExecution:
    """Tests for log_query_execution function."""

    def test_logs_query_type_at_info(self):
        """Should log query type at INFO level."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False

        log_query_execution(
            mock_logger,
            "AwardsSearch",
            [],
            "/api/v2/search/spending_by_award/",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "AwardsSearch" in call_args

    def test_logs_no_filters_message(self):
        """Should indicate when no filters are applied."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False

        log_query_execution(
            mock_logger,
            "AwardsSearch",
            [],
            "/api/v2/search/",
        )

        call_args = mock_logger.info.call_args[0][0]
        assert "no filters" in call_args.lower()

    def test_logs_filter_details_at_debug(self):
        """Should log filter details at DEBUG level."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = True

        # Create mock filter
        mock_filter = MagicMock()
        mock_filter.to_dict.return_value = {"keywords": ["test"]}
        type(mock_filter).__name__ = "KeywordsFilter"

        log_query_execution(
            mock_logger,
            "AwardsSearch",
            [mock_filter],
            "/api/v2/search/",
            page=2,
        )

        # Should have multiple debug calls
        assert mock_logger.debug.call_count >= 2

    def test_logs_filter_keys_at_info(self):
        """Should log filter keys at INFO level."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False

        # Create mock filters
        mock_filter1 = MagicMock()
        mock_filter1.to_dict.return_value = {"keywords": ["test"]}

        mock_filter2 = MagicMock()
        mock_filter2.to_dict.return_value = {"time_period": {"start_date": "2024-01-01"}}

        log_query_execution(
            mock_logger,
            "AwardsSearch",
            [mock_filter1, mock_filter2],
            "/api/v2/search/",
        )

        call_args = mock_logger.info.call_args[0][0]
        assert "keywords" in call_args
        assert "time_period" in call_args
