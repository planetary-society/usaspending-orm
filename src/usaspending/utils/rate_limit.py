"""Rate limiting implementation for USASpending API client."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Optional


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
            raise ValueError("max_calls must be positive")
        if period <= 0:
            raise ValueError("period must be positive")
            
        self.max_calls = max_calls
        self.period = period
        self._call_times: Deque[float] = deque()
        self._lock = threading.Lock()
    
    def wait_if_needed(self) -> None:
        """
        Wait if necessary to avoid exceeding the rate limit.
        
        This method will block until it's safe to make another API call
        without exceeding the configured rate limit.
        """
        with self._lock:
            now = time.time()
            
            # Remove timestamps outside the current window
            cutoff_time = now - self.period
            while self._call_times and self._call_times[0] <= cutoff_time:
                self._call_times.popleft()
            
            # If we're at the limit, calculate how long to wait
            if len(self._call_times) >= self.max_calls:
                # Wait until the oldest call exits the window
                oldest_call = self._call_times[0]
                wait_time = (oldest_call + self.period) - now
                
                if wait_time > 0:
                    # Release lock while sleeping to allow other threads
                    self._lock.release()
                    try:
                        time.sleep(wait_time)
                    finally:
                        self._lock.acquire()
                    
                    # Re-check and clean up after sleeping
                    now = time.time()
                    cutoff_time = now - self.period
                    while self._call_times and self._call_times[0] <= cutoff_time:
                        self._call_times.popleft()
            
            # Record this call
            self._call_times.append(now)
    
    def reset(self) -> None:
        """Reset the rate limiter, clearing all recorded calls."""
        with self._lock:
            self._call_times.clear()
    
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
    def next_available_time(self) -> Optional[float]:
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