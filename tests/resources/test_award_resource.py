"""Tests for award resource implementation."""

import pytest

from usaspending.resources import AwardResource
from usaspending.models import Award, Recipient
from usaspending.exceptions import ValidationError
from tests.mocks.mock_client import MockUSASpendingClient


class TestAwardResource:
    """Tests for AwardResource.find_by_generated_id() method."""

    @pytest.fixture
    def award_resource(self, mock_usa_client):
        """Create an AwardResource instance with mocked client."""
        return AwardResource(mock_usa_client)

    def test_get_award_success(
        self, award_resource, mock_usa_client, award_fixture_data
    ):
        """Test successful award retrieval."""
        award_id = "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        endpoint = MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(
            award_id=award_id
        )
        # Setup mock response using fixture
        mock_usa_client.set_fixture_response(endpoint, "awards/contract")

        # Call the method
        award = award_resource.find_by_generated_id(award_id)

        # Verify return value
        assert isinstance(award, Award)
        assert award._client is mock_usa_client
        assert (
            award.generated_unique_award_id
            == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        )

    def test_get_award_strips_whitespace(self, award_resource, mock_usa_client):
        """Test that award_id is stripped of whitespace."""
        award_id = "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        endpoint = MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(
            award_id=award_id
        )
        # Setup mock response using fixture
        mock_usa_client.set_fixture_response(endpoint, "awards/contract")

        award = award_resource.find_by_generated_id(f"  {award_id}  ")

        # Verify the award was retrieved successfully
        assert (
            award.generated_unique_award_id
            == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        )

    def test_get_award_empty_id_raises_validation_error(self, award_resource):
        """Test that empty award_id raises ValidationError."""
        with pytest.raises(ValidationError):
            award_resource.find_by_generated_id("")

        with pytest.raises(ValidationError):
            award_resource.find_by_generated_id(None)

        with pytest.raises(ValidationError):
            award_resource.find_by_generated_id("   ")

    def test_get_award_api_error_propagates(self, award_resource, mock_usa_client):
        """Test that API errors are propagated."""
        award_id = "INVALID_AWARD_ID"
        endpoint = MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(
            award_id=award_id
        )
        # Set up error response
        mock_usa_client.set_error_response(
            endpoint, 404, error_message="Award not found"
        )

        from usaspending.exceptions import HTTPError

        with pytest.raises(HTTPError, match="Award not found"):
            award_resource.find_by_generated_id(award_id)

    def test_award_model_initialization_with_client(
        self, award_fixture_data, mock_usa_client
    ):
        """Test Award model initialization with client parameter."""
        award = Award(award_fixture_data, client=mock_usa_client)

        assert award._client is mock_usa_client
        assert (
            award.generated_unique_award_id
            == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        )

    def test_award_model_initialization_raises_error_without_client(
        self, award_fixture_data
    ):
        """Test Award model initialization without client parameter."""

        with pytest.raises(TypeError):
            Award(award_fixture_data)

    def test_award_loads_related_models(self, award_fixture_data, mock_usa_client):
        """Test that Award model properties work with fixture data."""
        award = Award(award_fixture_data, mock_usa_client)

        # Test that recipient data is accessible
        assert isinstance(award.recipient, Recipient)
        assert isinstance(award.recipient.name, str)
        assert len(award.recipient.name) > 0

        # Test place of performance
        assert award.place_of_performance is not None
        assert award.place_of_performance.state_code == award_fixture_data.get(
            "place_of_performance", {}
        ).get("state_code")


