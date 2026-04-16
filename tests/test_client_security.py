"""Security-relevant behavior of the core client.

Covers the download-URL allow-list and config validation hardening
introduced in v0.7.1.
"""

from __future__ import annotations

import pytest

from usaspending.client import USASpendingClient
from usaspending.exceptions import ConfigurationError, DownloadError


def test_download_binary_rejects_host_not_in_allow_list(tmp_path, client_config) -> None:
    """Binary downloads outside the allow-list raise DownloadError.

    Regression: before v0.7.1 any absolute URL in an API response would be
    fetched verbatim, allowing SSRF via tampered responses (e.g., redirect
    to metadata services or attacker-controlled hosts).
    """
    client_config(allowed_download_hosts=frozenset({"files.usaspending.gov"}))

    client = USASpendingClient()
    try:
        with pytest.raises(DownloadError, match=r"not in .*allowed_download_hosts"):
            client._download_binary_file(
                "https://attacker.example.com/payload.zip",
                str(tmp_path / "out.zip"),
            )
    finally:
        client.close()


def test_download_binary_rejects_non_https(tmp_path, client_config) -> None:
    """Non-HTTPS downloads are rejected even if the host is allow-listed."""
    client_config(allowed_download_hosts=frozenset({"files.usaspending.gov"}))

    client = USASpendingClient()
    try:
        with pytest.raises(DownloadError, match="non-https scheme"):
            client._download_binary_file(
                "http://files.usaspending.gov/report.zip",
                str(tmp_path / "out.zip"),
            )
    finally:
        client.close()


def test_config_rejects_non_url_base_url(client_config) -> None:
    """config.validate now rejects base_url that is not an http(s) URL."""
    with pytest.raises(ConfigurationError, match="base_url must be an absolute"):
        client_config(base_url="not-a-url")


def test_config_rejects_crlf_in_user_agent(client_config) -> None:
    """CRLF in user_agent could enable header-injection into logs or proxies."""
    with pytest.raises(ConfigurationError, match="CR/LF"):
        client_config(user_agent="usaspending-orm/0.7.1\r\nX-Injected: yes")
