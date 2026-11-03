"""Disaster Emergency Fund Code reference model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DefCode:
    """Legislative and reference information for one DEF code.

    Attributes:
        code: The DEF code identifier.
        public_law: Associated public law reference.
        title: Optional descriptive title of the fund.
        urls: Optional list of related URLs for additional information.
        disaster: Optional disaster category or description.
    """

    code: str
    public_law: str
    title: str | None = None
    urls: list[str] | None = None
    disaster: str | None = None

    @classmethod
    def _from_api_data(cls, data: dict[str, Any]) -> DefCode:
        """Build a DEF code while normalizing historical URL response shapes.

        Args:
            data: One DEF code row from an API response.

        Returns:
            DefCode: The parsed code, with ``urls`` coerced to a list or None.
        """
        raw_urls = data.get("urls")
        if isinstance(raw_urls, str):
            urls = [raw_urls] if raw_urls else None
        elif isinstance(raw_urls, list):
            urls = list(raw_urls)
        else:
            urls = None

        return cls(
            code=data.get("code", ""),
            public_law=data.get("public_law", ""),
            title=data.get("title"),
            urls=urls,
            disaster=data.get("disaster"),
        )
