"""Tests for Disaster Emergency Fund Code reference models."""

import pytest

from usaspending.models import DefCode


@pytest.mark.parametrize(
    ("raw_urls", "expected"),
    [
        ("https://example.test/law", ["https://example.test/law"]),
        ("", None),
        (None, None),
    ],
)
def test_from_api_data_normalizes_non_list_urls(raw_urls, expected):
    """Legacy URL response shapes normalize to the public list-or-none shape."""
    code = DefCode._from_api_data(
        {
            "code": "A",
            "public_law": "P.L. 1-1",
            "urls": raw_urls,
        }
    )

    assert code.urls == expected


def test_from_api_data_copies_url_lists():
    """The model does not alias the mutable API response list."""
    urls = ["https://example.test/law"]

    code = DefCode._from_api_data(
        {
            "code": "A",
            "public_law": "P.L. 1-1",
            "urls": urls,
        }
    )
    urls.append("https://example.test/changed")

    assert code.urls == ["https://example.test/law"]


def test_from_api_data_preserves_defaults_and_optional_fields():
    """The shared factory retains the existing Agency conversion defaults."""
    code = DefCode._from_api_data({"title": "Emergency funding", "disaster": "test"})

    assert code.code == ""
    assert code.public_law == ""
    assert code.title == "Emergency funding"
    assert code.disaster == "test"
