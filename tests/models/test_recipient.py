from __future__ import annotations

from tests.utils import assert_decimal_equal
"""Tests for Recipient model functionality."""

import pytest

from usaspending.models.recipient import Recipient
from usaspending.models.location import Location
from usaspending.exceptions import ValidationError
from usaspending.utils.formatter import contracts_titlecase
from tests.conftest import load_json_fixture


class TestRecipientInitialization:
    """Test Recipient model initialization."""

    def test_init_with_dict_data(self, mock_usa_client):
        """Test Recipient initialization with dictionary data."""
        fixture_data = load_json_fixture("recipient_university.json")
        data = {
            "recipient_id": fixture_data["recipient_id"],
            "name": fixture_data["name"],
            "duns": fixture_data["duns"],
            "uei": fixture_data["uei"],
        }
        recipient = Recipient(data, mock_usa_client)

        assert recipient._data["recipient_id"] == fixture_data["recipient_id"]
        assert recipient._data["name"] == fixture_data["name"]
        assert recipient._data["duns"] == fixture_data["duns"]
        assert recipient._data["uei"] == fixture_data["uei"]
        assert recipient._client is not None

    def test_init_with_string_id(self, mock_usa_client):
        """Test Recipient initialization with string recipient ID."""
        fixture_data = load_json_fixture("recipient_university.json")
        recipient_id = fixture_data["recipient_id"]
        recipient = Recipient(recipient_id, mock_usa_client)

        assert recipient._data["recipient_id"] == recipient_id
        assert recipient._client is not None

    def test_init_with_hash_field(self, mock_usa_client):
        """Test Recipient initialization when dict has recipient_hash instead of recipient_id."""
        fixture_data = load_json_fixture("recipient_university.json")
        data = {
            "recipient_hash": fixture_data["recipient_id"],
            "name": "Test Recipient",
        }
        recipient = Recipient(data, mock_usa_client)

        # Should normalize to recipient_id
        assert recipient._data["recipient_id"] == fixture_data["recipient_id"]
        assert (
            "recipient_hash" not in recipient._data
            or recipient._data.get("recipient_hash") == fixture_data["recipient_id"]
        )

    def test_init_with_invalid_type_raises_error(self, mock_usa_client):
        """Test that Recipient initialization with invalid type raises ValidationError."""
        with pytest.raises(
            ValidationError, match="Recipient expects dict or recipient_id/hash string"
        ):
            Recipient(123, mock_usa_client)

        with pytest.raises(ValidationError):
            Recipient([], mock_usa_client)

    def test_init_copies_data_dict(self, mock_usa_client):
        """Test that Recipient initialization copies the data dictionary."""
        fixture_data = load_json_fixture("recipient_university.json")
        original_data = {
            "recipient_id": fixture_data["recipient_id"],
            "name": "Test Recipient",
        }
        recipient = Recipient(original_data, mock_usa_client)

        # Modify original data
        original_data["new_field"] = "new_value"
        original_data["name"] = "Modified Name"

        # Recipient should not be affected
        assert "new_field" not in recipient._data
        assert recipient._data["name"] == "Test Recipient"

    def test_init_cleans_recipient_id(self, mock_usa_client):
        """Test that recipient IDs are cleaned during initialization."""
        fixture_data = load_json_fixture("recipient_university.json")
        base_id = fixture_data["recipient_id"].split("-")[
            0
        ]  # Get base part before dash

        # Test with list-annotated ID
        data = {"recipient_id": f"{base_id}-['C','R']"}
        recipient = Recipient(data, mock_usa_client)
        assert recipient._data["recipient_id"] == f"{base_id}-C"

        # Test with string ID
        recipient2 = Recipient("abc123-['P','C']", mock_usa_client)
        assert recipient2._data["recipient_id"] == "abc123-P"


