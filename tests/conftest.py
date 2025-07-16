"""Shared test fixtures for USASpending API tests."""

import json
import pytest
from unittest.mock import Mock
from pathlib import Path

from usaspending.client import USASpending
from usaspending.config import Config


@pytest.fixture
def mock_client():
    """Create a mock USASpending client for testing.
    
    Mocks the _make_request method to avoid actual API calls.
    """
    config = Config(
        cache_backend="memory",
        rate_limit_calls=1000,
    )
    client = USASpending(config)
    client._make_request = Mock()
    return client


@pytest.fixture
def award_fixture_data():
    """Load the award fixture data."""
    fixture_path = Path(__file__).parent / "fixtures" / "award.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def top_recipients_response():
    """Load the top recipients response fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "top_recipients_response.json"
    with open(fixture_path) as f:
        return json.load(f)