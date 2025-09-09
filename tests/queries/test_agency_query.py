"""Tests for AgencyQuery implementation."""

import pytest

from usaspending.queries.agency_query import AgencyQuery
from usaspending.models.agency import Agency
from usaspending.exceptions import ValidationError


class TestAgencyQueryInitialization:
    """Test AgencyQuery initialization."""

    def test_init_with_client(self, mock_usa_client):
        """Test AgencyQuery initialization with client."""
        query = AgencyQuery(mock_usa_client)

        assert query._client is mock_usa_client
        assert query._endpoint == "/agency/"


class TestAgencyQueryValidation:
    """Test AgencyQuery input validation."""

    @pytest.fixture
    def agency_query(self, mock_usa_client):
        """Create an AgencyQuery instance."""
        return AgencyQuery(mock_usa_client)

    def test_find_by_id_empty_toptier_code_raises_validation_error(self, agency_query):
        """Test that empty toptier_code raises ValidationError."""
        with pytest.raises(ValidationError, match="toptier_code is required"):
            agency_query.find_by_id("")

    def test_find_by_id_none_toptier_code_raises_validation_error(self, agency_query):
        """Test that None toptier_code raises ValidationError."""
        with pytest.raises(ValidationError, match="toptier_code is required"):
            agency_query.find_by_id(None)

    @pytest.mark.parametrize(
        "invalid_code",
        [
            "12",  # Too short
            "12345",  # Too long
            "ABC",  # Non-numeric
            "08A",  # Mixed alphanumeric
            " ",  # Whitespace only
        ],
    )
    def test_find_by_id_invalid_toptier_code_format(self, agency_query, invalid_code):
        """Test that invalid toptier_code formats raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid toptier_code"):
            agency_query.find_by_id(invalid_code)

    @pytest.mark.parametrize(
        "valid_code",
        [
            "080",  # 3 digits
            "8000",  # 4 digits
            "012",  # 3 digits starting with 0
            "0120",  # 4 digits starting with 0
        ],
    )
    def test_find_by_id_valid_toptier_code_format(
        self, agency_query, mock_usa_client, agency_fixture_data, valid_code
    ):
        """Test that valid toptier_code formats are accepted."""
        # Setup mock response
        endpoint = f"/agency/{valid_code}/"
        mock_usa_client.set_fixture_response(endpoint, "agency")

        # Should not raise validation error
        result = agency_query.find_by_id(valid_code)
        assert isinstance(result, Agency)


class TestAgencyQueryExecution:
    """Test AgencyQuery execution and API calls."""

    @pytest.fixture
    def agency_query(self, mock_usa_client):
        """Create an AgencyQuery instance."""
        return AgencyQuery(mock_usa_client)

    def test_find_by_id_success_without_fiscal_year(
        self, agency_query, mock_usa_client, agency_fixture_data
    ):
        """Test successful agency retrieval without fiscal year."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"

        # Setup mock response
        mock_usa_client.set_fixture_response(endpoint, "agency")

        # Call the method
        agency = agency_query.find_by_id(toptier_code)

        # Verify return value
        assert isinstance(agency, Agency)
        assert agency._client is mock_usa_client
        assert agency.toptier_code == agency_fixture_data["toptier_code"]
        assert agency.name == agency_fixture_data["name"]

        # Verify API call was made without params
        last_request = mock_usa_client.get_last_request()
        assert last_request["endpoint"] == endpoint
        assert last_request["method"] == "GET"
        assert last_request["params"] is None

    def test_find_by_id_success_with_fiscal_year(
        self, agency_query, mock_usa_client, agency_fixture_data
    ):
        """Test successful agency retrieval with fiscal year."""
        toptier_code = agency_fixture_data["toptier_code"]
        fiscal_year = 2023
        endpoint = f"/agency/{toptier_code}/"

        # Setup mock response
        mock_usa_client.set_fixture_response(endpoint, "agency")

        # Call the method
        agency = agency_query.find_by_id(toptier_code, fiscal_year=fiscal_year)

        # Verify return value
        assert isinstance(agency, Agency)
        assert agency._client is mock_usa_client

        # Verify API call was made with fiscal_year param
        last_request = mock_usa_client.get_last_request()
        assert last_request["endpoint"] == endpoint
        assert last_request["method"] == "GET"
        assert last_request["params"] == {"fiscal_year": fiscal_year}

    def test_find_by_id_strips_whitespace(
        self, agency_query, mock_usa_client, agency_fixture_data
    ):
        """Test that toptier_code whitespace is stripped."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"

        # Setup mock response
        mock_usa_client.set_fixture_response(endpoint, "agency")

        # Call with whitespace around toptier_code
        agency = agency_query.find_by_id(f"  {toptier_code}  ")

        # Verify the agency was retrieved successfully
        assert agency.toptier_code == toptier_code

        # Verify correct endpoint was called (whitespace stripped)
        last_request = mock_usa_client.get_last_request()
        assert last_request["endpoint"] == endpoint

    def test_find_by_id_api_error_propagates(self, agency_query, mock_usa_client):
        """Test that API errors are propagated."""
        toptier_code = "999"
        endpoint = f"/agency/{toptier_code}/"

        # Setup error response
        mock_usa_client.set_error_response(
            endpoint, 404, error_message="Agency not found"
        )

        from usaspending.exceptions import HTTPError

        with pytest.raises(HTTPError, match="Agency not found"):
            agency_query.find_by_id(toptier_code)

    def test_find_by_id_400_error_as_api_error(self, agency_query, mock_usa_client):
        """Test that 400 errors are raised as APIError."""
        toptier_code = "999"
        endpoint = f"/agency/{toptier_code}/"

        # Setup 400 error response
        mock_usa_client.set_error_response(
            endpoint, 400, detail="Invalid toptier_code format"
        )

        from usaspending.exceptions import APIError

        with pytest.raises(APIError, match="Invalid toptier_code format"):
            agency_query.find_by_id(toptier_code)


class TestAgencyQueryModelCreation:
    """Test Agency model creation from AgencyQuery."""

    @pytest.fixture
    def agency_query(self, mock_usa_client):
        """Create an AgencyQuery instance."""
        return AgencyQuery(mock_usa_client)

    def test_agency_model_has_client_reference(
        self, agency_query, mock_usa_client, agency_fixture_data
    ):
        """Test that created Agency model has client reference."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"

        mock_usa_client.set_fixture_response(endpoint, "agency")

        agency = agency_query.find_by_id(toptier_code)

        assert agency._client is mock_usa_client

    def test_agency_model_has_fixture_data(
        self, agency_query, mock_usa_client, agency_fixture_data
    ):
        """Test that Agency model contains data from fixture."""
        toptier_code = agency_fixture_data["toptier_code"]
        endpoint = f"/agency/{toptier_code}/"

        mock_usa_client.set_fixture_response(endpoint, "agency")

        agency = agency_query.find_by_id(toptier_code)

        # Test key properties using fixture data (no hard-coded values)
        assert agency.fiscal_year == agency_fixture_data["fiscal_year"]
        assert agency.toptier_code == agency_fixture_data["toptier_code"]
        assert agency.name == agency_fixture_data["name"]
        assert agency.abbreviation == agency_fixture_data["abbreviation"]
        assert agency.agency_id == agency_fixture_data["agency_id"]
        assert agency.mission == agency_fixture_data["mission"]
        assert agency.website == agency_fixture_data["website"]
        assert (
            agency.subtier_agency_count == agency_fixture_data["subtier_agency_count"]
        )

        # Test def_codes property
        def_codes = agency.def_codes
        expected_def_codes = agency_fixture_data["def_codes"]
        assert len(def_codes) == len(expected_def_codes)

        if expected_def_codes:
            first_def_code = def_codes[0]
            first_expected = expected_def_codes[0]
            assert first_def_code.code == first_expected["code"]
            assert first_def_code.public_law == first_expected["public_law"]
            assert first_def_code.title == first_expected["title"]
            assert first_def_code.disaster == first_expected["disaster"]