class TestRecipientIdCleaning:
    """Test recipient ID cleaning functionality."""

    def test_clean_recipient_id_normal(self):
        """Test cleaning normal recipient IDs."""
        assert Recipient._clean_recipient_id("abc123-C") == "abc123-C"
        assert Recipient._clean_recipient_id("xyz789-P") == "xyz789-P"

    def test_clean_recipient_id_with_list_annotation(self):
        """Test cleaning IDs with list annotations like abc123-['C','R']."""
        assert Recipient._clean_recipient_id("abc123-['C','R']") == "abc123-C"
        assert Recipient._clean_recipient_id("xyz789-['P','C']") == "xyz789-P"

    def test_clean_recipient_id_with_single_annotation(self):
        """Test cleaning IDs with single annotations like abc123-['C']."""
        assert Recipient._clean_recipient_id("abc123-['C']") == "abc123-C"
        assert Recipient._clean_recipient_id("xyz789-['P']") == "xyz789-P"

    def test_clean_recipient_id_with_trailing_slash(self):
        """Test cleaning IDs with trailing slashes."""
        assert Recipient._clean_recipient_id("abc123-C/") == "abc123-C"
        assert Recipient._clean_recipient_id("xyz789-['P']/") == "xyz789-P"

    def test_clean_recipient_id_with_whitespace(self):
        """Test cleaning IDs with extra whitespace."""
        assert Recipient._clean_recipient_id("  abc123-C  ") == "abc123-C"
        assert Recipient._clean_recipient_id("xyz789-[ 'P' , 'C' ]") == "xyz789-P"

    def test_clean_recipient_id_empty_list(self):
        """Test handling of empty annotation lists."""
        # Empty brackets don't match the regex pattern, so they're returned as-is
        assert Recipient._clean_recipient_id("abc123-[]") == "abc123-[]"

    def test_clean_recipient_id_non_string(self):
        """Test defensive handling of non-string IDs."""
        # Should return input unchanged if not a string
        assert Recipient._clean_recipient_id(None) is None
        assert Recipient._clean_recipient_id(123) == 123


class TestRecipientProperties:
    """Test recipient property accessors."""

    @pytest.fixture
    def recipient_data(self):
        """Load recipient fixture data."""
        return load_json_fixture("recipient_university.json")

    def test_recipient_id_property(self, mock_usa_client, recipient_data):
        """Test recipient_id property with various data."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert recipient.recipient_id == recipient_data["recipient_id"]

        # Test with recipient_hash
        data_with_hash = {"recipient_hash": "test-hash-123"}
        recipient2 = Recipient(data_with_hash, mock_usa_client)
        assert recipient2.recipient_id == "test-hash-123"

    def test_name_property(self, mock_usa_client, recipient_data):
        """Test name property with titlecase formatting."""
        # Use actual fixture data
        recipient = Recipient(recipient_data, mock_usa_client)
        assert recipient.name == contracts_titlecase(recipient_data["name"])

    def test_name_property_with_none(self, mock_usa_client):
        """Test name property when value is None."""
        # Create recipient with no name field
        recipient = Recipient({"recipient_id": "test-123"}, mock_usa_client)

        # Mock the endpoint to return data with no name
        mock_usa_client.set_response(
            "/recipient/test-123/",
            {"recipient_id": "test-123"},  # No name field
        )

        assert recipient.name is None

    def test_duns_property(self, mock_usa_client, recipient_data):
        """Test DUNS property."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert recipient.duns == recipient_data["duns"]

    def test_uei_property(self, mock_usa_client, recipient_data):
        """Test UEI property."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert recipient.uei == recipient_data["uei"]

    def test_business_types_property(self, mock_usa_client, recipient_data):
        """Test business_types property returns list."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert recipient.business_types == recipient_data["business_types"]

    def test_repr(self, mock_usa_client, recipient_data):
        """Test string representation."""
        recipient = Recipient(recipient_data, mock_usa_client)
        repr_str = repr(recipient)
        assert "Recipient" in repr_str
        assert contracts_titlecase(recipient_data["name"]) in repr_str
        assert recipient_data["recipient_id"] in repr_str

    def test_repr_with_no_name(self, mock_usa_client):
        """Test repr when name is None."""
        # Create recipient with minimal data
        recipient = Recipient({"recipient_id": "test-123"}, mock_usa_client)

        # Mock endpoint to return no name
        mock_usa_client.set_response(
            "/recipient/test-123/", {"recipient_id": "test-123"}
        )

        repr_str = repr(recipient)
        assert "?" in repr_str
        assert "test-123" in repr_str


