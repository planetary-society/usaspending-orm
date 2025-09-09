"""Tests for AgencyAwardSummary query implementation."""

import pytest
from usaspending.queries.agency_award_summary import AgencyAwardSummary
from usaspending.exceptions import ValidationError
from usaspending.models.award_types import CONTRACT_CODES, GRANT_CODES


class TestAgencyAwardSummaryInitialization:
    """Test AgencyAwardSummary initialization."""

    def test_initialization(self, mock_usa_client):
        """Test that AgencyAwardSummary initializes correctly with client."""
        query = AgencyAwardSummary(mock_usa_client)
        assert query._client is mock_usa_client


class TestAgencyAwardSummaryEndpoint:
    """Test AgencyAwardSummary endpoint construction."""

    def test_base_endpoint(self, mock_usa_client):
        """Test base endpoint property."""
        query = AgencyAwardSummary(mock_usa_client)
        assert query._endpoint == "/agency/"

    def test_construct_endpoint(self, mock_usa_client):
        """Test endpoint construction with toptier_code."""
        query = AgencyAwardSummary(mock_usa_client)
        endpoint = query._construct_endpoint("080")
        assert endpoint == "/agency/080/awards/"


class TestAgencyAwardSummaryValidation:
    """Test AgencyAwardSummary parameter validation."""

    def test_empty_toptier_code_raises_error(self, mock_usa_client):
        """Test that empty toptier_code raises ValidationError."""
        query = AgencyAwardSummary(mock_usa_client)

        with pytest.raises(ValidationError, match="toptier_code is required"):
            query.get_awards_summary("")

    def test_none_toptier_code_raises_error(self, mock_usa_client):
        """Test that None toptier_code raises ValidationError."""
        query = AgencyAwardSummary(mock_usa_client)

        with pytest.raises(ValidationError, match="toptier_code is required"):
            query.get_awards_summary(None)

    def test_invalid_toptier_code_non_numeric_raises_error(self, mock_usa_client):
        """Test that non-numeric toptier_code raises ValidationError."""
        query = AgencyAwardSummary(mock_usa_client)

        with pytest.raises(ValidationError, match="Invalid toptier_code: ABC"):
            query.get_awards_summary("ABC")

    def test_invalid_toptier_code_wrong_length_raises_error(self, mock_usa_client):
        """Test that toptier_code with wrong length raises ValidationError."""
        query = AgencyAwardSummary(mock_usa_client)

        # Too short
        with pytest.raises(ValidationError, match="Invalid toptier_code: 12"):
            query.get_awards_summary("12")

        # Too long
        with pytest.raises(ValidationError, match="Invalid toptier_code: 12345"):
            query.get_awards_summary("12345")

    def test_valid_toptier_codes_accepted(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test that valid toptier_codes are accepted."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        # 3-digit code
        result = query.get_awards_summary("080")
        assert result["toptier_code"] == "080"

        # 4-digit code
        mock_usa_client.set_response(
            "/agency/1601/awards/", agency_award_summary_fixture_data
        )
        result = query.get_awards_summary("1601")
        assert result["toptier_code"] == "080"  # Fixture data

    def test_invalid_agency_type_raises_error(self, mock_usa_client):
        """Test that invalid agency_type raises ValidationError."""
        query = AgencyAwardSummary(mock_usa_client)

        with pytest.raises(ValidationError, match="Invalid agency_type: invalid"):
            query.get_awards_summary("080", agency_type="invalid")

    def test_valid_agency_types_accepted(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test that valid agency_types are accepted."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        # Test awarding
        result = query.get_awards_summary("080", agency_type="awarding")
        assert result is not None

        # Test funding
        result = query.get_awards_summary("080", agency_type="funding")
        assert result is not None


class TestAgencyAwardSummaryExecution:
    """Test AgencyAwardSummary query execution."""

    def test_get_awards_summary_basic(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test basic awards summary retrieval."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        result = query.get_awards_summary("080")

        # Verify API call was made correctly
        mock_usa_client.assert_called_with(
            "/agency/080/awards/", "GET", params={"agency_type": "awarding"}
        )

        # Verify result structure
        assert result["toptier_code"] == "080"
        assert result["fiscal_year"] == 2025
        assert result["obligations"] == 17275121376.15
        assert result["transaction_count"] == 29818
        assert result["latest_action_date"] == "2025-08-25T00:00:00"
        assert result["messages"] == []

    def test_get_awards_summary_with_fiscal_year(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test awards summary with fiscal year parameter."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        result = query.get_awards_summary("080", fiscal_year=2024)

        # Verify API call was made with fiscal_year
        mock_usa_client.assert_called_with(
            "/agency/080/awards/",
            "GET",
            params={"agency_type": "awarding", "fiscal_year": 2024},
        )

        assert result is not None

    def test_get_awards_summary_with_agency_type(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test awards summary with agency_type parameter."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        result = query.get_awards_summary("080", agency_type="funding")

        # Verify API call was made with funding agency_type
        mock_usa_client.assert_called_with(
            "/agency/080/awards/", "GET", params={"agency_type": "funding"}
        )

        assert result is not None

    def test_get_awards_summary_with_award_type_codes_list(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test awards summary with award_type_codes as list."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        award_codes = list(CONTRACT_CODES)
        result = query.get_awards_summary("080", award_type_codes=award_codes)

        # Verify API call was made with award_type_codes
        mock_usa_client.assert_called_with(
            "/agency/080/awards/",
            "GET",
            params={"agency_type": "awarding", "award_type_codes": award_codes},
        )

        assert result is not None

    def test_get_awards_summary_with_award_type_codes_set(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test awards summary with award_type_codes as set."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        award_codes = GRANT_CODES  # This is a frozenset
        result = query.get_awards_summary("080", award_type_codes=award_codes)

        # Verify API call was made with converted list
        mock_usa_client.assert_called_with(
            "/agency/080/awards/",
            "GET",
            params={"agency_type": "awarding", "award_type_codes": list(award_codes)},
        )

        assert result is not None

    def test_get_awards_summary_with_all_parameters(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test awards summary with all parameters."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        award_codes = ["A", "B", "C"]
        result = query.get_awards_summary(
            "080", fiscal_year=2023, agency_type="funding", award_type_codes=award_codes
        )

        # Verify API call was made with all parameters
        mock_usa_client.assert_called_with(
            "/agency/080/awards/",
            "GET",
            params={
                "agency_type": "funding",
                "fiscal_year": 2023,
                "award_type_codes": award_codes,
            },
        )

        assert result is not None

    def test_get_awards_summary_filters_empty_award_codes(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test that empty/None award codes are filtered out."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        award_codes = ["A", "", None, "B", ""]
        result = query.get_awards_summary("080", award_type_codes=award_codes)

        # Should only include non-empty codes
        mock_usa_client.assert_called_with(
            "/agency/080/awards/",
            "GET",
            params={"agency_type": "awarding", "award_type_codes": ["A", "B"]},
        )

        assert result is not None

    def test_get_awards_summary_skips_empty_award_codes_list(
        self, mock_usa_client, agency_award_summary_fixture_data
    ):
        """Test that empty award codes list is not included in params."""
        query = AgencyAwardSummary(mock_usa_client)
        mock_usa_client.set_response(
            "/agency/080/awards/", agency_award_summary_fixture_data
        )

        award_codes = ["", None, ""]  # All empty
        result = query.get_awards_summary("080", award_type_codes=award_codes)

        # Should not include award_type_codes param
        mock_usa_client.assert_called_with(
            "/agency/080/awards/", "GET", params={"agency_type": "awarding"}
        )

        assert result is not None


class TestAgencyAwardSummaryNotImplemented:
    """Test methods that should not be used."""

    def test_find_by_id_raises_not_implemented_error(self, mock_usa_client):
        """Test that find_by_id raises NotImplementedError."""
        query = AgencyAwardSummary(mock_usa_client)

        with pytest.raises(NotImplementedError, match="Use get_awards_summary"):
            query.find_by_id("080")
