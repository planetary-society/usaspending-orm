"""Tests for SubAgencyQuery query implementation."""

import pytest

from usaspending.exceptions import ValidationError
from usaspending.queries.sub_agency_query import SubAgencyQuery


class TestSubAgencyQueryInitialization:
    """Test SubAgencyQuery initialization."""

    def test_initialization(self, mock_usa_client):
        """Test that SubAgencyQuery initializes correctly with client."""
        query = SubAgencyQuery(mock_usa_client, "080")
        assert query._client is mock_usa_client
        assert query._toptier_code == "080"


class TestSubAgencyQueryEndpoint:
    """Test SubAgencyQuery endpoint construction."""

    def test_endpoint(self, mock_usa_client):
        """Test endpoint construction with toptier_code."""
        query = SubAgencyQuery(mock_usa_client, "080")
        assert query._endpoint == "/agency/080/sub_agency/"


class TestSubAgencyQueryValidation:
    """Test SubAgencyQuery parameter validation."""

    def test_empty_toptier_code_raises_error(self, mock_usa_client):
        """Test that empty toptier_code raises ValidationError."""
        with pytest.raises(ValidationError, match="toptier_code is required"):
            SubAgencyQuery(mock_usa_client, "")

    def test_invalid_toptier_code_non_numeric_raises_error(self, mock_usa_client):
        """Test that non-numeric toptier_code raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid toptier_code: ABC"):
            SubAgencyQuery(mock_usa_client, "ABC")

    def test_invalid_toptier_code_wrong_length_raises_error(self, mock_usa_client):
        """Test that toptier_code with wrong length raises ValidationError."""
        # Too short
        with pytest.raises(ValidationError, match="Invalid toptier_code: 12"):
            SubAgencyQuery(mock_usa_client, "12")

        # Too long
        with pytest.raises(ValidationError, match="Invalid toptier_code: 12345"):
            SubAgencyQuery(mock_usa_client, "12345")


class TestSubAgencyQueryFilters:
    """Test SubAgencyQuery filter methods."""

    def test_fiscal_year(self, mock_usa_client):
        """Test fiscal_year filter."""
        query = SubAgencyQuery(mock_usa_client, "080").fiscal_year(2024)
        assert query._fiscal_year == 2024

    def test_invalid_fiscal_year(self, mock_usa_client):
        """Test invalid fiscal year raises error."""
        with pytest.raises(ValidationError):
            SubAgencyQuery(mock_usa_client, "080").fiscal_year(1900)

    def test_agency_type(self, mock_usa_client):
        """Test agency_type filter."""
        query = SubAgencyQuery(mock_usa_client, "080").agency_type("funding")
        assert query._agency_type == "funding"

    def test_invalid_agency_type(self, mock_usa_client):
        """Test invalid agency_type raises error."""
        with pytest.raises(ValidationError, match="agency_type must be"):
            SubAgencyQuery(mock_usa_client, "080").agency_type("invalid")

    def test_award_type_codes(self, mock_usa_client):
        """Test award_type_codes filter."""
        query = SubAgencyQuery(mock_usa_client, "080").award_type_codes("A", "B")
        assert query._award_type_codes == ["A", "B"]

    def test_order_by(self, mock_usa_client):
        """Test order_by method."""
        query = SubAgencyQuery(mock_usa_client, "080").order_by("name", "asc")
        assert query._order_by == "name"
        assert query._order_direction == "asc"

    def test_invalid_order_by_field(self, mock_usa_client):
        """Test invalid sort field raises error."""
        with pytest.raises(ValidationError, match="Invalid sort field"):
            SubAgencyQuery(mock_usa_client, "080").order_by("invalid_field")

    def test_invalid_order_direction(self, mock_usa_client):
        """Test invalid sort direction raises error."""
        with pytest.raises(ValidationError, match="direction must be"):
            SubAgencyQuery(mock_usa_client, "080").order_by("name", "invalid")


class TestSubAgencyQueryExecution:
    """Test SubAgencyQuery query execution."""

    @pytest.fixture
    def setup_response(self, mock_usa_client, agency_subagencies_fixture_data):
        mock_usa_client.set_response("/agency/080/sub_agency/", agency_subagencies_fixture_data)

    def test_build_payload(self, mock_usa_client):
        """Test payload construction."""
        query = (
            SubAgencyQuery(mock_usa_client, "080")
            .fiscal_year(2024)
            .agency_type("funding")
            .award_type_codes("A", "B")
            .order_by("name", "asc")
            .page_size(50)
        )

        payload = query._build_payload(page=2)

        assert payload == {
            "agency_type": "funding",
            "page": 2,
            "limit": 50,
            "sort": "name",
            "order": "asc",
            "fiscal_year": 2024,
            "award_type_codes": ["A", "B"],
        }

    def test_execute_uses_get(
        self, mock_usa_client, agency_subagencies_fixture_data, setup_response
    ):
        """Test that execution uses GET method."""
        query = SubAgencyQuery(mock_usa_client, "080")

        # Execute query (triggering API call)
        query.all()

        # Verify API call
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "page": 1,
                "limit": 100,  # Default
                "sort": "total_obligations",  # Default
                "order": "desc",  # Default
            },
        )

    def test_count(self, mock_usa_client, agency_subagencies_fixture_data, setup_response):
        """Test count method."""
        query = SubAgencyQuery(mock_usa_client, "080")
        count = query.count()

        # Fixture data usually has page_metadata.total
        expected_count = agency_subagencies_fixture_data["page_metadata"]["total"]
        assert count == expected_count

        def test_iteration_transforms_results(
            self, mock_usa_client, agency_subagencies_fixture_data, setup_response
        ):
            """Test that iteration yields model objects."""

            query = SubAgencyQuery(mock_usa_client, "080")

            results = list(query)

            assert len(results) > 0

            assert results[0].__class__.__name__ == "SubTierAgency"

            assert results[0].name is not None

        def test_first_returns_single_item(
            self, mock_usa_client, agency_subagencies_fixture_data, setup_response
        ):
            """Test that .first() returns a single model instance."""

            query = SubAgencyQuery(mock_usa_client, "080")

            result = query.first()

            assert result.__class__.__name__ == "SubTierAgency"

            # Verify limit(1) was passed to API

            mock_usa_client.assert_called_with(
                "/agency/080/sub_agency/",
                "GET",
                params={
                    "agency_type": "awarding",
                    "page": 1,
                    "limit": 1,
                    "sort": "total_obligations",
                    "order": "desc",
                },
            )

        def test_limit_restricts_results(
            self, mock_usa_client, agency_subagencies_fixture_data, setup_response
        ):
            """Test that .limit() restricts the number of yielded items."""

            # Mock 20 results across 2 pages

            data = [{"name": f"Sub {i}"} for i in range(20)]

            mock_usa_client.set_paginated_response("/agency/080/sub_agency/", data, page_size=10)

            query = SubAgencyQuery(mock_usa_client, "080").limit(5)

            results = list(query)

            assert len(results) == 5

        def test_indexing_fetches_specific_page(
            self, mock_usa_client, agency_subagencies_fixture_data, setup_response
        ):
            """Test that [index] access works correctly."""

            # Setup 15 results, page size 5

            data = [{"name": f"Sub {i}", "code": str(i)} for i in range(15)]

            mock_usa_client.set_paginated_response("/agency/080/sub_agency/", data, page_size=5)

            query = SubAgencyQuery(mock_usa_client, "080").page_size(5)

            # Access index 12 (should be in page 3)

            item = query[12]

            assert item.code == "12"

            # Verify page 3 was requested

            mock_usa_client.assert_called_with(
                "/agency/080/sub_agency/",
                "GET",
                params={
                    "agency_type": "awarding",
                    "page": 3,
                    "limit": 5,
                    "sort": "total_obligations",
                    "order": "desc",
                },
            )
