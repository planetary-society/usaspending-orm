"""Tests for AwardAccountsQuery query builder."""

import pytest

from usaspending.exceptions import ValidationError
from usaspending.models.award_account import AwardAccount
from usaspending.queries.award_accounts_query import AwardAccountsQuery


class TestAwardAccountsQueryInitialization:
    """Tests for AwardAccountsQuery initialization."""

    def test_initialization(self, mock_usa_client):
        """Test basic initialization."""
        query = AwardAccountsQuery(mock_usa_client)

        assert query._client == mock_usa_client
        assert query._award_id is None
        assert query._sort_field == "federal_account"
        assert query._sort_order == "desc"

    def test_endpoint(self, mock_usa_client):
        """Test endpoint property."""
        query = AwardAccountsQuery(mock_usa_client)

        assert query._endpoint == "/awards/accounts/"


class TestAwardAccountsQueryAwardIdFilter:
    """Tests for the award_id filter method."""

    def test_award_id_sets_id(self, mock_usa_client):
        """Test award_id method sets the award ID."""
        query = AwardAccountsQuery(mock_usa_client)
        filtered = query.award_id("CONT_AWD_123")

        assert filtered._award_id == "CONT_AWD_123"

    def test_award_id_returns_clone(self, mock_usa_client):
        """Test award_id method returns a new instance."""
        query = AwardAccountsQuery(mock_usa_client)
        filtered = query.award_id("CONT_AWD_123")

        assert filtered is not query
        assert query._award_id is None
        assert filtered._award_id == "CONT_AWD_123"

    def test_award_id_clears_cached_count(self, mock_usa_client):
        """Test award_id clears cached count."""
        query = AwardAccountsQuery(mock_usa_client)
        query._cached_count = 5  # Simulate cached count

        filtered = query.award_id("CONT_AWD_123")

        assert filtered._cached_count is None

    def test_award_id_required_validation(self, mock_usa_client):
        """Test validation error when award_id is empty."""
        query = AwardAccountsQuery(mock_usa_client)

        with pytest.raises(ValidationError):
            query.award_id("")

    def test_award_id_whitespace_validation(self, mock_usa_client):
        """Test validation error when award_id is whitespace."""
        query = AwardAccountsQuery(mock_usa_client)

        with pytest.raises(ValidationError):
            query.award_id("   ")


class TestAwardAccountsQueryOrderBy:
    """Tests for the order_by method."""

    def test_order_by_amount(self, mock_usa_client):
        """Test order_by with amount field."""
        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        sorted_query = query.order_by("amount", "desc")

        assert sorted_query._sort_field == "total_transaction_obligated_amount"
        assert sorted_query._sort_order == "desc"

    def test_order_by_federal_account(self, mock_usa_client):
        """Test order_by with federal_account field."""
        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        sorted_query = query.order_by("federal_account", "asc")

        assert sorted_query._sort_field == "federal_account"
        assert sorted_query._sort_order == "asc"

    def test_order_by_account_title(self, mock_usa_client):
        """Test order_by with account_title field."""
        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        sorted_query = query.order_by("account_title", "asc")

        assert sorted_query._sort_field == "account_title"
        assert sorted_query._sort_order == "asc"

    def test_order_by_user_friendly_names(self, mock_usa_client):
        """Test order_by with user-friendly field names."""
        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")

        # Test various aliases
        assert query.order_by("title")._sort_field == "account_title"
        assert query.order_by("code")._sort_field == "federal_account"
        assert query.order_by("account")._sort_field == "federal_account"
        assert (
            query.order_by("obligated_amount")._sort_field == "total_transaction_obligated_amount"
        )

    def test_order_by_returns_clone(self, mock_usa_client):
        """Test order_by returns a new instance."""
        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        sorted_query = query.order_by("amount", "asc")

        assert sorted_query is not query
        assert query._sort_field == "federal_account"
        assert sorted_query._sort_field == "total_transaction_obligated_amount"

    def test_order_by_invalid_direction(self, mock_usa_client):
        """Test order_by with invalid direction raises error."""
        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="Invalid sort direction"):
            query.order_by("amount", "invalid")

    def test_order_by_invalid_field(self, mock_usa_client):
        """Test order_by with invalid field raises error."""
        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="Invalid sort field"):
            query.order_by("invalid_field")