class TestFindByAwardId:
    """Tests for AwardResource.find_by_award_id() method."""

    @pytest.fixture
    def award_resource(self, mock_usa_client):
        """Create an AwardResource instance with mocked client."""
        return AwardResource(mock_usa_client)

    def test_find_single_contract_award(self, award_resource, mock_usa_client):
        """Test successful retrieval of a single contract award."""
        # Mock count response - exactly one contract
        count_response = {
            "results": {
                "contracts": 1,
                "grants": 0,
                "idvs": 0,
                "loans": 0,
                "direct_payments": 0,
                "other": 0,
            }
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, count_response
        )

        # Mock search response
        search_response = {
            "results": [
                {
                    "generated_unique_award_id": "CONT_AWD_12345",
                    "piid": "12345",
                    "Award Amount": 100000,
                }
            ],
            "page_metadata": {"hasNext": False},
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH, search_response
        )

        # Call the method
        result = award_resource.find_by_award_id("12345")

        # Verify result
        assert result is not None
        assert result.generated_unique_award_id == "CONT_AWD_12345"

        # Verify API calls
        assert mock_usa_client.get_request_count() == 2
        # Verify correct endpoints were called (these are POST requests)
        mock_usa_client.assert_called_with(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, method="POST"
        )
        mock_usa_client.assert_called_with(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH, method="POST"
        )

    def test_find_single_grant_award(self, award_resource, mock_usa_client):
        """Test successful retrieval of a single grant award."""
        # Mock count response - exactly one grant
        count_response = {
            "results": {
                "contracts": 0,
                "grants": 1,
                "idvs": 0,
                "loans": 0,
                "direct_payments": 0,
                "other": 0,
            }
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, count_response
        )

        # Mock search response
        search_response = {
            "results": [
                {
                    "generated_unique_award_id": "ASST_NON_12345",
                    "fain": "12345",
                    "Award Amount": 50000,
                }
            ],
            "page_metadata": {"hasNext": False},
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH, search_response
        )

        # Call the method
        result = award_resource.find_by_award_id("12345")

        # Verify result
        assert result is not None
        assert result.generated_unique_award_id == "ASST_NON_12345"

    def test_find_no_awards(self, award_resource, mock_usa_client):
        """Test when no awards are found."""
        # Mock count response - no awards
        count_response = {
            "results": {
                "contracts": 0,
                "grants": 0,
                "idvs": 0,
                "loans": 0,
                "direct_payments": 0,
                "other": 0,
            }
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, count_response
        )

        # Call the method
        result = award_resource.find_by_award_id("NONEXISTENT")

        # Verify result
        assert result is None

        # Verify only count endpoint was called
        assert mock_usa_client.get_request_count() == 1

    def test_find_multiple_awards_same_type(self, award_resource, mock_usa_client):
        """Test when multiple awards of the same type are found."""
        # Mock count response - multiple contracts
        count_response = {
            "results": {
                "contracts": 2,
                "grants": 0,
                "idvs": 0,
                "loans": 0,
                "direct_payments": 0,
                "other": 0,
            }
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, count_response
        )

        # Call the method
        result = award_resource.find_by_award_id("DUPLICATE")

        # Verify result
        assert result is None

        # Verify only count endpoint was called
        assert mock_usa_client.get_request_count() == 1

    def test_find_awards_in_multiple_types(self, award_resource, mock_usa_client):
        """Test when awards are found in multiple types (ambiguous)."""
        # Mock count response - one contract and one grant
        count_response = {
            "results": {
                "contracts": 1,
                "grants": 1,
                "idvs": 0,
                "loans": 0,
                "direct_payments": 0,
                "other": 0,
            }
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, count_response
        )

        # Call the method
        result = award_resource.find_by_award_id("AMBIGUOUS")

        # Verify result
        assert result is None

        # Verify only count endpoint was called
        assert mock_usa_client.get_request_count() == 1

    def test_all_award_types(self, award_resource, mock_usa_client):
        """Test that all award types are properly mapped."""
        award_types = [
            ("contracts", "CONT_AWD_"),
            ("grants", "ASST_NON_"),
            ("idvs", "IDV_AWD_"),
            ("loans", "ASST_NON_"),
            ("direct_payments", "ASST_NON_"),
            ("other", "ASST_NON_"),
        ]

        for award_type, id_prefix in award_types:
            # Reset request history
            mock_usa_client._request_history.clear()

            # Mock count response
            count_response = {
                "results": {
                    "contracts": 0,
                    "grants": 0,
                    "idvs": 0,
                    "loans": 0,
                    "direct_payments": 0,
                    "other": 0,
                }
            }
            count_response["results"][award_type] = 1
            mock_usa_client.set_response(
                MockUSASpendingClient.Endpoints.AWARD_COUNT, count_response
            )

            # Mock search response
            search_response = {
                "results": [
                    {
                        "generated_unique_award_id": f"{id_prefix}TEST_{award_type}",
                        "Award Amount": 100000,
                    }
                ],
                "page_metadata": {"hasNext": False},
            }
            mock_usa_client.set_response(
                MockUSASpendingClient.Endpoints.AWARD_SEARCH, search_response
            )

            # Call the method
            result = award_resource.find_by_award_id(f"TEST_{award_type}")

            # Verify result
            assert result is not None, f"Failed for award type: {award_type}"
            assert result.generated_unique_award_id == f"{id_prefix}TEST_{award_type}"

    def test_unknown_award_type_from_api(self, award_resource, mock_usa_client):
        """Test handling of unknown award type from API."""
        # Mock count response with unknown type
        count_response = {
            "results": {
                "contracts": 0,
                "grants": 0,
                "idvs": 0,
                "loans": 0,
                "direct_payments": 0,
                "other": 0,
                "unknown_type": 1,  # This shouldn't happen but tests error handling
            }
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, count_response
        )

        # Call the method
        result = award_resource.find_by_award_id("UNKNOWN")

        # Verify result
        assert result is None

    def test_api_call_sequence(self, award_resource, mock_usa_client):
        """Test that API calls happen in the correct sequence."""
        # Mock count response
        count_response = {
            "results": {
                "contracts": 1,
                "grants": 0,
                "idvs": 0,
                "loans": 0,
                "direct_payments": 0,
                "other": 0,
            }
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_COUNT, count_response
        )

        # Mock search response
        search_response = {
            "results": [
                {"generated_unique_award_id": "CONT_AWD_12345", "piid": "12345"}
            ],
            "page_metadata": {"hasNext": False},
        }
        mock_usa_client.set_response(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH, search_response
        )

        # Call the method
        award_resource.find_by_award_id("12345")

        # Verify request sequence
        assert mock_usa_client.get_request_count() == 2

        # Check that correct endpoints were called with correct parameters
        mock_usa_client.assert_called_with(
            MockUSASpendingClient.Endpoints.AWARD_COUNT,
            method="POST",
            json={"filters": {"award_ids": ["12345"]}},
        )

        # The second call should include award type codes filter
        last_request = mock_usa_client.get_last_request(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH
        )
        assert last_request is not None
        assert "filters" in last_request["json"]
        assert "award_ids" in last_request["json"]["filters"]
        assert last_request["json"]["filters"]["award_ids"] == ["12345"]
        assert "award_type_codes" in last_request["json"]["filters"]
