"""Tests for Agency model TAS integration."""

from tests.mocks import MockUSASpendingClient
from usaspending.models.agency import Agency
from usaspending.queries.federal_accounts_query import FederalAccountsQuery


def seed_tas_tree(mock_usa_client, load_fixture) -> dict:
    """Seed agency 080's account level and the TAS level under every account.

    Seeds from the fixture rather than by iterating the query, so setup does not
    consume the account-level fetch that the request-count tests are measuring.
    Registering a response issues no request, so a test may take its baseline
    count after calling this.

    Returns:
        dict: The account-level fixture, whose ``results`` name the seeded accounts.
    """
    accounts = load_fixture("tas_federal_accounts.json")
    mock_usa_client.set_response("/references/filter_tree/tas/080/", accounts)
    tas_codes = load_fixture("tas_codes.json")
    for account in accounts["results"]:
        mock_usa_client.set_response(f"/references/filter_tree/tas/080/{account['id']}/", tas_codes)
    return accounts


def seeded_account_count(accounts_fixture: dict) -> int:
    """Report how many accounts a seeded fixture holds, refusing an empty one.

    Request-count claims are stated per seeded account, so they have to be
    measured against the fixture rather than against the accounts the walk being
    measured produced: a parser that dropped every row would otherwise satisfy
    its own budget. An emptied fixture would make that comparison 0 == 0, so it
    is rejected here, once, for every test that counts.

    Args:
        accounts_fixture: The account-level fixture ``seed_tas_tree`` returned.

    Returns:
        int: The number of accounts seeded, which is never zero.
    """
    count = len(accounts_fixture["results"])
    assert count > 0, "the fixture must seed accounts for a per-account count to mean anything"
    return count


class TestAgencyFederalAccountsProperty:
    """Test Agency.federal_accounts property."""

    def test_federal_accounts_returns_query(self, mock_usa_client):
        """Test federal_accounts returns FederalAccountsQuery instance."""
        data = {
            "toptier_agency": {
                "toptier_code": "080",
                "abbreviation": "NASA",
                "name": "National Aeronautics and Space Administration",
            }
        }
        agency = Agency(data, mock_usa_client)

        assert isinstance(agency.federal_accounts, FederalAccountsQuery)

    def test_federal_accounts_query_has_correct_toptier_code(self, mock_usa_client):
        """Test federal_accounts query is initialized with correct toptier_code."""
        data = {
            "toptier_agency": {
                "toptier_code": "080",
                "abbreviation": "NASA",
                "name": "National Aeronautics and Space Administration",
            }
        }
        agency = Agency(data, mock_usa_client)

        assert agency.federal_accounts._toptier_code == "080"

    def test_federal_accounts_with_missing_code(self, mock_usa_client):
        """Test federal_accounts with missing toptier_code returns empty query."""
        data = {
            "toptier_agency": {
                "abbreviation": "TEST",
                "name": "Test Agency",
            }
        }
        agency = Agency(data, mock_usa_client)

        # Should return query with empty toptier_code
        assert agency.federal_accounts._toptier_code == ""

    def test_federal_accounts_iteration(self, mock_usa_client, load_fixture):
        """Test iterating over federal_accounts."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        data = {
            "toptier_agency": {
                "toptier_code": "080",
                "abbreviation": "NASA",
                "name": "National Aeronautics and Space Administration",
            }
        }
        agency = Agency(data, mock_usa_client)

        accounts = list(agency.federal_accounts)

        assert len(accounts) == 16
        from usaspending.models.federal_account import FederalAccount

        assert all(isinstance(a, FederalAccount) for a in accounts)

    def test_federal_accounts_count(self, mock_usa_client, load_fixture):
        """Test count() on federal_accounts."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        data = {
            "toptier_agency": {
                "toptier_code": "080",
                "abbreviation": "NASA",
                "name": "National Aeronautics and Space Administration",
            }
        }
        agency = Agency(data, mock_usa_client)

        assert agency.federal_accounts.count() == 16


