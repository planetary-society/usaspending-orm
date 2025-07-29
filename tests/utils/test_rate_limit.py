"""Tests for the RateLimiter class."""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

from usaspending.utils.rate_limit import RateLimiter


class TestRateLimiterInitialization:
    """Test RateLimiter initialization and validation."""
    
    def test_valid_initialization(self):
        """Test creating a rate limiter with valid parameters."""
        limiter = RateLimiter(max_calls=10, period=1.0)
        assert limiter.max_calls == 10
        assert limiter.period == 1.0
        assert limiter.available_calls == 10
    
    def test_invalid_max_calls(self):
        """Test that invalid max_calls raises ValueError."""
        with pytest.raises(ValueError, match="max_calls must be positive"):
            RateLimiter(max_calls=0, period=1.0)
        
        with pytest.raises(ValueError, match="max_calls must be positive"):
            RateLimiter(max_calls=-1, period=1.0)
    
    def test_invalid_period(self):
        """Test that invalid period raises ValueError."""
        with pytest.raises(ValueError, match="period must be positive"):
            RateLimiter(max_calls=10, period=0)
        
        with pytest.raises(ValueError, match="period must be positive"):
            RateLimiter(max_calls=10, period=-1.0)


class TestRateLimiterBasicFunctionality:
    """Test basic rate limiting functionality."""
    
    def test_single_call_no_wait(self):
        """Test that a single call doesn't require waiting."""
        limiter = RateLimiter(max_calls=1, period=1.0)
        
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1  # Should be instant
        assert limiter.available_calls == 0
    
    def test_multiple_calls_within_limit(self):
        """Test multiple calls within the rate limit."""
        limiter = RateLimiter(max_calls=3, period=1.0)
        
        start_time = time.time()
        for _ in range(3):
            limiter.wait_if_needed()
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1  # All should be instant
        assert limiter.available_calls == 0
    
    def test_exceeding_limit_causes_wait(self):
        """Test that exceeding the limit causes a wait."""
        limiter = RateLimiter(max_calls=2, period=0.005)
        
        # Make two calls (at the limit)
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        # Third call should wait
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time
        
        assert elapsed >= 0.004  # Should wait almost the full period
        assert elapsed < 0.008  # But not too long
    
    def test_sliding_window(self):
        """Test that the sliding window works correctly."""
        limiter = RateLimiter(max_calls=2, period=0.003)
        
        # Make first call
        limiter.wait_if_needed()
        
        # Wait half the period
        time.sleep(0.0015)
        
        # Make second call
        limiter.wait_if_needed()
        
        # Third call should only wait for first call to expire
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time
        
        # Should wait about 0.0015s (0.003s period - 0.0015s already elapsed)
        assert 0.001 <= elapsed <= 0.002
    
    def test_reset(self):
        """Test that reset() clears the call history."""
        limiter = RateLimiter(max_calls=1, period=10.0)
        
        # Use up the limit
        limiter.wait_if_needed()
        assert limiter.available_calls == 0
        
        # Reset should clear history
        limiter.reset()
        assert limiter.available_calls == 1
        
        # Should be able to call immediately
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time
        assert elapsed < 0.1


class TestRateLimiterProperties:
    """Test RateLimiter properties."""
    
    def test_available_calls_property(self):
        """Test the available_calls property."""
        limiter = RateLimiter(max_calls=3, period=0.005)
        
        assert limiter.available_calls == 3
        
        limiter.wait_if_needed()
        assert limiter.available_calls == 2
        
        limiter.wait_if_needed()
        assert limiter.available_calls == 1
        
        limiter.wait_if_needed()
        assert limiter.available_calls == 0
        
        # Wait for calls to expire
        time.sleep(0.006)
        assert limiter.available_calls == 3
    
    def test_next_available_time_property(self):
        """Test the next_available_time property."""
        limiter = RateLimiter(max_calls=1, period=0.01)
        
        # Should be None when calls are available
        assert limiter.next_available_time is None
        
        # Make a call
        call_time = time.time()
        limiter.wait_if_needed()
        
        # Should return when the call expires
        next_time = limiter.next_available_time
        assert next_time is not None
        assert abs(next_time - (call_time + 0.01)) < 0.001
        
        # Wait for it to expire
        time.sleep(0.011)
        assert limiter.next_available_time is None


