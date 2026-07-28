"""Tests for FederalAccount model."""

import gc
import weakref

from tests.mocks import MockUSASpendingClient
from usaspending.models.federal_account import FederalAccount
from usaspending.queries.tas_codes_query import TASCodesQuery


class TestFederalAccountBasicProperties:
    """Test basic FederalAccount properties."""

    def test_basic_properties(self, mock_usa_client):
        """Test basic property access."""
        data = {
            "id": "080-0120",
            "ancestors": ["080"],
            "description": "Science, National Aeronautics and Space Administration",
            "count": 16,
            "children": None,
        }

        account = FederalAccount(data, mock_usa_client)

        assert account.id == "080-0120"
        assert account.code == "080-0120"
        assert account.federal_account_code == "080-0120"
        assert account.description == "Science, National Aeronautics and Space Administration"
        assert account.name == "Science, National Aeronautics and Space Administration"
        assert account.title == "Science, National Aeronautics and Space Administration"
        assert account.count == 16
        assert account.ancestors == ["080"]

    def test_toptier_code_from_ancestors(self, mock_usa_client):
        """Test toptier_code extracted from ancestors."""
        data = {
            "id": "080-0120",
            "ancestors": ["080"],
        }

        account = FederalAccount(data, mock_usa_client)

        assert account.toptier_code == "080"

    def test_toptier_code_from_constructor(self, mock_usa_client):
        """Test toptier_code from constructor takes precedence."""
        data = {
            "id": "080-0120",
            "ancestors": ["999"],  # Different from constructor
        }

        account = FederalAccount(data, mock_usa_client, toptier_code="080")

        assert account.toptier_code == "080"

    def test_empty_ancestors(self, mock_usa_client):
        """Test handling of empty ancestors."""
        data = {
            "id": "080-0120",
            "ancestors": [],
        }

        account = FederalAccount(data, mock_usa_client)

        assert account.ancestors == []
        assert account.toptier_code is None


class TestFederalAccountTASCodesProperty:
    """Test FederalAccount.tas_codes property."""

    def test_tas_codes_returns_query(self, mock_usa_client):
        """Test tas_codes returns TASCodesQuery instance."""
        data = {
            "id": "080-0120",
            "ancestors": ["080"],
        }

        account = FederalAccount(data, mock_usa_client, toptier_code="080")
        tas_codes = account.tas_codes

        assert isinstance(tas_codes, TASCodesQuery)

    def test_tas_codes_query_has_correct_params(self, mock_usa_client):
        """Test tas_codes query is initialized with correct params."""
        data = {
            "id": "080-0120",
            "ancestors": ["080"],
        }

        account = FederalAccount(data, mock_usa_client, toptier_code="080")
        tas_codes = account.tas_codes

        assert tas_codes._toptier_code == "080"
        assert tas_codes._federal_account == "080-0120"

    def test_tas_codes_without_toptier_code(self, mock_usa_client):
        """Test tas_codes with missing toptier_code returns empty query."""
        data = {
            "id": "080-0120",
            "ancestors": [],
        }

        account = FederalAccount(data, mock_usa_client)
        tas_codes = account.tas_codes

        # Should return empty query
        assert tas_codes._toptier_code == ""


class TestFederalAccountRepr:
    """Test string representation."""

    def test_repr_basic(self, mock_usa_client):
        """Test repr includes code and title."""
        data = {
            "id": "080-0120",
            "description": "Science, NASA",
        }
        account = FederalAccount(data, mock_usa_client)

        assert "080-0120" in repr(account)
        assert "Science, NASA" in repr(account)
        assert "FederalAccount" in repr(account)

    def test_repr_long_title_truncated(self, mock_usa_client):
        """Test repr truncates long titles."""
        data = {
            "id": "080-0120",
            "description": "A" * 100,  # Very long title
        }
        account = FederalAccount(data, mock_usa_client)

        assert "..." in repr(account)


class TestFederalAccountFromFixture:
    """Test FederalAccount with real fixture data."""

    def test_from_fixture_data(self, mock_usa_client, load_fixture):
        """Test creating FederalAccount from fixture data."""
        fixture = load_fixture("tas_federal_accounts.json")
        first_result = fixture["results"][0]

        account = FederalAccount(first_result, mock_usa_client, toptier_code="080")

        assert account.id == "080-0109"
        assert account.toptier_code == "080"
        assert account.count == 24
        assert "Inspector General" in account.description

    def test_multiple_accounts_from_fixture(self, mock_usa_client, load_fixture):
        """Test creating multiple FederalAccount instances from fixture."""
        fixture = load_fixture("tas_federal_accounts.json")

        accounts = [
            FederalAccount(data, mock_usa_client, toptier_code="080") for data in fixture["results"]
        ]

        assert len(accounts) == 16
        assert all(a.toptier_code == "080" for a in accounts)
        assert all(a.id.startswith("080-") for a in accounts)


