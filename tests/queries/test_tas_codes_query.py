"""Tests for TASCodesQuery."""

import pytest

from usaspending.queries.tas_codes_query import TASCodesQuery
from usaspending.models.treasury_account_symbol import TreasuryAccountSymbol


class TestTASCodesQueryBasics:
    """Test basic TASCodesQuery functionality."""

    def test_init(self, mock_usa_client):
        """Test TASCodesQuery initialization."""
        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        assert query._client is mock_usa_client
        assert query._toptier_code == "080"
        assert query._federal_account == "080-0120"
        assert query._results is None

    def test_repr_before_fetch(self, mock_usa_client):
        """Test repr before results are fetched."""
        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        assert "080" in repr(query)
        assert "080-0120" in repr(query)
        assert "not fetched" in repr(query)


class TestTASCodesQueryFetch:
    """Test TASCodesQuery fetching."""

    def test_iteration_fetches_results(self, mock_usa_client, load_fixture):
        """Test iteration triggers API fetch."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")
        results = list(query)

        assert len(results) == 16
        assert all(isinstance(r, TreasuryAccountSymbol) for r in results)

    def test_len_fetches_results(self, mock_usa_client, load_fixture):
        """Test len() triggers API fetch."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        assert len(query) == 16

    def test_count_returns_len(self, mock_usa_client, load_fixture):
        """Test count() returns same as len()."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        assert query.count() == 16
        assert query.count() == len(query)

    def test_getitem_fetches_results(self, mock_usa_client, load_fixture):
        """Test indexing fetches results."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")
        first = query[0]

        assert isinstance(first, TreasuryAccountSymbol)
        assert first.id == "080-2011/2012-0120-000"

    def test_results_cached(self, mock_usa_client, load_fixture):
        """Test results are cached after first fetch."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

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
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")
        _ = list(query)

        assert "16 results" in repr(query)


class TestTASCodesQueryMethods:
    """Test TASCodesQuery convenience methods."""

    def test_all_returns_list(self, mock_usa_client, load_fixture):
        """Test all() returns list."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")
        results = query.all()

        assert isinstance(results, list)
        assert len(results) == 16

    def test_first_returns_first_item(self, mock_usa_client, load_fixture):
        """Test first() returns first item."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")
        first = query.first()

        assert isinstance(first, TreasuryAccountSymbol)
        assert first.id == "080-2011/2012-0120-000"

    def test_first_returns_none_when_empty(self, mock_usa_client):
        """Test first() returns None for empty results."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", {"results": []}
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        assert query.first() is None

    def test_bool_true_when_results(self, mock_usa_client, load_fixture):
        """Test bool() returns True when there are results."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        assert bool(query) is True

    def test_bool_false_when_empty(self, mock_usa_client):
        """Test bool() returns False when empty."""
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", {"results": []}
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        assert bool(query) is False


class TestTASCodesQueryEmptyParams:
    """Test TASCodesQuery with empty parameters."""

    def test_empty_toptier_code_returns_empty(self, mock_usa_client):
        """Test empty toptier_code returns empty results without API call."""
        query = TASCodesQuery(mock_usa_client, "", "080-0120")

        assert len(query) == 0
        assert query.first() is None
        assert query.all() == []

    def test_empty_federal_account_returns_empty(self, mock_usa_client):
        """Test empty federal_account returns empty results without API call."""
        query = TASCodesQuery(mock_usa_client, "080", "")

        assert len(query) == 0
        assert query.first() is None
        assert query.all() == []


class TestTASCodesQueryIntegration:
    """Test TASCodesQuery integration with TreasuryAccountSymbol."""

    def test_tas_have_parent_codes(self, mock_usa_client, load_fixture):
        """Test fetched TAS have parent codes set."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        for tas in query:
            assert tas.toptier_code == "080"
            assert tas.federal_account_code == "080-0120"

    def test_tas_can_check_fiscal_year(self, mock_usa_client, load_fixture):
        """Test fetched TAS can check fiscal year."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")
        first = query.first()

        # 080-2011/2012-0120-000 should cover 2011 and 2012
        assert first.fiscal_year(2011) is True
        assert first.fiscal_year(2012) is True
        assert first.fiscal_year(2013) is False

    def test_no_year_tas_in_results(self, mock_usa_client, load_fixture):
        """Test no-year TAS can be found in results."""
        fixture = load_fixture("tas_codes.json")
        mock_usa_client.set_response(
            "/references/filter_tree/tas/080/080-0120/", fixture
        )

        query = TASCodesQuery(mock_usa_client, "080", "080-0120")

        # Find the no-year TAS
        no_year_tas = next((t for t in query if t.availability_type_code == "X"), None)

        assert no_year_tas is not None
        assert no_year_tas.id == "080-X-0120-000"
        assert no_year_tas.fiscal_year(2024) is True
