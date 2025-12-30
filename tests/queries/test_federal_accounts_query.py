"""Tests for FederalAccountsQuery."""

import pytest

from usaspending.queries.federal_accounts_query import FederalAccountsQuery
from usaspending.models.federal_account import FederalAccount


class TestFederalAccountsQueryBasics:
    """Test basic FederalAccountsQuery functionality."""

    def test_init(self, mock_usa_client):
        """Test FederalAccountsQuery initialization."""
        query = FederalAccountsQuery(mock_usa_client, "080")

        assert query._client is mock_usa_client
        assert query._toptier_code == "080"
        assert query._results is None

    def test_repr_before_fetch(self, mock_usa_client):
        """Test repr before results are fetched."""
        query = FederalAccountsQuery(mock_usa_client, "080")

        assert "080" in repr(query)
        assert "not fetched" in repr(query)


class TestFederalAccountsQueryFetch:
    """Test FederalAccountsQuery fetching."""

    def test_iteration_fetches_results(self, mock_usa_client, load_fixture):
        """Test iteration triggers API fetch."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")
        results = list(query)

        assert len(results) == 16
        assert all(isinstance(r, FederalAccount) for r in results)

    def test_len_fetches_results(self, mock_usa_client, load_fixture):
        """Test len() triggers API fetch."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")

        assert len(query) == 16

    def test_count_returns_len(self, mock_usa_client, load_fixture):
        """Test count() returns same as len()."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")

        assert query.count() == 16
        assert query.count() == len(query)

    def test_getitem_fetches_results(self, mock_usa_client, load_fixture):
        """Test indexing fetches results."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")
        first = query[0]

        assert isinstance(first, FederalAccount)
        assert first.id == "080-0109"

    def test_results_cached(self, mock_usa_client, load_fixture):
        """Test results are cached after first fetch."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")

        # First access
        _ = list(query)
        first_results = query._results

        # Second access
        _ = list(query)
        second_results = query._results

        # Same object (cached)
        assert first_results is second_results

    def test_repr_after_fetch(self, mock_usa_client, load_fixture):
        """Test repr after results are fetched shows count."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")
        _ = list(query)

        assert "16 results" in repr(query)


class TestFederalAccountsQueryMethods:
    """Test FederalAccountsQuery convenience methods."""

    def test_all_returns_list(self, mock_usa_client, load_fixture):
        """Test all() returns list."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")
        results = query.all()

        assert isinstance(results, list)
        assert len(results) == 16

    def test_first_returns_first_item(self, mock_usa_client, load_fixture):
        """Test first() returns first item."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")
        first = query.first()

        assert isinstance(first, FederalAccount)
        assert first.id == "080-0109"

    def test_first_returns_none_when_empty(self, mock_usa_client):
        """Test first() returns None for empty results."""
        mock_usa_client.set_response("/references/filter_tree/tas/080/", {"results": []})

        query = FederalAccountsQuery(mock_usa_client, "080")

        assert query.first() is None

    def test_bool_true_when_results(self, mock_usa_client, load_fixture):
        """Test bool() returns True when there are results."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")

        assert bool(query) is True

    def test_bool_false_when_empty(self, mock_usa_client):
        """Test bool() returns False when empty."""
        mock_usa_client.set_response("/references/filter_tree/tas/080/", {"results": []})

        query = FederalAccountsQuery(mock_usa_client, "080")

        assert bool(query) is False


class TestFederalAccountsQueryEmptyToptierCode:
    """Test FederalAccountsQuery with empty toptier_code."""

    def test_empty_toptier_code_returns_empty(self, mock_usa_client):
        """Test empty toptier_code returns empty results without API call."""
        query = FederalAccountsQuery(mock_usa_client, "")

        assert len(query) == 0
        assert query.first() is None
        assert query.all() == []


class TestFederalAccountsQueryIntegration:
    """Test FederalAccountsQuery integration with FederalAccount."""

    def test_accounts_have_toptier_code(self, mock_usa_client, load_fixture):
        """Test fetched accounts have toptier_code set."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")

        for account in query:
            assert account.toptier_code == "080"

    def test_accounts_can_access_tas_codes(self, mock_usa_client, load_fixture):
        """Test fetched accounts can access tas_codes property."""
        fixture = load_fixture("tas_federal_accounts.json")
        mock_usa_client.set_response("/references/filter_tree/tas/080/", fixture)

        query = FederalAccountsQuery(mock_usa_client, "080")
        first = query.first()

        # tas_codes property should return TASCodesQuery
        from usaspending.queries.tas_codes_query import TASCodesQuery
        assert isinstance(first.tas_codes, TASCodesQuery)


