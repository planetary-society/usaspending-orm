"""Tests for SubAgencyQuery query implementation."""

import pytest
from usaspending.queries.sub_agency_query import SubAgencyQuery
from usaspending.exceptions import ValidationError
from usaspending.models.award_types import CONTRACT_CODES, GRANT_CODES


class TestSubAgencyQueryInitialization:
    """Test SubAgencyQuery initialization."""

    def test_initialization(self, mock_usa_client):
        """Test that SubAgencyQuery initializes correctly with client."""
        query = SubAgencyQuery(mock_usa_client)
        assert query._client is mock_usa_client


class TestSubAgencyQueryEndpoint:
    """Test SubAgencyQuery endpoint construction."""

    def test_base_endpoint(self, mock_usa_client):
        """Test base endpoint property."""
        query = SubAgencyQuery(mock_usa_client)
        assert query._endpoint == mock_usa_client.Endpoints.AGENCY_SUBAGENCIES

    def test_construct_endpoint(self, mock_usa_client):
        """Test endpoint construction with toptier_code."""
        query = SubAgencyQuery(mock_usa_client)
        endpoint = query._construct_endpoint("080")
        assert endpoint == "/agency/080/sub_agency/"


class TestSubAgencyQueryValidation:
    """Test SubAgencyQuery parameter validation."""

    def test_empty_toptier_code_raises_error(self, mock_usa_client):
        """Test that empty toptier_code raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="toptier_code is required"):
            query.get_subagencies("")

    def test_none_toptier_code_raises_error(self, mock_usa_client):
        """Test that None toptier_code raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="toptier_code is required"):
            query.get_subagencies(None)

    def test_invalid_toptier_code_non_numeric_raises_error(self, mock_usa_client):
        """Test that non-numeric toptier_code raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="Invalid toptier_code: ABC"):
            query.get_subagencies("ABC")

    def test_invalid_toptier_code_wrong_length_raises_error(self, mock_usa_client):
        """Test that toptier_code with wrong length raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        # Too short
        with pytest.raises(ValidationError, match="Invalid toptier_code: 12"):
            query.get_subagencies("12")

        # Too long
        with pytest.raises(ValidationError, match="Invalid toptier_code: 12345"):
            query.get_subagencies("12345")

    def test_valid_toptier_codes_accepted(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test that valid toptier_codes are accepted."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        # 3-digit code
        result = query.get_subagencies("080")
        assert result["toptier_code"] == "080"

        # 4-digit code
        mock_usa_client.set_response(
            "/agency/1601/sub_agency/", agency_subagencies_fixture_data
        )
        result = query.get_subagencies("1601")
        assert result["toptier_code"] == "080"  # Fixture data

    def test_invalid_agency_type_raises_error(self, mock_usa_client):
        """Test that invalid agency_type raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="Invalid agency_type: invalid"):
            query.get_subagencies("080", agency_type="invalid")

    def test_valid_agency_types_accepted(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test that valid agency_types are accepted."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        # Test awarding
        result = query.get_subagencies("080", agency_type="awarding")
        assert result is not None

        # Test funding
        result = query.get_subagencies("080", agency_type="funding")
        assert result is not None

    def test_invalid_order_raises_error(self, mock_usa_client):
        """Test that invalid order raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="Invalid order: invalid"):
            query.get_subagencies("080", order="invalid")

    def test_valid_order_accepted(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test that valid order values are accepted."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        # Test asc
        result = query.get_subagencies("080", order="asc")
        assert result is not None

        # Test desc
        result = query.get_subagencies("080", order="desc")
        assert result is not None

    def test_invalid_sort_raises_error(self, mock_usa_client):
        """Test that invalid sort raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="Invalid sort: invalid"):
            query.get_subagencies("080", sort="invalid")

    def test_valid_sort_accepted(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test that valid sort values are accepted."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        valid_sorts = [
            "name",
            "total_obligations",
            "transaction_count",
            "new_award_count",
        ]
        for sort_field in valid_sorts:
            result = query.get_subagencies("080", sort=sort_field)
            assert result is not None

    def test_invalid_page_raises_error(self, mock_usa_client):
        """Test that invalid page raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        with pytest.raises(ValidationError, match="page must be >= 1"):
            query.get_subagencies("080", page=0)

    def test_invalid_limit_raises_error(self, mock_usa_client):
        """Test that invalid limit raises ValidationError."""
        query = SubAgencyQuery(mock_usa_client)

        # Too small
        with pytest.raises(ValidationError, match="limit must be between 1 and 100"):
            query.get_subagencies("080", limit=0)

        # Too large
        with pytest.raises(ValidationError, match="limit must be between 1 and 100"):
            query.get_subagencies("080", limit=101)


class TestSubAgencyQueryExecution:
    """Test SubAgencyQuery query execution."""

    def test_get_subagencies_basic(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test basic sub-agencies retrieval."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        result = query.get_subagencies("080")

        # Verify API call was made correctly
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
            },
        )

        # Verify result structure
        assert result["toptier_code"] == "080"
        assert result["fiscal_year"] == 2025
        assert "page_metadata" in result
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["messages"] == []

    def test_get_subagencies_with_fiscal_year(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test sub-agencies with fiscal year parameter."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        result = query.get_subagencies("080", fiscal_year=2024)

        # Verify API call was made with fiscal_year
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
                "fiscal_year": 2024,
            },
        )

        assert result is not None

    def test_get_subagencies_with_agency_type(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test sub-agencies with agency_type parameter."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        result = query.get_subagencies("080", agency_type="funding")

        # Verify API call was made with funding agency_type
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "funding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
            },
        )

        assert result is not None

    def test_get_subagencies_with_award_type_codes_list(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test sub-agencies with award_type_codes as list."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        award_codes = list(CONTRACT_CODES)
        result = query.get_subagencies("080", award_type_codes=award_codes)

        # Verify API call was made with award_type_codes
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
                "award_type_codes": award_codes,
            },
        )

        assert result is not None

    def test_get_subagencies_with_award_type_codes_set(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test sub-agencies with award_type_codes as set."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        award_codes = GRANT_CODES  # This is a frozenset
        result = query.get_subagencies("080", award_type_codes=award_codes)

        # Verify API call was made with converted list
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
                "award_type_codes": list(award_codes),
            },
        )

        assert result is not None

    def test_get_subagencies_with_pagination(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test sub-agencies with pagination parameters."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        result = query.get_subagencies("080", page=2, limit=50)

        # Verify API call was made with pagination
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 2,
                "limit": 50,
            },
        )

        assert result is not None

    def test_get_subagencies_with_sorting(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test sub-agencies with sorting parameters."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        result = query.get_subagencies("080", sort="name", order="asc")

        # Verify API call was made with sorting
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "asc",
                "sort": "name",
                "page": 1,
                "limit": 100,
            },
        )

        assert result is not None

    def test_get_subagencies_with_all_parameters(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test sub-agencies with all parameters."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        award_codes = ["A", "B", "C"]
        result = query.get_subagencies(
            "080",
            fiscal_year=2023,
            agency_type="funding",
            award_type_codes=award_codes,
            order="asc",
            sort="name",
            page=2,
            limit=25,
        )

        # Verify API call was made with all parameters
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "funding",
                "order": "asc",
                "sort": "name",
                "page": 2,
                "limit": 25,
                "fiscal_year": 2023,
                "award_type_codes": award_codes,
            },
        )

        assert result is not None

    def test_get_subagencies_filters_empty_award_codes(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test that empty/None award codes are filtered out."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        award_codes = ["A", "", None, "B", ""]
        result = query.get_subagencies("080", award_type_codes=award_codes)

        # Should only include non-empty codes
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
                "award_type_codes": ["A", "B"],
            },
        )

        assert result is not None

    def test_get_subagencies_skips_empty_award_codes_list(
        self, mock_usa_client, agency_subagencies_fixture_data
    ):
        """Test that empty award codes list is not included in params."""
        query = SubAgencyQuery(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/sub_agency/", agency_subagencies_fixture_data
        )

        award_codes = ["", None, ""]  # All empty
        result = query.get_subagencies("080", award_type_codes=award_codes)

        # Should not include award_type_codes param
        mock_usa_client.assert_called_with(
            "/agency/080/sub_agency/",
            "GET",
            params={
                "agency_type": "awarding",
                "order": "desc",
                "sort": "total_obligations",
                "page": 1,
                "limit": 100,
            },
        )

        assert result is not None


class TestSubAgencyQueryNotImplemented:
    """Test methods that should not be used."""

    def test_find_by_id_raises_not_implemented_error(self, mock_usa_client):
        """Test that find_by_id raises NotImplementedError."""
        query = SubAgencyQuery(mock_usa_client)

        with pytest.raises(NotImplementedError, match="Use get_subagencies"):
            query.find_by_id("080")
