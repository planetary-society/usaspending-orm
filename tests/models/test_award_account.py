"""Tests for AwardAccount model."""

from decimal import Decimal

import pytest

from usaspending.models.agency import Agency
from usaspending.models.award_account import AwardAccount


class TestAwardAccountInitialization:
    """Tests for AwardAccount initialization and field mapping."""

    @pytest.fixture
    def accounts_fixture(self, load_fixture):
        """Load accounts fixture data."""
        return load_fixture("awards/accounts.json")

    @pytest.fixture
    def first_account_data(self, accounts_fixture):
        """Get first account data from fixture."""
        return accounts_fixture["results"][0]

    @pytest.fixture
    def second_account_data(self, accounts_fixture):
        """Get second account data from fixture."""
        return accounts_fixture["results"][1]

    @pytest.fixture
    def first_account(self, first_account_data, mock_usa_client):
        """Create AwardAccount from first fixture record."""
        return AwardAccount(first_account_data, mock_usa_client)

    @pytest.fixture
    def second_account(self, second_account_data, mock_usa_client):
        """Create AwardAccount from second fixture record."""
        return AwardAccount(second_account_data, mock_usa_client)

    def test_initialization_from_api_response(self, first_account):
        """Test initialization with API response data."""
        assert first_account is not None
        assert isinstance(first_account, AwardAccount)

    def test_field_mapping_federal_account_to_id(self, first_account, first_account_data):
        """Test that federal_account is mapped to id property."""
        expected = first_account_data["federal_account"]
        assert first_account.id == expected
        assert first_account.code == expected
        assert first_account.federal_account_code == expected

    def test_federal_account(self, first_account, first_account_data):
        """Test federal_account property."""
        expected = first_account_data["federal_account"]
        assert first_account.federal_account == expected

    def test_field_mapping_account_title_to_description(self, first_account, first_account_data):
        """Test that account_title is mapped to description property."""
        expected = first_account_data["account_title"]
        assert first_account.description == expected
        assert first_account.name == expected
        assert first_account.title == expected

    def test_account_title(self, first_account, first_account_data):
        """Test account_title property."""
        expected = first_account_data["account_title"]
        assert first_account.account_title == expected

    def test_toptier_code_extraction(self, first_account, first_account_data):
        """Test that toptier_code is extracted from federal_account."""
        expected_toptier = first_account_data["federal_account"].split("-")[0]
        assert first_account.toptier_code == expected_toptier

    def test_toptier_code_extraction_second_account(self, second_account, second_account_data):
        """Test toptier_code extraction from second fixture account."""
        expected_id = second_account_data["federal_account"]
        expected_toptier = expected_id.split("-")[0]
        assert second_account.id == expected_id
        assert second_account.toptier_code == expected_toptier


class TestAwardAccountProperties:
    """Tests for AwardAccount properties."""

    @pytest.fixture
    def accounts_fixture(self, load_fixture):
        """Load accounts fixture data."""
        return load_fixture("awards/accounts.json")

    @pytest.fixture
    def first_account_data(self, accounts_fixture):
        """Get first account data from fixture."""
        return accounts_fixture["results"][0]

    @pytest.fixture
    def first_account(self, first_account_data, mock_usa_client):
        """Create AwardAccount from first fixture record."""
        return AwardAccount(first_account_data, mock_usa_client)

    def test_total_transaction_obligated_amount(self, first_account, first_account_data):
        """Test total_transaction_obligated_amount property."""
        expected = Decimal(str(first_account_data["total_transaction_obligated_amount"]))
        assert first_account.total_transaction_obligated_amount == expected
        assert isinstance(first_account.total_transaction_obligated_amount, Decimal)

    def test_obligated_amount_alias(self, first_account):
        """Test obligated_amount is an alias for total_transaction_obligated_amount."""
        assert first_account.obligated_amount == first_account.total_transaction_obligated_amount

    def test_funding_agency_name(self, first_account, first_account_data):
        """Test funding_agency_name property."""
        assert first_account.funding_agency_name == first_account_data["funding_agency_name"]

    def test_funding_agency_abbreviation(self, first_account, first_account_data):
        """Test funding_agency_abbreviation property."""
        assert (
            first_account.funding_agency_abbreviation
            == first_account_data["funding_agency_abbreviation"]
        )

    def test_funding_agency_id(self, first_account, first_account_data):
        """Test funding_agency_id property."""
        assert first_account.funding_agency_id == first_account_data["funding_agency_id"]

    def test_funding_toptier_agency_id(self, first_account, first_account_data):
        """Test funding_toptier_agency_id property returns string."""
        assert first_account.funding_toptier_agency_id == str(
            first_account_data["funding_toptier_agency_id"]
        )

    def test_funding_agency_slug(self, first_account, first_account_data):
        """Test funding_agency_slug property."""
        assert first_account.funding_agency_slug == first_account_data["funding_agency_slug"]


