"""Tests for configuration module."""

import pytest
from unittest.mock import patch
from datetime import timedelta
from usaspending.config import _Config
from usaspending.exceptions import ConfigurationError


class TestCacheBackendConfiguration:
    """Test cache backend configuration settings."""

    def test_file_backend_passes_cache_dir(self, client_config):
        """Test that file backend passes cache_dir to cachier."""
        with patch("usaspending.config.cachier") as mock_cachier:
            client_config(cache_enabled=True, cache_backend="file")

            # Verify set_global_params was called with cache_dir
            assert mock_cachier.set_global_params.called
            call_kwargs = mock_cachier.set_global_params.call_args[1]
            assert "cache_dir" in call_kwargs
            assert "backend" in call_kwargs
            assert call_kwargs["backend"] == "pickle"
            assert mock_cachier.enable_caching.called

    def test_memory_backend_omits_cache_dir(self, client_config):
        """Test that memory backend does not pass cache_dir to cachier."""
        with patch("usaspending.config.cachier") as mock_cachier:
            client_config(cache_enabled=True, cache_backend="memory")

            # Verify set_global_params was called without cache_dir
            assert mock_cachier.set_global_params.called
            call_kwargs = mock_cachier.set_global_params.call_args[1]
            assert "cache_dir" not in call_kwargs
            assert "backend" in call_kwargs
            assert call_kwargs["backend"] == "memory"
            assert mock_cachier.enable_caching.called

    def test_cache_disabled_calls_disable_caching(self, client_config):
        """Test that cache_enabled=False calls disable_caching."""
        with patch("usaspending.config.cachier") as mock_cachier:
            client_config(cache_enabled=False)

            assert mock_cachier.disable_caching.called
            # enable_caching might have been called during initialization
            # so we just verify disable was called

    def test_both_backends_use_stale_after(self, client_config):
        """Test that both backends use stale_after parameter."""
        test_ttl = timedelta(hours=12)

        # Test file backend
        with patch("usaspending.config.cachier") as mock_cachier:
            client_config(cache_enabled=True, cache_backend="file", cache_ttl=test_ttl)

            call_kwargs = mock_cachier.set_global_params.call_args[1]
            assert call_kwargs["stale_after"] == test_ttl

        # Test memory backend
        with patch("usaspending.config.cachier") as mock_cachier:
            client_config(
                cache_enabled=True, cache_backend="memory", cache_ttl=test_ttl
            )

            call_kwargs = mock_cachier.set_global_params.call_args[1]
            assert call_kwargs["stale_after"] == test_ttl


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_invalid_cache_backend_raises_error(self):
        """Test that invalid cache backend raises ConfigurationError."""
        test_config = _Config()
        with pytest.raises(ConfigurationError, match="cache_backend must be one of"):
            test_config.configure(cache_enabled=True, cache_backend="redis")

    def test_valid_backends_accepted(self):
        """Test that valid backends are accepted."""
        # These should not raise errors
        test_config = _Config()
        test_config.configure(cache_enabled=True, cache_backend="file")

        test_config2 = _Config()
        test_config2.configure(cache_enabled=True, cache_backend="memory")

    def test_negative_timeout_raises_error(self):
        """Test that negative timeout raises ConfigurationError."""
        test_config = _Config()
        with pytest.raises(ConfigurationError, match="timeout must be positive"):
            test_config.configure(timeout=-1)

    def test_negative_cache_timeout_raises_error(self):
        """Test that negative cache_timeout raises ConfigurationError."""
        test_config = _Config()
        with pytest.raises(ConfigurationError, match="cache_timeout must be positive"):
            test_config.configure(cache_timeout=-1)


class TestConfigurationSettings:
    """Test configuration settings and defaults."""

    def test_default_cache_disabled(self):
        """Test that cache is disabled by default."""
        test_config = _Config()
        assert test_config.cache_enabled is False

    def test_default_cache_backend_is_file(self):
        """Test that default cache backend is file."""
        test_config = _Config()
        assert test_config.cache_backend == "file"

    def test_default_cache_ttl(self):
        """Test that default cache TTL is 1 week."""
        test_config = _Config()
        assert test_config.cache_ttl == timedelta(weeks=1)

    def test_cache_ttl_from_seconds(self):
        """Test that cache_ttl can be set from seconds."""
        test_config = _Config()
        test_config.configure(cache_ttl=3600)
        assert test_config.cache_ttl == timedelta(seconds=3600)

    def test_unknown_config_key_warning(self, client_config, caplog):
        """Test that unknown config keys generate warnings."""
        client_config(unknown_key="value")
        assert "Unknown configuration key 'unknown_key' was ignored" in caplog.text
