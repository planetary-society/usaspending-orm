"""Rate limiting implementation for USASpending API client."""

from __future__ import annotations

import threading
import time
from collections import deque

from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)


class RateLimiter:
    """
    Rate limiter using a sliding window algorithm.

    This implementation tracks the timestamps of API calls and ensures
    that no more than `max_calls` are made within any `period` second window.

    Thread-safe implementation using locks.
    """

    def __init__(self, max_calls: int, period: float):
        """
        Initialize the rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        if max_calls <= 0:
            raise ValidationError("max_calls must be positive")
        if period <= 0:
            raise ValidationError("period must be positive")

        self.max_calls = max_calls
        self.period = period
        self._call_times: deque[float] = deque()
        self._lock = threading.Lock()

        logger.debug(f"Initialized RateLimiter: {max_calls} calls per {period}s")

    def wait_if_needed(self) -> None:
        """
        Wait if necessary to avoid exceeding the rate limit.

        This method will block until it's safe to make another API call
        without exceeding the configured rate limit.
        """
        while True:
            with self._lock:
                now = time.time()
                cutoff_time = now - self.period
                while self._call_times and self._call_times[0] <= cutoff_time:
                    self._call_times.popleft()

                if len(self._call_times) < self.max_calls:
                    self._call_times.append(now)
                    return

                wait_time = self._call_times[0] + self.period - now

            # Another waiter can claim the slot while we sleep, so check again.
            logger.info(f"Rate limit reached. Waiting {wait_time:.2f}s before next request")
            time.sleep(wait_time)

    def reset(self) -> None:
        """Reset the rate limiter, clearing all recorded calls."""
        with self._lock:
            self._call_times.clear()
            logger.debug("Rate limiter reset")

    @property
    def available_calls(self) -> int:
        """
        Get the number of calls that can be made immediately.

        Returns:
            Number of available calls without waiting
        """
        with self._lock:
            now = time.time()
            cutoff_time = now - self.period

            # Remove outdated timestamps
            while self._call_times and self._call_times[0] <= cutoff_time:
                self._call_times.popleft()

            return max(0, self.max_calls - len(self._call_times))

    @property
    def next_available_time(self) -> float | None:
        """
        Get the timestamp when the next call will be available.

        Returns:
            Unix timestamp when next call can be made, or None if calls are available now
        """
        with self._lock:
            now = time.time()
            cutoff_time = now - self.period

            # Remove outdated timestamps
            while self._call_times and self._call_times[0] <= cutoff_time:
                self._call_times.popleft()

            if len(self._call_times) < self.max_calls:
                return None  # Calls available now

            # Return when the oldest call will exit the window
            return self._call_times[0] + self.period