class TestAgencyFederalAccountChain:
    """Test chaining from Agency to TAS codes."""

    def test_chain_to_tas_codes(self, mock_usa_client, load_fixture):
        """Test chaining agency.federal_accounts[0].tas_codes."""
        federal_accounts_fixture = load_fixture("tas_federal_accounts.json")
        tas_codes_fixture = load_fixture("tas_codes.json")

        mock_usa_client.set_response("/references/filter_tree/tas/080/", federal_accounts_fixture)
        mock_usa_client.set_response("/references/filter_tree/tas/080/080-0120/", tas_codes_fixture)

        data = {
            "toptier_agency": {
                "toptier_code": "080",
                "abbreviation": "NASA",
                "name": "National Aeronautics and Space Administration",
            }
        }
        agency = Agency(data, mock_usa_client)

        # Get Science account (080-0120)
        accounts = agency.federal_accounts.all()
        science = next((a for a in accounts if a.id == "080-0120"), None)
        assert science is not None

        # Get TAS codes
        tas_codes = science.tas_codes.all()
        assert len(tas_codes) == 16

    def test_chain_with_fiscal_year_filter(self, mock_usa_client, load_fixture):
        """Test filtering TAS codes by fiscal year."""
        federal_accounts_fixture = load_fixture("tas_federal_accounts.json")
        tas_codes_fixture = load_fixture("tas_codes.json")

        mock_usa_client.set_response("/references/filter_tree/tas/080/", federal_accounts_fixture)
        mock_usa_client.set_response("/references/filter_tree/tas/080/080-0120/", tas_codes_fixture)

        data = {
            "toptier_agency": {
                "toptier_code": "080",
                "abbreviation": "NASA",
                "name": "National Aeronautics and Space Administration",
            }
        }
        agency = Agency(data, mock_usa_client)

        # Get Science account
        accounts = agency.federal_accounts.all()
        science = next((a for a in accounts if a.id == "080-0120"), None)

        # Filter TAS codes by fiscal year 2024
        fy_2024_tas = [t for t in science.tas_codes if t.fiscal_year(2024)]

        # Should include X (no-year) accounts
        assert any(t.availability_type_code == "X" for t in fy_2024_tas)

    def test_chain_iteration_pattern(self, mock_usa_client, load_fixture):
        """Test typical iteration pattern across all levels."""
        seed_tas_tree(mock_usa_client, load_fixture)

        data = {
            "toptier_agency": {
                "toptier_code": "080",
                "abbreviation": "NASA",
                "name": "National Aeronautics and Space Administration",
            }
        }
        agency = Agency(data, mock_usa_client)

        # Iterate over all federal accounts and their TAS codes
        total_tas_count = 0
        for account in agency.federal_accounts:
            for _tas in account.tas_codes:
                total_tas_count += 1

        # 16 accounts * 16 TAS codes each = 256
        assert total_tas_count == 256


