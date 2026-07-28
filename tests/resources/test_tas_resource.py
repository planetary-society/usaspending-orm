"""Tests for TASResource."""

from usaspending.models.agency import Agency
from usaspending.queries.tas_agencies_query import TASAgenciesQuery
from usaspending.resources.tas_resource import TASResource


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
    """Test TASResource.agencies."""

    def test_agencies_returns_a_query_over_agency_models(self, mock_usa_client, load_fixture):
        """It hands back a query, like the two tree levels below it."""
        fixture = load_fixture("tas_agencies.json")
        mock_usa_client.set_response("/references/filter_tree/tas/", fixture)

        resource = TASResource(mock_usa_client)
        agencies = resource.agencies

        assert isinstance(agencies, TASAgenciesQuery)
        assert len(agencies) == 91
        assert all(isinstance(a, Agency) for a in agencies)
        assert isinstance(agencies.all(), list)

    def test_agencies_supports_the_list_like_operations(self, mock_usa_client, load_fixture):
        """Iteration, len, indexing and slicing all work without calling all()."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/", load_fixture("tas_agencies.json")
        )
        agencies = TASResource(mock_usa_client).agencies

        assert sum(1 for _ in agencies) == 91
        assert agencies[0].code
        assert len([a.code for a in agencies[:3]]) == 3

    def test_agencies_can_be_filtered(self, mock_usa_client, load_fixture):
        """The filters the query brings are the point of returning one."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/", load_fixture("tas_agencies.json")
        )
        agencies = TASResource(mock_usa_client).agencies

        assert agencies.code("080").first().code == "080"
        assert {a.code for a in agencies.codes("080", "012")} == {"080", "012"}

    def test_filtering_costs_no_further_requests(self, mock_usa_client, load_fixture):
        """The query holds the fetched level, so clones share it."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/", load_fixture("tas_agencies.json")
        )
        agencies = TASResource(mock_usa_client).agencies

        len(agencies)
        agencies.code("080").all()
        agencies.description("national").all()

        assert mock_usa_client.get_request_count() == 1

    def test_all_returns_an_independent_list_each_time(self, mock_usa_client, load_fixture):
        """No shared list to corrupt: a caller may sort or pop what it gets."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/", load_fixture("tas_agencies.json")
        )
        agencies = TASResource(mock_usa_client).agencies

        first = agencies.all()
        first.pop()

        assert len(agencies.all()) == 91

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
        """An empty level yields an empty query, not an error."""
        mock_usa_client.set_response("/references/filter_tree/tas/", {"results": []})

        agencies = TASResource(mock_usa_client).agencies

        assert agencies.all() == []
        assert len(agencies) == 0


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
        mock_usa_client.set_response("/references/filter_tree/tas/080/", federal_accounts_fixture)
        mock_usa_client.set_response("/references/filter_tree/tas/080/080-0120/", tas_codes_fixture)

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