class TestFederalAccountCount:
    """count must not pay for a fallback it does not use."""

    def test_count_from_data_makes_no_request(self, mock_usa_client):
        """A count present in the filter tree is returned without any API call.

        The fallback used to be passed as a default argument, which Python
        evaluates eagerly, so every access fired a TAS-code count request whose
        result was then discarded.
        """
        account = FederalAccount(
            {"id": "080-0120", "ancestors": ["080"], "count": 7},
            mock_usa_client,
            toptier_code="080",
        )

        before = mock_usa_client.get_request_count()
        assert account.count == 7
        assert mock_usa_client.get_request_count() == before

    def test_count_falls_back_to_tas_codes_when_absent(self, mock_usa_client):
        """With no count key, the TAS codes are counted instead."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/",
            {"results": [{"id": "080-2011/2012-0120-000"}, {"id": "080-2012/2013-0120-000"}]},
        )
        account = FederalAccount(
            {"id": "080-0120", "ancestors": ["080"]},
            mock_usa_client,
            toptier_code="080",
        )

        assert account.count == 2


class TestTASCodesFetchedOnce:
    """The TAS level is fetched once per account, not once per read.

    tas_codes used to build a fresh query on every access, discarding the result
    cache the query had just filled, so len() then a filter then first() cost
    three requests for one level.
    """

    ENDPOINT = "/references/filter_tree/tas/080/080-0120/"

    def _account(self, mock_usa_client, load_fixture):
        mock_usa_client.set_response(self.ENDPOINT, load_fixture("tas_codes.json"))
        return FederalAccount(
            {"id": "080-0120", "ancestors": ["080"]}, mock_usa_client, toptier_code="080"
        )

    def test_repeated_reads_cost_one_request(self, mock_usa_client, load_fixture):
        account = self._account(mock_usa_client, load_fixture)
        before = mock_usa_client.get_request_count()

        len(account.tas_codes)
        account.tas_codes.all()
        account.tas_codes.first()
        account.tas_codes.availability_type_code("X").all()

        assert mock_usa_client.get_request_count() - before == 1

    def test_each_read_returns_an_independent_query(self, mock_usa_client, load_fixture):
        """So one caller filtering or exhausting cannot affect the next."""
        account = self._account(mock_usa_client, load_fixture)

        assert account.tas_codes is not account.tas_codes

        expected = len(account.tas_codes)
        account.tas_codes.all().pop()

        assert len(account.tas_codes) == expected

    def test_an_unscoped_account_yields_nothing_without_a_request(self, mock_usa_client):
        """An account that does not know its codes must not call the API."""
        account = FederalAccount({"id": "080-0120"}, mock_usa_client, toptier_code=None)
        before = mock_usa_client.get_request_count()

        assert account.tas_codes.all() == []
        assert mock_usa_client.get_request_count() == before

    def test_caching_the_models_does_not_pin_the_client(self, load_fixture):
        """The model holds the client weakly; its cache must not undo that.

        Builds its own client rather than taking the fixture, because pytest keeps
        a fixture value alive for the duration of the test, which would mask the
        very reference this checks for.
        """
        client = MockUSASpendingClient()
        client.set_response(self.ENDPOINT, load_fixture("tas_codes.json"))
        account = FederalAccount(
            {"id": "080-0120", "ancestors": ["080"]}, client, toptier_code="080"
        )
        account.tas_codes.all()
        reference = weakref.ref(client)

        del client
        gc.collect()

        assert reference() is None, "a cached query would have kept the client alive"

    def test_reading_the_property_alone_makes_no_request(self, mock_usa_client, load_fixture):
        """Caching must not cost laziness; see the query's _seed docstring."""
        account = self._account(mock_usa_client, load_fixture)
        before = mock_usa_client.get_request_count()

        query = account.tas_codes.fiscal_year(2024)

        assert mock_usa_client.get_request_count() == before
        assert len(query.all()) > 0, "still fetches once someone reads it"

    def test_reattach_rebinds_the_cached_codes(self, mock_usa_client, load_fixture):
        """A cache of models must not outlive the client those models point at."""
        account = self._account(mock_usa_client, load_fixture)
        account.tas_codes.all()

        replacement = MockUSASpendingClient()
        account.reattach(replacement, recursive=True)

        codes = account.tas_codes.all()
        # The replacement has no responses, so a refetch would return nothing.
        assert replacement.get_request_count() == 0
        assert len(codes) == 16
        assert all(code._client is replacement for code in codes)
