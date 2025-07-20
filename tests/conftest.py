"""Shared test fixtures for USASpending API tests."""

import json
import pytest
from unittest.mock import Mock
from pathlib import Path

from usaspending.client import USASpending
from usaspending.config import Config
from tests.mocks import MockUSASpendingClient


@pytest.fixture
def mock_client():
    """Create a mock USASpending client for testing.
    
    Mocks the _make_request method to avoid actual API calls.
    Uses optimized settings for faster test execution.
    """
    config = Config(
        cache_backend="memory",
        rate_limit_calls=1000,
        max_retries=0,  # Disable retries for faster tests
    )
    client = USASpending(config)
    client._make_request = Mock()
    return client


@pytest.fixture
def mock_usa_client():
    """Create a MockUSASpendingClient for testing.
    
    This is the new recommended way to mock the USASpending client.
    It provides better functionality for testing pagination, errors,
    and complex scenarios.
    
    Example:
        def test_award_search(mock_usa_client):
            mock_usa_client.mock_award_search([
                {"Award ID": "123", "Recipient Name": "Test Corp"}
            ])
            
            results = list(mock_usa_client.awards.search().with_award_types("A"))
            assert len(results) == 1
    """
    return MockUSASpendingClient()


@pytest.fixture
def award_fixture_data():
    """Load the award fixture data."""
    fixture_path = Path(__file__).parent / "fixtures" / "awards" / "contract.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def top_recipients_response():
    """Load the top recipients response fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "top_recipients_response.json"
    with open(fixture_path) as f:
        return json.load(f)