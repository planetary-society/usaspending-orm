"""Shared test fixtures for USASpending API tests."""

import json
import copy
import pytest
from unittest.mock import Mock
from pathlib import Path

from tests.mocks import MockUSASpendingClient
from usaspending.config import config


@pytest.fixture(autouse=True)
def default_test_config():
    """
    This fixture automatically sets the baseline configuration for all tests.
    It runs before any other test-specific fixture.
    """
    config.configure(
        cache_enabled=False,
        max_retries=0,
        timeout=0.01,
        retry_delay=0.01,
        retry_backoff=0.01,
        rate_limit_calls=10000
    )

@pytest.fixture
def client_config():
    """
    This fixture provides the `config.configure` function to a test,
    ensuring that the original configuration is restored after the test completes.
    """
    # 1. Save a copy of the config object's state dictionary
    original_config_vars = copy.deepcopy(vars(config))

    # 2. Yield the configure function to the test for modification
    yield config.configure

    # 3. Teardown: Restore the original state using the public `configure()` method
    # Unpacking the saved dictionary as keyword arguments is the key.
    config.configure(**original_config_vars)

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
    client = MockUSASpendingClient()
    return client


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