class TestRecipientParentRelationships:
    """Test recipient parent relationship functionality."""

    @pytest.fixture
    def recipient_data(self):
        """Load recipient fixture data."""
        return load_json_fixture("recipient_university.json")

    def test_parent_property(self, mock_usa_client, recipient_data):
        """Test parent property creates Recipient instance."""
        recipient = Recipient(recipient_data, mock_usa_client)
        
        if recipient_data.get("parent_id") and recipient_data.get("parent_id") == recipient_data.get("recipient_id"):
            # If parent_id is same as recipient_id, parent should be None
            assert recipient.parent is None
        else:
            parent = recipient.parent
            assert isinstance(parent, Recipient)
            assert parent._data["recipient_id"] == recipient_data["parent_id"]
            assert parent._data["name"] == recipient_data["parent_name"]
            assert parent._data["duns"] == recipient_data["parent_duns"]
            assert parent._data["uei"] == recipient_data["parent_uei"]

    def test_parent_property_with_no_parent(self, mock_usa_client):
        """Test parent property when no parent exists."""
        # Create recipient with no parent_id
        data = {"recipient_id": "test-123", "name": "Test Recipient"}
        recipient = Recipient(data, mock_usa_client)

        # Mock endpoint to return data with no parent_id
        mock_usa_client.set_response("/recipient/test-123/", data)

        assert recipient.parent is None

    def test_parent_property_ignores_same_parentage(self, mock_usa_client):
        """Sometimes a recipient lists itself as a parent - ignore this."""
        data = {"recipient_id": "test-123", "name": "Test Recipient", "parent_id": "test-123"}
        recipient = Recipient(data, mock_usa_client)

        assert recipient.parent is None


    def test_parents_property(self, mock_usa_client, recipient_data):
        """Test parents property returns list of Recipients."""
        recipient = Recipient(recipient_data, mock_usa_client)

        parents = recipient.parents

        assert len(parents) == len(recipient_data["parents"])
        assert all(isinstance(p, Recipient) for p in parents)
        assert (
            parents[0]._data["recipient_id"]
            == recipient_data["parents"][0]["parent_id"]
        )
        assert parents[0]._data["name"] == recipient_data["parents"][0]["parent_name"]

    def test_parents_property_ignores_same_parentage(self, mock_usa_client):
        """Sometimes a recipient lists itself as a parent - ignore these."""
        parents = [{"parent_id": "test-123", "parent_name": "Test Parent"},{"parent_id": "test-456", "parent_name": "Another Parent"}]
        data = {"recipient_id": "test-123", "name": "Test Recipient", "parents": parents}
        recipient = Recipient(data, mock_usa_client)

        assert len(recipient.parents) == 1

    def test_parents_property_empty(self, mock_usa_client):
        """Test parents property when no parents data."""
        data = {"recipient_id": "test-123", "name": "Test Recipient"}
        recipient = Recipient(data, mock_usa_client)

        assert recipient.parents == []


class TestRecipientLocation:
    """Test recipient location functionality."""

    @pytest.fixture
    def recipient_data(self):
        """Load recipient fixture data."""
        return load_json_fixture("recipient_university.json")

    def test_location_property(self, mock_usa_client, recipient_data):
        """Test location property creates Location instance."""
        recipient = Recipient(recipient_data, mock_usa_client)

        location = recipient.location

        assert isinstance(location, Location)
        assert location._data["city_name"] == recipient_data["location"]["city_name"]
        assert location._data["state_code"] == recipient_data["location"]["state_code"]
        assert (
            location._data["country_code"] == recipient_data["location"]["country_code"]
        )
        assert location._data["zip"] == recipient_data["location"]["zip"]

    def test_location_property_with_no_location(self, mock_usa_client):
        """Test location when no location data."""
        data = {"recipient_id": "test-123", "name": "Test Recipient"}
        recipient = Recipient(data, mock_usa_client)

        # Mock endpoint to return data with no location
        mock_usa_client.set_response("/recipient/test-123/", data)

        assert recipient.location is None


class TestRecipientTotals:
    """Test recipient total amount properties."""

    @pytest.fixture
    def recipient_data(self):
        """Load recipient fixture data."""
        return load_json_fixture("recipient_university.json")

    def test_total_transaction_amount(self, mock_usa_client, recipient_data):
        """Test total transaction amount property."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert_decimal_equal(
            recipient.total_transaction_amount,
            recipient_data["total_transaction_amount"]
        )

    def test_total_transactions(self, mock_usa_client, recipient_data):
        """Test total transactions property."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert recipient.total_transactions == recipient_data["total_transactions"]

    def test_total_face_value_loan_amount(self, mock_usa_client, recipient_data):
        """Test total face value loan amount."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert (
            recipient.total_face_value_loan_amount
            == recipient_data["total_face_value_loan_amount"]
        )

    def test_total_face_value_loan_transactions(self, mock_usa_client, recipient_data):
        """Test total face value loan transactions."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert (
            recipient.total_face_value_loan_transactions
            == recipient_data["total_face_value_loan_transactions"]
        )


