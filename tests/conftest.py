"""Shared test fixtures for USASpending API tests."""

import json
import copy
import pytest
from pathlib import Path

from tests.mocks import MockUSASpendingClient
from usaspending.config import config


@pytest.fixture(autouse=True)
def default_test_config():
    """
    This fixture automatically sets the baseline configuration for all tests.
    It runs before any other test-specific fixture.
    
    Note: No logging configuration is needed here - the library uses NullHandler
    by default, so tests run silently unless explicitly configured.
    """
    config.configure(
        cache_enabled=False,
        max_retries=0,
        timeout=0.01,
        retry_delay=0.01,
        retry_backoff=0.01,
        rate_limit_calls=10000,
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


def load_json_fixture(relative_path):
    """Helper to load a JSON fixture file given a relative path from the test directory."""
    fixture_path = Path(__file__).parent / "fixtures" / relative_path
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def load_fixture():
    """General fixture loader that returns a function to load any fixture file."""

    def _load(relative_path):
        return load_json_fixture(relative_path)

    return _load


@pytest.fixture
def award_fixture_data():
    """Load the award fixture data."""
    return load_json_fixture("awards/contract.json")


@pytest.fixture
def contract_fixture_data():
    """Load the award fixture data."""
    return load_json_fixture("awards/contract.json")


@pytest.fixture
def idv_fixture_data():
    """Load the award fixture data."""
    return load_json_fixture("awards/idv.json")


@pytest.fixture
def grant_fixture_data():
    """Load the award fixture data."""
    return load_json_fixture("awards/grant.json")


@pytest.fixture
def loan_fixture_data():
    """Load the loan fixture data."""
    return load_json_fixture("awards/loan.json")


@pytest.fixture
def top_recipients_response():
    """Load the top recipients response fixture."""
    return load_json_fixture("top_recipients_response.json")


@pytest.fixture
def search_results_contracts_data():
    """Load the search results fixture data for contracts."""
    return load_json_fixture("awards/search_results_contracts.json")["results"]


@pytest.fixture
def search_results_grants_data():
    """Load the search results fixture data for grants."""
    return load_json_fixture("awards/search_results_grants.json")["results"]


@pytest.fixture
def search_results_idvs_data():
    """Load the search results fixture data for IDVs."""
    return load_json_fixture("awards/search_results_idvs.json")["results"]


@pytest.fixture
def agency_fixture_data():
    """Load the agency fixture data."""
    return load_json_fixture("agency.json")


@pytest.fixture
def agency_award_summary_fixture_data():
    """Load the agency award summary fixture data."""
    return load_json_fixture("agency_award_summary.json")


@pytest.fixture
def agency_subagencies_fixture_data():
    """Load the agency sub-agencies fixture data."""
    return load_json_fixture("agency_subagencies.json")


@pytest.fixture
def agency_autocomplete_fixture():
    """Load agency autocomplete fixture data."""
    return load_json_fixture("agency_autocomplete.json")


@pytest.fixture
def recipients_search_fixture_data():
    """Load the recipients search fixture data."""
    return load_json_fixture("recipients_search.json")