class TestRateLimiterThreadSafety:
    """Test thread safety of the RateLimiter."""
    
    def test_concurrent_calls_respect_limit(self):
        """Test that concurrent calls from multiple threads respect the limit."""
        limiter = RateLimiter(max_calls=5, period=0.01)
        call_times = []
        lock = threading.Lock()
        
        def make_call():
            limiter.wait_if_needed()
            with lock:
                call_times.append(time.time())
        
        # Start 10 threads trying to make calls
        threads = []
        start_time = time.time()
        
        for _ in range(10):
            thread = threading.Thread(target=make_call)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that rate limit was respected
        call_times.sort()
        
        # First 5 calls should be immediate
        for i in range(5):
            assert call_times[i] - start_time < 0.002
        
        # Next 5 calls should be after 0.01 second
        for i in range(5, 10):
            assert call_times[i] - start_time >= 0.009
    
    def test_concurrent_property_access(self):
        """Test that properties can be accessed safely from multiple threads."""
        limiter = RateLimiter(max_calls=10, period=1.0)
        results = []
        lock = threading.Lock()
        
        def check_properties():
            for _ in range(100):
                calls = limiter.available_calls
                next_time = limiter.next_available_time
                with lock:
                    results.append((calls, next_time))
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=check_properties)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should have collected results without errors
        assert len(results) == 500


class TestRateLimiterEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_fractional_period(self):
        """Test rate limiter with fractional second periods."""
        limiter = RateLimiter(max_calls=2, period=0.001)
        
        # Should be able to make rapid calls after period expires
        for _ in range(5):
            limiter.wait_if_needed()
            limiter.wait_if_needed()
            time.sleep(0.0011)  # Just over the period
    
    def test_high_frequency_calls(self):
        """Test with high frequency rate limit."""
        limiter = RateLimiter(max_calls=100, period=1.0)
        
        # Should be able to make 100 calls instantly
        start_time = time.time()
        for _ in range(100):
            limiter.wait_if_needed()
        elapsed = time.time() - start_time
        
        assert elapsed < 0.5  # Should be very fast
    
    def test_long_period(self):
        """Test with a long period."""
        limiter = RateLimiter(max_calls=1, period=3600.0)  # 1 hour
        
        # Make one call
        limiter.wait_if_needed()
        
        # Next available time should be an hour away
        next_time = limiter.next_available_time
        assert next_time is not None
        assert next_time - time.time() > 3599.0
    
    @patch('time.time')
    @patch('time.sleep')
    def test_time_precision(self, mock_sleep, mock_time):
        """Test that time calculations handle precision correctly."""
        # Mock time to control it precisely
        current_time = 1000.0
        mock_time.return_value = current_time
        
        limiter = RateLimiter(max_calls=1, period=1.0)
        
        # First call
        limiter.wait_if_needed()
        
        # Try second call immediately
        limiter.wait_if_needed()
        
        # Should have slept for exactly 1 second
        mock_sleep.assert_called_once_with(1.0)
    
    def test_cleanup_old_calls(self):
        """Test that old calls are properly cleaned up."""
        limiter = RateLimiter(max_calls=1000, period=0.001)
        
        # Make many calls over time
        for i in range(100):
            limiter.wait_if_needed()
            if i % 10 == 0:
                time.sleep(0.0002)  # Small delay every 10 calls
        
        # Internal deque should not grow unbounded
        # After period expires, old calls should be cleaned up
        time.sleep(0.0015)
        
        # All calls should be available again
        assert limiter.available_calls == 1000