class TestAwardAccountsQueryPayload:
    """Tests for payload building."""

    def test_build_payload_with_award_id(self, mock_usa_client):
        """Test payload includes award_id."""
        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        payload = query._build_payload(1)

        assert payload["award_id"] == "CONT_AWD_123"
        assert payload["page"] == 1
        assert "limit" in payload
        assert payload["sort"] == "federal_account"
        assert payload["order"] == "desc"

    def test_build_payload_without_award_id_raises_error(self, mock_usa_client):
        """Test build_payload raises error without award_id."""
        query = AwardAccountsQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="award_id is required"):
            query._build_payload(1)

    def test_build_payload_respects_sort_settings(self, mock_usa_client):
        """Test payload includes sort settings."""
        query = (
            AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123").order_by("amount", "asc")
        )
        payload = query._build_payload(1)

        assert payload["sort"] == "total_transaction_obligated_amount"
        assert payload["order"] == "asc"


class TestAwardAccountsQueryClone:
    """Tests for the _clone method."""

    def test_clone_preserves_attributes(self, mock_usa_client):
        """Test _clone preserves all attributes."""
        query = (
            AwardAccountsQuery(mock_usa_client)
            .award_id("CONT_AWD_123")
            .order_by("amount", "asc")
            .limit(50)
        )

        clone = query._clone()

        assert clone._award_id == "CONT_AWD_123"
        assert clone._sort_field == "total_transaction_obligated_amount"
        assert clone._sort_order == "asc"
        assert clone._total_limit == 50
        assert clone is not query


class TestAwardAccountsQueryTransformResult:
    """Tests for result transformation."""

    def test_transform_result_creates_award_account(self, mock_usa_client, load_fixture):
        """Test _transform_result creates AwardAccount objects."""
        fixture = load_fixture("awards/accounts.json")
        account_data = fixture["results"][0]

        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        result = query._transform_result(account_data)

        assert isinstance(result, AwardAccount)
        assert result.id == "080-0131"


class TestAwardAccountsQueryIteration:
    """Tests for query iteration."""

    def test_iteration_with_fixture(self, mock_usa_client, load_fixture):
        """Test iteration returns AwardAccount objects."""
        fixture = load_fixture("awards/accounts.json")
        mock_usa_client.set_response("/awards/accounts/", fixture)

        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        results = list(query)

        assert len(results) == 2
        assert all(isinstance(r, AwardAccount) for r in results)

    def test_iteration_preserves_data(self, mock_usa_client, load_fixture):
        """Test iteration preserves fixture data."""
        fixture = load_fixture("awards/accounts.json")
        mock_usa_client.set_response("/awards/accounts/", fixture)

        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        results = list(query)

        assert results[0].id == "080-0131"
        assert results[1].id == "080-0124"


class TestAwardAccountsQueryCount:
    """Tests for the count method."""

    def test_count_uses_page_metadata(self, mock_usa_client, load_fixture):
        """Test count uses page_metadata.count from API response."""
        fixture = load_fixture("awards/accounts.json")
        mock_usa_client.set_response("/awards/accounts/", fixture)

        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        count = query.count()

        assert count == 2  # From page_metadata.count in fixture

    def test_count_caches_result(self, mock_usa_client, load_fixture):
        """Test count caches the result."""
        fixture = load_fixture("awards/accounts.json")
        mock_usa_client.set_response("/awards/accounts/", fixture)

        query = AwardAccountsQuery(mock_usa_client).award_id("CONT_AWD_123")
        count1 = query.count()
        count2 = query.count()

        assert count1 == count2
        assert query._cached_count == 2

    def test_count_requires_award_id(self, mock_usa_client):
        """Test count raises error without award_id."""
        query = AwardAccountsQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="award_id is required"):
            query.count()


class TestAwardAccountsQueryChaining:
    """Tests for method chaining."""

    def test_chaining_multiple_methods(self, mock_usa_client, load_fixture):
        """Test chaining multiple methods."""
        fixture = load_fixture("awards/accounts.json")
        mock_usa_client.set_response("/awards/accounts/", fixture)

        results = (
            AwardAccountsQuery(mock_usa_client)
            .award_id("CONT_AWD_123")
            .order_by("amount", "desc")
            .limit(10)
            .all()
        )

        assert len(results) == 2
        assert all(isinstance(r, AwardAccount) for r in results)
