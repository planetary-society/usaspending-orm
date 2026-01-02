"""Tests for Agency model TAS integration."""


from usaspending.models.agency import Agency
from usaspending.queries.federal_accounts_query import FederalAccountsQuery


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

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", tas_codes_fixture
        )

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

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", tas_codes_fixture
        )

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
        federal_accounts_fixture = load_fixture("tas_federal_accounts.json")
        tas_codes_fixture = load_fixture("tas_codes.json")

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )
        # Set up response for each federal account (using same fixture for simplicity)
        for result in federal_accounts_fixture["results"]:
            account_id = result["id"]
            mock_usa_client.set_response(
                f"/references/filter_tree/tas/080/{account_id}/", tas_codes_fixture
            )

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
