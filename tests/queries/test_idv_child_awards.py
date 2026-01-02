"""Tests for IDVChildAwardsSearch query builder."""

from __future__ import annotations

import pytest

from usaspending.exceptions import ValidationError
from usaspending.models.award import Award
from usaspending.queries.idv_child_awards import IDVChildAwardsSearch


class TestIDVChildAwardsSearchInitialization:
    """Test IDVChildAwardsSearch initialization."""

    def test_initialization_with_valid_award_id(self, mock_usa_client):
        """Test basic initialization with valid award_id."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        assert search._client == mock_usa_client
        assert search._award_id == "CONT_IDV_123"
        assert search._sort_field == "obligated_amount"
        assert search._sort_order == "desc"
        assert search._idv_award_type == "child_awards"
        assert search._endpoint == "/idvs/awards/"

    def test_initialization_empty_award_id_raises_error(self, mock_usa_client):
        """Test that empty award_id raises ValidationError."""
        with pytest.raises(ValidationError, match="award_id cannot be empty"):
            IDVChildAwardsSearch(mock_usa_client, "")

    def test_initialization_whitespace_award_id_raises_error(self, mock_usa_client):
        """Test that whitespace-only award_id raises ValidationError."""
        with pytest.raises(ValidationError, match="award_id cannot be empty"):
            IDVChildAwardsSearch(mock_usa_client, "   ")


class TestBuildPayload:
    """Test payload construction."""

    def test_build_payload_default(self, mock_usa_client):
        """Test default payload construction."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        payload = search._build_payload(1)

        assert payload == {
            "award_id": "CONT_IDV_123",
            "limit": 100,
            "page": 1,
            "sort": "obligated_amount",
            "order": "desc",
            "type": "child_awards",
        }

    def test_build_payload_with_limit(self, mock_usa_client):
        """Test payload with custom limit."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123").limit(25)

        payload = search._build_payload(1)

        assert payload["limit"] == 25

    def test_build_payload_with_page(self, mock_usa_client):
        """Test payload with different page numbers."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        payload_page_1 = search._build_payload(1)
        payload_page_2 = search._build_payload(2)

        assert payload_page_1["page"] == 1
        assert payload_page_2["page"] == 2

    def test_build_payload_with_sort(self, mock_usa_client):
        """Test payload with custom sort settings."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123").order_by("piid", "asc")

        payload = search._build_payload(1)

        assert payload["sort"] == "piid"
        assert payload["order"] == "asc"

    def test_build_payload_with_type_filter(self, mock_usa_client):
        """Test payload with type filter."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123").award_type("child_idvs")

        payload = search._build_payload(1)

        assert payload["type"] == "child_idvs"