class TestFederalAccountsFetchedOnce:
    """The federal-account level is fetched once per Agency, not once per read.

    federal_accounts used to build a fresh query on every access, so the three
    reads its own docstring demonstrates cost three requests for one level, and a
    walk over N accounts reading tas_codes cost 2N.
    """

    def _agency(self, mock_usa_client, load_fixture):
        """An agency whose whole TAS subtree is answerable, with nothing fetched.

        Returns:
            tuple: The agency, and the account-level fixture it was seeded from,
            which is what the request-count expectations are measured against.
        """
        accounts_fixture = seed_tas_tree(mock_usa_client, load_fixture)
        return Agency({"toptier_code": "080"}, mock_usa_client), accounts_fixture

    def test_repeated_reads_cost_one_request(self, mock_usa_client, load_fixture):
        agency, _ = self._agency(mock_usa_client, load_fixture)
        before = mock_usa_client.get_request_count()

        len(agency.federal_accounts)
        agency.federal_accounts.code("080-0120").first()
        agency.federal_accounts.description("science").all()
        agency.federal_accounts[0]

        assert mock_usa_client.get_request_count() - before == 1

    def test_each_read_returns_an_independent_query(self, mock_usa_client, load_fixture):
        agency, _ = self._agency(mock_usa_client, load_fixture)

        assert agency.federal_accounts is not agency.federal_accounts

        expected = len(agency.federal_accounts)
        agency.federal_accounts.all().pop()

        assert len(agency.federal_accounts) == expected

    def test_nested_walk_costs_one_request_per_level(self, mock_usa_client, load_fixture):
        """The docstring's own pattern: iterate accounts, read each one's codes."""
        agency, accounts_fixture = self._agency(mock_usa_client, load_fixture)
        expected_accounts = seeded_account_count(accounts_fixture)

        before = mock_usa_client.get_request_count()
        accounts = list(agency.federal_accounts)
        for account in accounts:
            len(account.tas_codes)
            account.tas_codes.all()

        assert len(accounts) == expected_accounts
        # One for the account level, one per account for its TAS level.
        assert mock_usa_client.get_request_count() - before == 1 + expected_accounts

    def test_an_agency_without_a_code_makes_no_request(self, mock_usa_client):
        agency = Agency({"name": "Unknown"}, mock_usa_client)
        agency._details_fetched = True
        before = mock_usa_client.get_request_count()

        assert agency.federal_accounts.all() == []
        assert mock_usa_client.get_request_count() == before

    def test_reading_the_property_alone_makes_no_request(self, mock_usa_client, load_fixture):
        """Caching must not cost laziness.

        The cache is reached through a callable for exactly this reason: handing
        the models to the query directly would evaluate the cache here, at
        property-access time, and fetch a level nobody has asked to see yet.
        """
        agency, _ = self._agency(mock_usa_client, load_fixture)
        before = mock_usa_client.get_request_count()

        query = agency.federal_accounts
        query = query.description("science")

        assert mock_usa_client.get_request_count() == before
        assert len(query.all()) > 0, "still fetches once someone reads it"

    def test_filtering_by_fiscal_year_costs_one_request_per_level(
        self, mock_usa_client, load_fixture
    ):
        """The pattern the TAS docstrings demonstrate, over a whole agency.

        fiscal_year() filters in memory, so each additional year should be free.
        Before the level was cached per model, every filter on every account
        re-fetched, and three years over 16 accounts cost ~51 requests.
        """
        agency, accounts_fixture = self._agency(mock_usa_client, load_fixture)
        expected_accounts = seeded_account_count(accounts_fixture)

        before = mock_usa_client.get_request_count()
        accounts = agency.federal_accounts.all()
        for account in accounts:
            for year in (2023, 2024, 2025):
                account.tas_codes.fiscal_year(year).all()

        assert len(accounts) == expected_accounts
        assert mock_usa_client.get_request_count() - before == 1 + expected_accounts

    def test_the_cross_level_filter_costs_one_request_per_level(
        self, mock_usa_client, load_fixture
    ):
        """FederalAccountsQuery.fiscal_year reads tas_codes for every account.

        This is the expensive filter and the one the request-count claim rests on:
        its predicate crosses into the level below, so before the levels were cached
        per model it re-fetched every account's codes on every call.
        """
        agency, accounts_fixture = self._agency(mock_usa_client, load_fixture)
        accounts = seeded_account_count(accounts_fixture)

        before = mock_usa_client.get_request_count()
        for year in (2023, 2024, 2025):
            agency.federal_accounts.fiscal_year(year).all()

        # One for the account level, one per account for the codes its predicate reads.
        assert mock_usa_client.get_request_count() - before == 1 + accounts

    def test_a_recursive_reattach_rebinds_the_cache_without_refetching(
        self, mock_usa_client, load_fixture
    ):
        """The cached models hold a weak reference to the client they were built with.

        Left alone they would raise DetachedInstanceError once that client went
        away. Rebinding them in place fixes that and keeps the level, where
        discarding the cache would be equally correct but would refetch every level
        already fetched. The replacement is deliberately given no responses, so any
        request at all is a failure.
        """
        seed_tas_tree(mock_usa_client, load_fixture)
        agency = Agency({"toptier_code": "080"}, mock_usa_client)
        len(agency.federal_accounts[0].tas_codes)

        replacement = MockUSASpendingClient()
        agency.reattach(replacement, recursive=True)
        accounts = agency.federal_accounts.all()
        codes = accounts[0].tas_codes.all()

        assert replacement.get_request_count() == 0
        assert len(accounts) == 16
        assert all(account._client is replacement for account in accounts)
        assert all(code._client is replacement for code in codes)

    def test_a_non_recursive_reattach_discards_the_cache(self, mock_usa_client, load_fixture):
        """It leaves nested models alone, so it cannot rebind them and must drop them.

        The next read rebuilds against whichever client is current, which is what
        an uncached property did anyway. Keeping the cache instead would hand back
        accounts bound to a client on its way out.
        """
        accounts = seed_tas_tree(mock_usa_client, load_fixture)
        agency = Agency({"toptier_code": "080"}, mock_usa_client)
        agency.federal_accounts.all()

        replacement = MockUSASpendingClient()
        replacement.set_response("/references/filter_tree/tas/080/", accounts)
        agency.reattach(replacement, recursive=False)

        assert all(a._client is replacement for a in agency.federal_accounts.all())