class TestRecipientLazyLoading:
    """Test recipient lazy loading functionality."""

    @pytest.fixture
    def recipient_data(self):
        """Load recipient fixture data."""
        return load_json_fixture("recipient_university.json")

    def test_lazy_load_on_missing_field(self, mock_usa_client, recipient_data):
        """Test that accessing missing fields triggers lazy load."""
        recipient_id = recipient_data["recipient_id"]

        # Set up the mock response for recipient GET
        mock_usa_client.set_fixture_response(
            f"/recipient/{recipient_id}/", "recipient_university"
        )

        # Create recipient with minimal data (no name field)
        recipient = Recipient({"recipient_id": recipient_id}, mock_usa_client)

        # Verify no API calls yet
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 0

        # Access a field that should trigger lazy load
        name = recipient.name

        # Verify the value from fixture
        assert name == contracts_titlecase(recipient_data["name"])

        # Verify the endpoint was called
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 1

    def test_lazy_load_caches_data(self, mock_usa_client, recipient_data):
        """Test that lazy loading only happens once."""
        recipient_id = recipient_data["recipient_id"]

        # Set up the mock response
        mock_usa_client.set_fixture_response(
            f"/recipient/{recipient_id}/", "recipient_university"
        )

        # Create recipient with minimal data
        recipient = Recipient({"recipient_id": recipient_id}, mock_usa_client)

        # First access triggers lazy load
        duns1 = recipient.duns
        assert duns1 == recipient_data["duns"]
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 1

        # Second access should use cached data
        duns2 = recipient.duns
        assert duns2 == recipient_data["duns"]
        # Should still be 1 - no additional API call
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 1

        # Access different field - should still use cached data
        uei = recipient.uei
        assert uei == recipient_data["uei"]
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 1

    def test_lazy_load_updates_existing_data(self, mock_usa_client, recipient_data):
        """Test that lazy load merges with existing data."""
        recipient_id = recipient_data["recipient_id"]

        # Set up the mock response
        mock_usa_client.set_fixture_response(
            f"/recipient/{recipient_id}/", "recipient_university"
        )

        # Create recipient with some initial data
        initial_data = {
            "recipient_id": recipient_id,
            "existing_field": "original_value",
        }
        recipient = Recipient(initial_data, mock_usa_client)

        # Access a field that triggers lazy load
        name = recipient.name

        # Check that new data was loaded
        assert name == contracts_titlecase(recipient_data["name"])

        # Check that original field is preserved
        assert recipient._data["existing_field"] == "original_value"
        assert recipient._data["recipient_id"] == recipient_id

        # Check that other fields were loaded too
        assert recipient._data["duns"] == recipient_data["duns"]

    def test_lazy_load_handles_fetch_failure(self, mock_usa_client):
        """Test graceful handling when fetch fails."""
        recipient_id = "bad-recipient-id"

        # Set up error response
        mock_usa_client.set_error_response(
            f"/recipient/{recipient_id}/", 404, "Not Found", "Recipient not found"
        )

        # Create recipient
        recipient = Recipient({"recipient_id": recipient_id}, mock_usa_client)

        # Access should handle error gracefully
        name = recipient.name
        assert name is None

        # Should have tried to fetch
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 1

        # Should not try again on subsequent access
        name2 = recipient.name
        assert name2 is None
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 1

    def test_no_lazy_load_for_existing_fields(self, mock_usa_client, recipient_data):
        """Test no API call when field already exists."""
        recipient_id = recipient_data["recipient_id"]

        # Create recipient with all data already present
        data = {
            "recipient_id": recipient_id,
            "name": "Existing Name",
            "duns": "existing_duns",
            "uei": "existing_uei",
        }
        recipient = Recipient(data, mock_usa_client)

        # Access existing fields should not trigger API call
        assert recipient._lazy_get("name") == "Existing Name"
        assert recipient._lazy_get("duns") == "existing_duns"

        # Verify no API calls were made
        assert mock_usa_client.get_request_count() == 0
