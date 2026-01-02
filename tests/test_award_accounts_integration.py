"""Integration tests for Award accounts relationship."""

import pytest

from usaspending.models.award import Award
from usaspending.models.award_account import AwardAccount
from usaspending.queries.award_accounts_query import AwardAccountsQuery


class TestAwardAccountsProperty:
    """Tests for accessing accounts through the Award model."""

    @pytest.fixture
    def accounts_fixture(self, load_fixture):
        """Load accounts fixture data."""
        return load_fixture("awards/accounts.json")

    @pytest.fixture
    def first_account_data(self, accounts_fixture):
        """Get first account data from fixture."""
        return accounts_fixture["results"][0]

    @pytest.fixture
    def mock_accounts_response(self, mock_usa_client, accounts_fixture):
        """Set up mock client with accounts response."""
        mock_usa_client.set_response("/awards/accounts/", accounts_fixture)
        return mock_usa_client

    @pytest.fixture
    def award_with_accounts(self, mock_accounts_response):
        """Create Award with mocked accounts response."""
        return Award(
            {"generated_unique_award_id": "CONT_AWD_123"}, mock_accounts_response
        )

    def test_award_accounts_property_returns_query(self, mock_usa_client):
        """Test award.accounts returns an AwardAccountsQuery."""
        award = Award({"generated_unique_award_id": "CONT_AWD_123"}, mock_usa_client)

        accounts_query = award.accounts

        assert isinstance(accounts_query, AwardAccountsQuery)
        assert accounts_query._award_id == "CONT_AWD_123"

    def test_award_accounts_iteration(self, award_with_accounts, accounts_fixture):
        """Test iterating through award.accounts."""
        accounts = list(award_with_accounts.accounts)

        assert len(accounts) == len(accounts_fixture["results"])
        assert all(isinstance(a, AwardAccount) for a in accounts)

    def test_award_accounts_count(self, award_with_accounts, accounts_fixture):
        """Test award.accounts.count()."""
        count = award_with_accounts.accounts.count()

        assert count == accounts_fixture["page_metadata"]["count"]

    def test_award_accounts_order_by(self, award_with_accounts, accounts_fixture):
        """Test award.accounts.order_by()."""
        accounts = award_with_accounts.accounts.order_by("amount", "desc").all()

        assert len(accounts) == len(accounts_fixture["results"])
        assert all(isinstance(a, AwardAccount) for a in accounts)


class TestAwardAccountsDataAccess:
    """Tests for accessing account data through the Award model."""

    @pytest.fixture
    def accounts_fixture(self, load_fixture):
        """Load accounts fixture data."""
        return load_fixture("awards/accounts.json")

    @pytest.fixture
    def first_account_data(self, accounts_fixture):
        """Get first account data from fixture."""
        return accounts_fixture["results"][0]

    @pytest.fixture
    def mock_accounts_response(self, mock_usa_client, accounts_fixture):
        """Set up mock client with accounts response."""
        mock_usa_client.set_response("/awards/accounts/", accounts_fixture)
        return mock_usa_client

    @pytest.fixture
    def award_with_accounts(self, mock_accounts_response):
        """Create Award with mocked accounts response."""
        return Award(
            {"generated_unique_award_id": "CONT_AWD_123"}, mock_accounts_response
        )

    @pytest.fixture
    def first_account(self, award_with_accounts):
        """Get first account from award."""
        return next(iter(award_with_accounts.accounts))

    def test_account_properties_accessible(self, first_account, first_account_data):
        """Test that account properties are accessible through award.accounts."""
        from decimal import Decimal

        expected_amount = Decimal(
            str(first_account_data["total_transaction_obligated_amount"])
        )

        assert first_account.id == first_account_data["federal_account"]
        assert first_account.total_transaction_obligated_amount == expected_amount
        assert (
            first_account.funding_agency_name
            == first_account_data["funding_agency_name"]
        )

    def test_account_funding_agency(self, first_account, first_account_data):
        """Test accessing funding_agency through award.accounts."""
        agency = first_account.funding_agency

        assert agency is not None
        assert agency.name == first_account_data["funding_agency_name"]
        assert agency.abbreviation == first_account_data["funding_agency_abbreviation"]

    def test_account_tas_codes_query(self, first_account, first_account_data):
        """Test accessing tas_codes through award.accounts."""
        federal_account = first_account_data["federal_account"]
        expected_toptier = federal_account.split("-")[0]

        tas_query = first_account.tas_codes

        assert tas_query._toptier_code == expected_toptier
        assert tas_query._federal_account == federal_account


class TestClientAwardAccountsAccess:
    """Tests for accessing award_accounts through the client."""

    @pytest.fixture
    def accounts_fixture(self, load_fixture):
        """Load accounts fixture data."""
        return load_fixture("awards/accounts.json")

    @pytest.fixture
    def mock_accounts_response(self, mock_usa_client, accounts_fixture):
        """Set up mock client with accounts response."""
        mock_usa_client.set_response("/awards/accounts/", accounts_fixture)
        return mock_usa_client

    def test_client_award_accounts_property(self, mock_usa_client):
        """Test client.award_accounts returns resource."""
        resource = mock_usa_client.award_accounts

        assert resource is not None
        assert hasattr(resource, "award_id")

    def test_client_award_accounts_award_id(
        self, mock_accounts_response, accounts_fixture
    ):
        """Test client.award_accounts.award_id()."""
        accounts = list(mock_accounts_response.award_accounts.award_id("CONT_AWD_123"))

        assert len(accounts) == len(accounts_fixture["results"])
        assert all(isinstance(a, AwardAccount) for a in accounts)


class TestAwardAccountsResourceCaching:
    """Tests for resource caching."""

    def test_award_accounts_resource_cached(self, mock_usa_client):
        """Test that award_accounts resource is cached on client."""
        resource1 = mock_usa_client.award_accounts
        resource2 = mock_usa_client.award_accounts

        assert resource1 is resource2