class TestOrderBy:
    """Test order_by functionality."""

    def test_order_by_valid_fields(self, mock_usa_client):
        """Test order_by with valid fields."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        # Test user-friendly field names
        result = search.order_by("piid", "asc")
        assert result._sort_field == "piid"
        assert result._sort_order == "asc"

        result = search.order_by("obligated_amount", "desc")
        assert result._sort_field == "obligated_amount"
        assert result._sort_order == "desc"

        result = search.order_by("start_date")
        assert result._sort_field == "period_of_performance_start_date"
        assert result._sort_order == "desc"  # Default

    def test_order_by_all_mapped_fields(self, mock_usa_client):
        """Test all field mappings in SORT_FIELD_MAP."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        field_mappings = {
            "award_type": "award_type",
            "description": "description",
            "funding_agency": "funding_agency",
            "awarding_agency": "awarding_agency",
            "obligated_amount": "obligated_amount",
            "obligation": "obligated_amount",
            "start_date": "period_of_performance_start_date",
            "end_date": "period_of_performance_current_end_date",
            "piid": "piid",
            "last_date_to_order": "last_date_to_order",
        }

        for user_field, api_field in field_mappings.items():
            result = search.order_by(user_field)
            assert result._sort_field == api_field

    def test_order_by_invalid_direction(self, mock_usa_client):
        """Test order_by with invalid direction."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        with pytest.raises(ValidationError, match="Invalid sort direction"):
            search.order_by("piid", "invalid")

    def test_order_by_invalid_field(self, mock_usa_client):
        """Test order_by with invalid field."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        with pytest.raises(ValidationError, match="Invalid sort field"):
            search.order_by("invalid_field")

    def test_order_by_returns_clone(self, mock_usa_client):
        """Test that order_by returns a new instance."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
        result = search.order_by("piid")

        assert result is not search
        assert result._sort_field == "piid"
        assert search._sort_field == "obligated_amount"  # Original unchanged


class TestAwardTypeFilter:
    """Test award_type filter functionality."""

    def test_award_type_child_idvs(self, mock_usa_client):
        """Test filtering to child_idvs type."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
        result = search.award_type("child_idvs")

        assert result._idv_award_type == "child_idvs"

    def test_award_type_child_awards(self, mock_usa_client):
        """Test filtering to child_awards type."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
        result = search.award_type("child_awards")

        assert result._idv_award_type == "child_awards"

    def test_award_type_grandchild_awards(self, mock_usa_client):
        """Test filtering to grandchild_awards type."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
        result = search.award_type("grandchild_awards")

        assert result._idv_award_type == "grandchild_awards"

    def test_award_type_case_insensitive(self, mock_usa_client):
        """Test that award_type is case insensitive."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        result = search.award_type("CHILD_IDVS")
        assert result._idv_award_type == "child_idvs"

        result = search.award_type("GRANDCHILD_AWARDS")
        assert result._idv_award_type == "grandchild_awards"

    def test_award_type_invalid(self, mock_usa_client):
        """Test that invalid award type raises error."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        with pytest.raises(ValidationError, match="Invalid type filter"):
            search.award_type("contract")

    def test_award_type_returns_clone(self, mock_usa_client):
        """Test that award_type returns a new instance."""
        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
        result = search.award_type("child_idvs")

        assert result is not search
        assert result._idv_award_type == "child_idvs"
        assert search._idv_award_type == "child_awards"  # Original unchanged


class TestClone:
    """Test clone functionality."""

    def test_clone_preserves_all_attributes(self, mock_usa_client):
        """Test that _clone preserves all attributes."""
        search = (
            IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
            .order_by("piid", "asc")
            .award_type("child_idvs")
            .limit(50)
        )

        clone = search._clone()

        assert clone._award_id == "CONT_IDV_123"
        assert clone._sort_field == "piid"
        assert clone._sort_order == "asc"
        assert clone._idv_award_type == "child_idvs"
        assert clone._total_limit == 50
        assert clone is not search


class TestTransformResult:
    """Test result transformation."""

    def test_transform_result_creates_award(self, mock_usa_client, load_fixture):
        """Test that _transform_result creates Award model from fixture data."""
        fixture_data = load_fixture("awards/idv_awards.json")
        first_result = fixture_data["results"][0]

        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
        result = search._transform_result(first_result)

        # Should create an Award (or subclass) instance
        assert isinstance(result, Award)

        # Verify data from fixture is accessible
        assert result.generated_unique_award_id == first_result["generated_unique_award_id"]