class TestFederalAccountsQueryFiscalYearFilter:
    """Test FederalAccountsQuery.fiscal_year() filter method."""

    def test_fiscal_year_filters_by_active_tas(self, mock_usa_client, load_fixture):
        """Test fiscal_year filters to accounts with active TAS codes."""
        federal_accounts_fixture = load_fixture("tas_federal_accounts.json")
        tas_codes_fixture = load_fixture("tas_codes.json")

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )

        # Set up TAS codes response for each federal account
        for account in federal_accounts_fixture["results"]:
            account_id = account["id"]
            mock_usa_client.set_response(
                f"/references/filter_tree/tas/080/{account_id}/", tas_codes_fixture
            )

        query = FederalAccountsQuery(mock_usa_client, "080")

        # Filter by 2024 - should include accounts with 2023/2024, 2024/2025, or X TAS
        active_2024 = query.fiscal_year(2024)

        assert isinstance(active_2024, list)
        # All 16 accounts have the same TAS codes fixture, which includes 2024 TAS
        assert len(active_2024) == 16

    def test_fiscal_year_excludes_inactive_accounts(self, mock_usa_client, load_fixture):
        """Test fiscal_year excludes accounts without matching TAS codes."""
        federal_accounts_fixture = load_fixture("tas_federal_accounts.json")

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )

        # Set up TAS codes with only old years (no 2010 coverage except X)
        old_tas_fixture = {
            "results": [
                {
                    "id": "080-2015/2016-0120-000",
                    "ancestors": ["080", "080-0120"],
                    "description": "Test TAS",
                    "count": 0,
                    "children": None,
                }
            ]
        }

        # Set up same response for all accounts
        for account in federal_accounts_fixture["results"]:
            account_id = account["id"]
            mock_usa_client.set_response(
                f"/references/filter_tree/tas/080/{account_id}/", old_tas_fixture
            )

        query = FederalAccountsQuery(mock_usa_client, "080")

        # Filter by 2010 - TAS 2015/2016 doesn't cover 2010
        active_2010 = query.fiscal_year(2010)

        assert active_2010 == []

    def test_fiscal_year_excludes_no_year_by_default(self, mock_usa_client, load_fixture):
        """Test fiscal_year excludes no-year (X) TAS codes by default."""
        federal_accounts_fixture = load_fixture("tas_federal_accounts.json")

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )

        # Set up TAS codes with only no-year (X) TAS
        no_year_tas_fixture = {
            "results": [
                {
                    "id": "080-X-0120-000",
                    "ancestors": ["080", "080-0120"],
                    "description": "No-year TAS",
                    "count": 0,
                    "children": None,
                }
            ]
        }

        # Set up same response for all accounts
        for account in federal_accounts_fixture["results"]:
            account_id = account["id"]
            mock_usa_client.set_response(
                f"/references/filter_tree/tas/080/{account_id}/", no_year_tas_fixture
            )

        query = FederalAccountsQuery(mock_usa_client, "080")

        # Filter by any year - no-year accounts excluded by default
        active_explicit = query.fiscal_year(2099)

        # No accounts should be included since all have only no-year TAS
        assert len(active_explicit) == 0

    def test_fiscal_year_includes_no_year_when_flag_true(
        self, mock_usa_client, load_fixture
    ):
        """Test fiscal_year includes no-year (X) TAS codes when include_noyear_accounts=True."""
        federal_accounts_fixture = load_fixture("tas_federal_accounts.json")

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )

        # Set up TAS codes with only no-year (X) TAS
        no_year_tas_fixture = {
            "results": [
                {
                    "id": "080-X-0120-000",
                    "ancestors": ["080", "080-0120"],
                    "description": "No-year TAS",
                    "count": 0,
                    "children": None,
                }
            ]
        }

        # Set up same response for all accounts
        for account in federal_accounts_fixture["results"]:
            account_id = account["id"]
            mock_usa_client.set_response(
                f"/references/filter_tree/tas/080/{account_id}/", no_year_tas_fixture
            )

        query = FederalAccountsQuery(mock_usa_client, "080")

        # Filter by any year with include_noyear_accounts=True
        active_any_year = query.fiscal_year(2099, include_noyear_accounts=True)

        # All 16 accounts have no-year TAS, so all should be included
        assert len(active_any_year) == 16

    def test_fiscal_year_returns_empty_for_no_accounts(self, mock_usa_client):
        """Test fiscal_year returns empty list when no accounts exist."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", {"results": []}
        )

        query = FederalAccountsQuery(mock_usa_client, "080")

        active_2024 = query.fiscal_year(2024)

        assert active_2024 == []

    def test_fiscal_year_with_mixed_tas_codes(self, mock_usa_client, load_fixture):
        """Test fiscal_year with accounts having different TAS code ranges."""
        # Create a fixture with 2 accounts
        federal_accounts_fixture = {
            "results": [
                {
                    "id": "080-0120",
                    "ancestors": ["080"],
                    "description": "Account with 2024 TAS",
                    "count": 1,
                    "children": None,
                },
                {
                    "id": "080-0121",
                    "ancestors": ["080"],
                    "description": "Account with old TAS only",
                    "count": 1,
                    "children": None,
                },
            ]
        }

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )

        # First account has 2024 TAS
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/",
            {
                "results": [
                    {
                        "id": "080-2024/2025-0120-000",
                        "ancestors": ["080", "080-0120"],
                        "description": "2024 TAS",
                        "count": 0,
                        "children": None,
                    }
                ]
            },
        )

        # Second account has only old TAS
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0121/",
            {
                "results": [
                    {
                        "id": "080-2010/2011-0121-000",
                        "ancestors": ["080", "080-0121"],
                        "description": "Old TAS",
                        "count": 0,
                        "children": None,
                    }
                ]
            },
        )

        query = FederalAccountsQuery(mock_usa_client, "080")

        # Filter by 2024 - should only include first account
        active_2024 = query.fiscal_year(2024)

        assert len(active_2024) == 1
        assert active_2024[0].id == "080-0120"

    def test_fiscal_year_include_noyear_with_mixed_tas(
        self, mock_usa_client
    ):
        """Test include_noyear_accounts with accounts having both no-year and explicit TAS."""
        # Create a fixture with 2 accounts
        federal_accounts_fixture = {
            "results": [
                {
                    "id": "080-0120",
                    "ancestors": ["080"],
                    "description": "Account with both no-year and 2024 TAS",
                    "count": 2,
                    "children": None,
                },
                {
                    "id": "080-0121",
                    "ancestors": ["080"],
                    "description": "Account with only no-year TAS",
                    "count": 1,
                    "children": None,
                },
            ]
        }

        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/", federal_accounts_fixture
        )

        # First account has both no-year AND explicit 2024 TAS
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/",
            {
                "results": [
                    {
                        "id": "080-X-0120-000",
                        "ancestors": ["080", "080-0120"],
                        "description": "No-year TAS",
                        "count": 0,
                        "children": None,
                    },
                    {
                        "id": "080-2024/2025-0120-000",
                        "ancestors": ["080", "080-0120"],
                        "description": "2024 TAS",
                        "count": 0,
                        "children": None,
                    },
                ]
            },
        )

        # Second account has only no-year TAS
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0121/",
            {
                "results": [
                    {
                        "id": "080-X-0121-000",
                        "ancestors": ["080", "080-0121"],
                        "description": "No-year TAS",
                        "count": 0,
                        "children": None,
                    }
                ]
            },
        )

        query = FederalAccountsQuery(mock_usa_client, "080")

        # Default: only first account matches (has explicit 2024 TAS)
        active_explicit = query.fiscal_year(2024)
        assert len(active_explicit) == 1
        assert active_explicit[0].id == "080-0120"

        # With include_noyear_accounts=True, both accounts match
        active_all = query.fiscal_year(2024, include_noyear_accounts=True)
        assert len(active_all) == 2
