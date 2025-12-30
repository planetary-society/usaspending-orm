"""Tests for TASResource."""

import pytest

from usaspending.resources.tas_resource import TASResource
from usaspending.models.agency import Agency


class TestTASResourceBasics:
    """Test basic TASResource functionality."""

    def test_init(self, mock_usa_client):
        """Test TASResource initialization."""
        resource = TASResource(mock_usa_client)

        assert resource._client is mock_usa_client

    def test_endpoint(self, mock_usa_client):
        """Test TASResource endpoint."""
        resource = TASResource(mock_usa_client)

        assert resource.ENDPOINT == "/references/filter_tree/tas/"


class TestTASResourceAgencies:
    """Test TASResource.agencies property."""

    def test_agencies_returns_list(self, mock_usa_client, load_fixture):
        """Test agencies property returns list of Agency models."""
        fixture = load_fixture("tas_agencies.json")
        mock_usa_client.set_response("/references/filter_tree/tas/", fixture)

        resource = TASResource(mock_usa_client)
        agencies = resource.agencies

        assert isinstance(agencies, list)
        assert len(agencies) == 91
        assert all(isinstance(a, Agency) for a in agencies)

    def test_agencies_have_correct_properties(self, mock_usa_client, load_fixture):
        """Test returned agencies have correct properties."""
        fixture = load_fixture("tas_agencies.json")
        mock_usa_client.set_response("/references/filter_tree/tas/", fixture)

        resource = TASResource(mock_usa_client)
        agencies = resource.agencies

        # Check first agency (NASA - 080)
        nasa = next((a for a in agencies if a.code == "080"), None)
        assert nasa is not None
        assert "National Aeronautics and Space Administration" in nasa.name

    def test_agencies_returns_consistent_data(self, mock_usa_client, load_fixture):
        """Test agencies property returns consistent data on multiple calls."""
        fixture = load_fixture("tas_agencies.json")
        mock_usa_client.set_response("/references/filter_tree/tas/", fixture)

        resource = TASResource(mock_usa_client)

        # First access
        first_call = resource.agencies
        # Second access
        second_call = resource.agencies

        # Should return same data
        assert len(first_call) == len(second_call)
        assert [a.code for a in first_call] == [a.code for a in second_call]

    def test_agencies_empty_results(self, mock_usa_client):
        """Test agencies property with empty results."""
        mock_usa_client.set_response("/references/filter_tree/tas/", {"results": []})

        resource = TASResource(mock_usa_client)
        agencies = resource.agencies

        assert agencies == []


class TestTASResourceIntegration:
    """Test TASResource integration with Agency model."""

    def test_agencies_can_access_federal_accounts(self, mock_usa_client, load_fixture):
        """Test agencies from TASResource can access federal_accounts property."""
        agencies_fixture = load_fixture("tas_agencies.json")
        mock_usa_client.set_response("/references/filter_tree/tas/", agencies_fixture)

        resource = TASResource(mock_usa_client)
        agencies = resource.agencies

        # Find NASA
        nasa = next((a for a in agencies if a.code == "080"), None)
        assert nasa is not None

        # federal_accounts should return FederalAccountsQuery
        from usaspending.queries.federal_accounts_query import FederalAccountsQuery
        assert isinstance(nasa.federal_accounts, FederalAccountsQuery)

    def test_full_chain_agencies_to_tas_codes(self, mock_usa_client, load_fixture):
        """Test full chain from agencies to TAS codes."""
        agencies_fixture = load_fixture("tas_agencies.json")
        federal_accounts_fixture = load_fixture("tas_federal_accounts.json")
        tas_codes_fixture = load_fixture("tas_codes.json")

        mock_usa_client.set_response("/references/filter_tree/tas/", agencies_fixture)
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", tas_codes_fixture
        )

        resource = TASResource(mock_usa_client)
        agencies = resource.agencies

        # Find NASA
        nasa = next((a for a in agencies if a.code == "080"), None)
        assert nasa is not None

        # Get federal accounts
        accounts = nasa.federal_accounts.all()
        assert len(accounts) == 16

        # Find Science account (080-0120)
        science = next((a for a in accounts if a.id == "080-0120"), None)
        assert science is not None

        # Get TAS codes
        tas_codes = science.tas_codes.all()
        assert len(tas_codes) == 16

        # Check first TAS
        first_tas = tas_codes[0]
        assert first_tas.id == "080-2011/2012-0120-000"
        assert first_tas.fiscal_year(2011) is True
        assert first_tas.fiscal_year(2012) is True