class TestIteration:
    """Test iteration and result retrieval."""

    def test_iteration_with_fixture_data(self, mock_usa_client, load_fixture):
        """Test iteration through child awards results using for loop."""
        fixture_data = load_fixture("awards/idv_awards.json")
        expected_results = fixture_data["results"]

        # Use paginated response to properly handle iteration
        mock_usa_client.set_paginated_response("/idvs/awards/", expected_results, page_size=100)

        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")

        # Use for loop to avoid __len__ consuming responses
        results = []
        for item in search:
            results.append(item)

        # Compare count against fixture
        assert len(results) == len(expected_results)
        assert all(isinstance(r, Award) for r in results)

        # Verify each result matches corresponding fixture data
        for result, expected in zip(results, expected_results):
            assert result.generated_unique_award_id == expected["generated_unique_award_id"]
            assert result._data.get("piid") == expected["piid"]
            assert result._data.get("obligated_amount") == expected["obligated_amount"]

    def test_first_returns_single_result(self, mock_usa_client, load_fixture):
        """Test that first() returns only the first result."""
        fixture_data = load_fixture("awards/idv_awards.json")
        expected_first = fixture_data["results"][0]

        # Use paginated response
        mock_usa_client.set_paginated_response(
            "/idvs/awards/", fixture_data["results"], page_size=100
        )

        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
        first = search.first()

        assert isinstance(first, Award)
        # Verify matches fixture first item
        assert first.generated_unique_award_id == expected_first["generated_unique_award_id"]
        assert first._data.get("piid") == expected_first["piid"]
        assert first._data.get("description") == expected_first["description"]
        assert first._data.get("awarding_agency") == expected_first["awarding_agency"]

    def test_all_returns_list(self, mock_usa_client, load_fixture):
        """Test that all() returns a list of results."""
        fixture_data = load_fixture("awards/idv_awards.json")
        limit = 5
        expected_results = fixture_data["results"][:limit]

        # Set up paginated response
        mock_usa_client.set_paginated_response("/idvs/awards/", expected_results, page_size=100)

        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123").limit(limit)
        results = search.all()

        assert isinstance(results, list)
        assert len(results) == len(expected_results)
        assert all(isinstance(r, Award) for r in results)

        # Verify each result matches corresponding fixture data
        for result, expected in zip(results, expected_results):
            assert result.generated_unique_award_id == expected["generated_unique_award_id"]


class TestCount:
    """Test count functionality."""

    def test_count_iterates_results(self, mock_usa_client, load_fixture):
        """Test that count() iterates through all results."""
        fixture_data = load_fixture("awards/idv_awards.json")

        # Use paginated response to properly handle iteration
        mock_usa_client.set_paginated_response(
            "/idvs/awards/", fixture_data["results"], page_size=100
        )

        search = IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
        count = search.count()

        assert count == len(fixture_data["results"])


class TestQueryChaining:
    """Test query method chaining."""

    def test_query_chaining(self, mock_usa_client):
        """Test that query methods can be chained."""
        search = (
            IDVChildAwardsSearch(mock_usa_client, "CONT_IDV_123")
            .order_by("piid", "asc")
            .award_type("grandchild_awards")
            .limit(25)
            .page_size(10)
        )

        assert search._award_id == "CONT_IDV_123"
        assert search._sort_field == "piid"
        assert search._sort_order == "asc"
        assert search._idv_award_type == "grandchild_awards"
        assert search._total_limit == 25
        assert search._page_size == 10


class TestFixtureDataIntegrity:
    """Test that fixture data matches expected structure."""

    def test_fixture_has_expected_fields(self, load_fixture):
        """Test that fixture data has expected fields."""
        fixture_data = load_fixture("awards/idv_awards.json")

        assert "results" in fixture_data
        assert "page_metadata" in fixture_data
        assert len(fixture_data["results"]) > 0

        # Check first result has expected fields
        first_result = fixture_data["results"][0]
        expected_fields = [
            "award_id",
            "award_type",
            "description",
            "funding_agency",
            "awarding_agency",
            "generated_unique_award_id",
            "obligated_amount",
            "period_of_performance_start_date",
            "period_of_performance_current_end_date",
            "piid",
        ]
        for field in expected_fields:
            assert field in first_result, f"Missing field: {field}"

    def test_fixture_pagination_metadata(self, load_fixture):
        """Test that fixture has correct pagination metadata."""
        fixture_data = load_fixture("awards/idv_awards.json")

        page_metadata = fixture_data["page_metadata"]
        assert "page" in page_metadata
        assert "hasNext" in page_metadata
        assert "hasPrevious" in page_metadata
