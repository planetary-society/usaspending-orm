"""Tests for AwardAccount model."""

from decimal import Decimal

import pytest

from usaspending.models.agency import Agency
from usaspending.models.award_account import AwardAccount


@pytest.fixture(autouse=True)
def account_parent_response(mock_usa_client, load_fixture):
    """Supply the recorded account hierarchy for lazy parent resolution."""
    mock_usa_client.set_response(
        "/references/filter_tree/tas/",
        {
            "results": [
                {"id": "080", "children": load_fixture("tas_federal_accounts.json")["results"]}
            ]
        },
    )


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
    def first_account(self, first_account_data, mock_usa_client):
        """Create AwardAccount from first fixture record."""
        return AwardAccount(first_account_data, mock_usa_client)

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

    @pytest.mark.parametrize("account_index", [0, 1])
    def test_toptier_code_resolution(self, accounts_fixture, account_index, mock_usa_client):
        """The recorded TAS hierarchy supplies each account's parent code."""
        account = AwardAccount(accounts_fixture["results"][account_index], mock_usa_client)
        assert account.toptier_code == "080"


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

    @pytest.mark.parametrize("account_index", [0, 1])
    def test_tas_codes_use_the_parent_returned_by_the_hierarchy(
        self, accounts_fixture, account_index, mock_usa_client
    ):
        """Test tas_codes resolves the parent on iteration, not on access."""
        federal_account = accounts_fixture["results"][account_index]["federal_account"]
        account = AwardAccount(accounts_fixture["results"][account_index], mock_usa_client)
        endpoint = f"/references/filter_tree/tas/080/{federal_account}/"
        mock_usa_client.set_response(endpoint, {"results": []})

        tas_query = account.tas_codes
        assert mock_usa_client.get_request_count() == 0
        assert tas_query.all() == []
        assert mock_usa_client.get_request_count(endpoint) == 1


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

    @pytest.mark.parametrize("code", [None, ""])
    def test_missing_code_does_not_resolve_parent(self, mock_usa_client, code):
        account = AwardAccount({"federal_account": code}, mock_usa_client)
        mock_usa_client.forbid_requests()
        assert account.toptier_code is None

    def test_missing_obligated_amount_returns_none(self, mock_usa_client):
        """An absent amount is None, so callers can tell it from a reported zero."""
        account_data = {
            "federal_account": "080-0131",
            "account_title": "Test Account",
        }
        account = AwardAccount(account_data, mock_usa_client)
        assert account.total_transaction_obligated_amount is None
        assert account.obligated_amount is None

    def test_reported_zero_obligated_amount_is_decimal_zero(self, mock_usa_client):
        """A zero the API actually reports stays Decimal("0.00")."""
        account = AwardAccount(
            {"federal_account": "080-0131", "total_transaction_obligated_amount": 0},
            mock_usa_client,
        )
        assert account.total_transaction_obligated_amount == Decimal("0.00")

    def test_repr_renders_a_missing_amount_as_zero(self, mock_usa_client):
        """__repr__ guards the format, so an absent amount renders rather than raising."""
        account = AwardAccount({"federal_account": "080-0131"}, mock_usa_client)
        assert "$0.00" in repr(account)