class TestAwardAccountFundingAgency:
    """Tests for the funding_agency property."""

    @pytest.fixture
    def accounts_fixture(self, load_fixture):
        """Load accounts fixture data."""
        return load_fixture("awards/accounts.json")

    @pytest.fixture
    def first_account_data(self, accounts_fixture):
        """Get first account data from fixture."""
        return accounts_fixture["results"][0]

    @pytest.fixture
    def first_account(self, first_account_data, mock_usa_client):
        """Create AwardAccount from first fixture record."""
        return AwardAccount(first_account_data, mock_usa_client)

    def test_funding_agency_creates_agency_object(self, first_account):
        """Test funding_agency returns an Agency object."""
        agency = first_account.funding_agency
        assert agency is not None
        assert isinstance(agency, Agency)

    def test_funding_agency_has_correct_properties(self, first_account, first_account_data):
        """Test funding_agency Agency object has correct properties."""
        agency = first_account.funding_agency
        assert agency.name == first_account_data["funding_agency_name"]
        assert agency.abbreviation == first_account_data["funding_agency_abbreviation"]
        assert agency.slug == first_account_data["funding_agency_slug"]

    def test_funding_agency_is_cached(self, first_account):
        """Test funding_agency property is cached."""
        agency1 = first_account.funding_agency
        agency2 = first_account.funding_agency
        assert agency1 is agency2

    def test_funding_agency_returns_none_when_no_data(self, mock_usa_client):
        """Test funding_agency returns None when no funding agency data."""
        account_data = {
            "federal_account": "080-0131",
            "account_title": "Test Account",
            "total_transaction_obligated_amount": 1000.00,
        }
        account = AwardAccount(account_data, mock_usa_client)
        assert account.funding_agency is None


class TestAwardAccountTASCodes:
    """Tests for the tas_codes property."""

    @pytest.fixture
    def accounts_fixture(self, load_fixture):
        """Load accounts fixture data."""
        return load_fixture("awards/accounts.json")

    @pytest.fixture
    def first_account_data(self, accounts_fixture):
        """Get first account data from fixture."""
        return accounts_fixture["results"][0]

    @pytest.fixture
    def second_account_data(self, accounts_fixture):
        """Get second account data from fixture."""
        return accounts_fixture["results"][1]

    @pytest.fixture
    def first_account(self, first_account_data, mock_usa_client):
        """Create AwardAccount from first fixture record."""
        return AwardAccount(first_account_data, mock_usa_client)

    @pytest.fixture
    def second_account(self, second_account_data, mock_usa_client):
        """Create AwardAccount from second fixture record."""
        return AwardAccount(second_account_data, mock_usa_client)

    def test_tas_codes_has_correct_toptier_code(self, first_account, first_account_data):
        """Test tas_codes uses toptier_code extracted from federal_account."""
        federal_account = first_account_data["federal_account"]
        expected_toptier = federal_account.split("-")[0]

        tas_query = first_account.tas_codes
        assert tas_query._toptier_code == expected_toptier
        assert tas_query._federal_account == federal_account

    def test_tas_codes_works_for_second_account(self, second_account, second_account_data):
        """Test tas_codes for second fixture account."""
        federal_account = second_account_data["federal_account"]
        expected_toptier = federal_account.split("-")[0]

        tas_query = second_account.tas_codes
        assert tas_query._toptier_code == expected_toptier
        assert tas_query._federal_account == federal_account


class TestAwardAccountRepr:
    """Tests for AwardAccount string representation."""

    @pytest.fixture
    def accounts_fixture(self, load_fixture):
        """Load accounts fixture data."""
        return load_fixture("awards/accounts.json")

    @pytest.fixture
    def first_account_data(self, accounts_fixture):
        """Get first account data from fixture."""
        return accounts_fixture["results"][0]

    @pytest.fixture
    def first_account(self, first_account_data, mock_usa_client):
        """Create AwardAccount from first fixture record."""
        return AwardAccount(first_account_data, mock_usa_client)

    def test_repr(self, first_account, first_account_data):
        """Test __repr__ output contains fixture data."""
        repr_str = repr(first_account)

        assert "AwardAccount" in repr_str
        assert first_account_data["federal_account"] in repr_str
        assert first_account_data["funding_agency_abbreviation"] in repr_str


class TestAwardAccountEdgeCases:
    """Tests for edge cases and error handling."""

    def test_extract_toptier_code_with_none(self):
        """Test _extract_toptier_code with None input."""
        result = AwardAccount._extract_toptier_code(None)
        assert result is None

    def test_extract_toptier_code_with_empty_string(self):
        """Test _extract_toptier_code with empty string."""
        result = AwardAccount._extract_toptier_code("")
        assert result is None

    def test_extract_toptier_code_with_no_hyphen(self):
        """Test _extract_toptier_code with no hyphen."""
        result = AwardAccount._extract_toptier_code("0800131")
        assert result == "0800131"

    def test_missing_obligated_amount_returns_zero(self, mock_usa_client):
        """Test missing total_transaction_obligated_amount returns zero."""
        account_data = {
            "federal_account": "080-0131",
            "account_title": "Test Account",
        }
        account = AwardAccount(account_data, mock_usa_client)
        assert account.total_transaction_obligated_amount == Decimal("0.00")
