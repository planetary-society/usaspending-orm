"""Tests for Recipient model functionality."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from tests.conftest import load_json_fixture
from tests.utils import assert_decimal_equal
from usaspending.exceptions import ValidationError
from usaspending.models.location import Location
from usaspending.models.recipient import Recipient
from usaspending.utils.textcase import titlecase_name


class TestSearchResultKeys:
    """The flat keys an award search result carries are read by this model.

    Three of the five were already read here and two were not, so `Award` had to
    translate its payload before handing it over. Reading all five here makes this
    the one owner of the mapping.
    """

    def test_every_flat_key_is_read(self, mock_usa_client):
        """Each flat spelling an award search result sends reaches its property."""
        recipient = Recipient(
            {
                "recipient_id": "abc123-C",
                "Recipient Name": "ACME CORPORATION",
                "Recipient DUNS Number": "123456789",
                "Recipient UEI": "UEIXYZ123",
                "Recipient Location": {"city_name": "PASADENA", "state_code": "CA"},
            },
            mock_usa_client,
        )

        assert recipient.name == "Acme Corporation"
        assert recipient.duns == "123456789"
        assert recipient.uei == "UEIXYZ123"
        assert recipient.location is not None
        assert recipient.location.state_code == "CA"

    def test_the_nested_spellings_still_win(self, mock_usa_client):
        """A detail response's own keys take precedence over the flat ones."""
        recipient = Recipient(
            {
                "recipient_uei": "NESTED_UEI",
                "Recipient UEI": "FLAT_UEI",
                "location": {"state_code": "TX"},
                "Recipient Location": {"state_code": "CA"},
            },
            mock_usa_client,
        )

        assert recipient.uei == "NESTED_UEI"
        assert recipient.location.state_code == "TX"

    def test_from_search_result_takes_only_its_own_keys(self, mock_usa_client):
        """The projection is scoped, so `raw` describes a recipient and not an award.

        It must also copy rather than alias, since this is a lazy record whose
        `raw` is replaced in place when a detail fetch fires.
        """
        award_data = {
            "recipient_id": "abc123-C",
            "Recipient Name": "ACME",
            "Award ID": "CONT_AWD_1",
            "Start Date": "2020-01-01",
        }

        recipient = Recipient._from_search_result(award_data, mock_usa_client)

        assert set(recipient.raw) == {"recipient_id", "Recipient Name"}

        award_data.clear()
        assert recipient.name == "Acme"


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
        with pytest.raises(ValidationError, match="Recipient expects dict or string, got int"):
            Recipient(123, mock_usa_client)

        with pytest.raises(ValidationError, match="Recipient expects dict or string, got list"):
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
        base_id = fixture_data["recipient_id"].split("-")[0]  # Get base part before dash

        # Test with list-annotated ID: the first level listed wins
        data = {"recipient_id": f"{base_id}-['C','R']"}
        recipient = Recipient(data, mock_usa_client)
        assert recipient._data["recipient_id"] == f"{base_id}-C"

        # Test with string ID
        recipient2 = Recipient("abc123-['P','C']", mock_usa_client)
        assert recipient2._data["recipient_id"] == "abc123-P"

        # Test with problematic case
        recipient3 = Recipient("bc396b9b-bdab-f7b7-b1a8-1409da07fdc0-C", mock_usa_client)
        assert recipient3._data["recipient_id"] == "bc396b9b-bdab-f7b7-b1a8-1409da07fdc0-C"


class TestRecipientIdCleaning:
    """Construction normalizes the recipient ID.

    The normalizer's own edge cases live in tests/utils/test_validations.py; what
    matters here is that Recipient applies it, so a model and a query built from
    the same raw ID address the same entity.
    """

    def test_construction_normalizes_a_level_list(self, mock_usa_client):
        """A level list collapses to the single level the API will be asked for."""
        recipient = Recipient({"recipient_id": "abc123-['C','R']"}, mock_usa_client)

        assert recipient.recipient_id == "abc123-C"

    def test_construction_leaves_a_normal_id_alone(self, mock_usa_client):
        """An already-normal ID passes through untouched."""
        recipient = Recipient({"recipient_id": "abc123-C"}, mock_usa_client)

        assert recipient.recipient_id == "abc123-C"

    def test_construction_agrees_with_the_query_path(self, mock_usa_client):
        """The two paths that used to disagree now resolve identically."""
        from usaspending.queries.recipient_query import RecipientQuery

        raw = "abc123-['C','R']"
        recipient = Recipient({"recipient_id": raw}, mock_usa_client)

        assert recipient.recipient_id == RecipientQuery(mock_usa_client)._clean_resource_id(raw)


class TestRecipientLevel:
    """recipient_level says which level of the hierarchy a record describes.

    Normalization picks one level from a multi-level ID, so without this the
    caller would have to parse the ID string to learn which record they hold.
    """

    def test_level_from_a_detail_payload(self, mock_usa_client):
        """The API reports the level; it is not parsed from the ID."""
        recipient = Recipient({"recipient_id": "abc123-C", "recipient_level": "C"}, mock_usa_client)

        assert recipient.recipient_level == "C"

    def test_level_reflects_the_record_actually_fetched(self, mock_usa_client):
        """A multi-level ID collapses, and the level matches what came back."""
        mock_usa_client.set_response(
            "/recipient/abc123-C/",
            {"recipient_id": "abc123-C", "recipient_level": "C", "name": "ACME"},
        )
        recipient = Recipient({"recipient_id": "abc123-['C','R']"}, mock_usa_client)

        assert recipient.recipient_id == "abc123-C"
        assert recipient.recipient_level == "C"

    def test_an_explicit_suffix_selects_that_level(self, mock_usa_client):
        """An ID given with a suffix is used as-is, which is how a caller opts in to -R."""
        mock_usa_client.set_response(
            "/recipient/abc123-R/",
            {"recipient_id": "abc123-R", "recipient_level": "R", "name": "ACME"},
        )
        recipient = Recipient({"recipient_id": "abc123-R"}, mock_usa_client)

        assert recipient.recipient_id == "abc123-R"
        assert recipient.recipient_level == "R"

    def test_absent_level_is_none(self, mock_usa_client):
        """Not every payload reports it."""
        recipient = Recipient({"recipient_id": "abc123-C"}, mock_usa_client)
        recipient._details_fetched = True

        assert recipient.recipient_level is None


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
        assert recipient.name == titlecase_name(recipient_data["name"])

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

    def test_alternate_names_property(self, mock_usa_client, recipient_data):
        """Test alternate_names property returns list with titlecase."""
        recipient = Recipient(recipient_data, mock_usa_client)
        expected_names = [
            titlecase_name(name) for name in recipient_data.get("alternate_names", [])
        ]
        assert recipient.alternate_names == expected_names

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
        assert titlecase_name(recipient_data["name"]) in repr_str
        assert recipient_data["recipient_id"] in repr_str

    def test_repr_with_no_name(self, mock_usa_client):
        """Test repr when name is None."""
        # Create recipient with minimal data
        recipient = Recipient({"recipient_id": "test-123"}, mock_usa_client)

        # Mock endpoint to return no name
        mock_usa_client.set_response("/recipient/test-123/", {"recipient_id": "test-123"})

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

        if recipient_data.get("parent_id") and recipient_data.get(
            "parent_id"
        ) == recipient_data.get("recipient_id"):
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
        data = {
            "recipient_id": "test-123",
            "name": "Test Recipient",
            "parent_id": "test-123",
        }
        recipient = Recipient(data, mock_usa_client)

        assert recipient.parent is None

    def test_parents_property(self, mock_usa_client, recipient_data):
        """Test parents property returns list of Recipients."""
        recipient = Recipient(recipient_data, mock_usa_client)

        parents = recipient.parents

        assert len(parents) == len(recipient_data["parents"])
        assert all(isinstance(p, Recipient) for p in parents)
        assert parents[0]._data["recipient_id"] == recipient_data["parents"][0]["parent_id"]
        assert parents[0]._data["name"] == recipient_data["parents"][0]["parent_name"]

    def test_parents_property_ignores_same_parentage(self, mock_usa_client):
        """Sometimes a recipient lists itself as a parent - ignore these."""
        parents = [
            {"parent_id": "test-123", "parent_name": "Test Parent"},
            {"parent_id": "test-456", "parent_name": "Another Parent"},
        ]
        data = {
            "recipient_id": "test-123",
            "name": "Test Recipient",
            "parents": parents,
        }
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
        assert location._data["country_code"] == recipient_data["location"]["country_code"]
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
            recipient_data["total_transaction_amount"],
        )

    def test_total_transactions(self, mock_usa_client, recipient_data):
        """Test total transactions property."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert recipient.total_transactions == recipient_data["total_transactions"]

    def test_total_face_value_loan_amount(self, mock_usa_client, recipient_data):
        """Test total face value loan amount."""
        recipient = Recipient(recipient_data, mock_usa_client)
        assert (
            recipient.total_face_value_loan_amount == recipient_data["total_face_value_loan_amount"]
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
        mock_usa_client.set_fixture_response(f"/recipient/{recipient_id}/", "recipient_university")

        # Create recipient with minimal data (no name field)
        recipient = Recipient({"recipient_id": recipient_id}, mock_usa_client)

        # Verify no API calls yet
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 0

        # Access a field that should trigger lazy load
        name = recipient.name

        # Verify the value from fixture
        assert name == titlecase_name(recipient_data["name"])

        # Verify the endpoint was called
        assert mock_usa_client.get_request_count(f"/recipient/{recipient_id}/") == 1

    def test_lazy_load_caches_data(self, mock_usa_client, recipient_data):
        """Test that lazy loading only happens once."""
        recipient_id = recipient_data["recipient_id"]

        # Set up the mock response
        mock_usa_client.set_fixture_response(f"/recipient/{recipient_id}/", "recipient_university")

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
        mock_usa_client.set_fixture_response(f"/recipient/{recipient_id}/", "recipient_university")

        # Create recipient with some initial data
        initial_data = {
            "recipient_id": recipient_id,
            "existing_field": "original_value",
        }
        recipient = Recipient(initial_data, mock_usa_client)

        # Access a field that triggers lazy load
        name = recipient.name

        # Check that new data was loaded
        assert name == titlecase_name(recipient_data["name"])

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


class TestLazyLoadingFixes:
    """Test lazy loading bug fixes."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.mock_client = Mock()
        self.mock_client._closed = False  # Mark client as open for lazy loading
        self.mock_client._make_request.return_value = {
            "name": "Full Recipient Data",
            "recipient_id": "test-123",
            "parents": [
                {
                    "parent_id": "parent-456",
                    "parent_name": "Parent Recipient",
                    "parent_duns": "123456789",
                    "parent_uei": "ABC123DEF",
                }
            ],
            "business_types": ["nonprofit", "small_business"],
        }

    def test_parents_lazy_loading_with_missing_key(self):
        """Test that parents property triggers lazy loading when key is missing."""
        # Create recipient without parents data
        recipient = Recipient({"recipient_id": "test-123"}, client=self.mock_client)

        # Access parents property - should trigger lazy load
        parents = recipient.parents

        # Assert: API was called
        self.mock_client._make_request.assert_called_once()

        # Assert: parent objects were created
        assert len(parents) == 1
        assert parents[0].recipient_id == "parent-456"
        assert parents[0].name == "Parent Recipient"

    def test_parents_lazy_loading_with_empty_list(self):
        """Test that parents property still works with empty list in initial data."""
        # Create recipient with empty parents list
        recipient = Recipient({"recipient_id": "test-123", "parents": []}, client=self.mock_client)

        # Access parents property - should NOT trigger lazy load since key exists
        parents = recipient.parents

        # Assert: API was NOT called (key exists, even if empty)
        self.mock_client._make_request.assert_not_called()

        # Assert: empty list returned
        assert len(parents) == 0

    def test_business_types_lazy_loading_with_missing_key(self):
        """Test that business_types triggers lazy loading when key is missing."""
        # Create recipient without business_types data
        recipient = Recipient({"recipient_id": "test-123"}, client=self.mock_client)

        # Access business_types property - should trigger lazy load
        business_types = recipient.business_types

        # Assert: API was called
        self.mock_client._make_request.assert_called_once()

        # Assert: correct data returned
        assert business_types == ["nonprofit", "small_business"]


class TestRecipientSpendingIntegration:
    """Test RecipientSpending integration with fixes."""

    def test_recipient_spending_from_spending_query_data(self):
        """Test creating RecipientSpending from spending query results."""
        mock_client = Mock()
        mock_client._closed = False  # Mark client as open for lazy loading
        mock_client._make_request.return_value = {
            "name": "ASSOCIATION OF UNIVERSITIES FOR RESEARCH IN ASTRONOMY, INC.",
            "recipient_id": "bc396b9b-bdab-f7b7-b1a8-1409da07fdc0-C",
            "parents": [
                {
                    "parent_id": "4c2d8769-6506-a0d1-dbb6-ceb88e11e281-P",
                    "parent_name": "PARENT AURA",
                }
            ],
            "business_types": ["nonprofit"],
        }

        # Data from spending by recipient query (with list suffix)
        spending_data = {
            "amount": 12345678.90,
            "recipient_id": "bc396b9b-bdab-f7b7-b1a8-1409da07fdc0-['C']",
            "name": "ASSOCIATION OF UNIVERSITIES FOR RESEARCH IN ASTRONOMY, INC.",
            "code": "101460871",
            "uei": "W1NBN156CYF9",
            "total_outlays": 9876543.21,
        }

        # Create RecipientSpending object
        from usaspending.models.recipient_spending import RecipientSpending

        recipient_spending = RecipientSpending(spending_data, client=mock_client)

        # Assert: recipient_id was cleaned
        assert recipient_spending.recipient_id == "bc396b9b-bdab-f7b7-b1a8-1409da07fdc0-C"

        # Assert: name from initial data
        assert (
            recipient_spending.name == "Association of Universities for Research in Astronomy, Inc."
        )

        # Assert: amount property works (returns Decimal)
        from decimal import Decimal

        assert recipient_spending.amount == Decimal("12345678.90")

        # Access parents property - should trigger lazy load
        parents = recipient_spending.parents

        # Assert: API was called for lazy load
        mock_client._make_request.assert_called_once()

        # Assert: parent was created
        assert len(parents) == 1
        assert parents[0].recipient_id == "4c2d8769-6506-a0d1-dbb6-ceb88e11e281-P"


class TestCircularReferenceProtection:
    """Test protection against circular references."""

    def test_circular_parent_references(self):
        """Test that circular parent references don't cause infinite loops."""
        call_count = 0

        def mock_make_request(method, endpoint):
            nonlocal call_count
            call_count += 1

            if call_count > 5:
                pytest.fail("Too many API calls - possible infinite loop")

            if "recipient-A" in endpoint:
                return {
                    "name": "Recipient A",
                    "recipient_id": "recipient-A",
                    "parents": [{"parent_id": "recipient-B", "parent_name": "Recipient B"}],
                }
            elif "recipient-B" in endpoint:
                return {
                    "name": "Recipient B",
                    "recipient_id": "recipient-B",
                    "parents": [{"parent_id": "recipient-A", "parent_name": "Recipient A"}],
                }
            else:
                return {"name": "Unknown", "recipient_id": "unknown", "parents": []}

        mock_client = Mock()
        mock_client._closed = False  # Mark client as open for lazy loading
        mock_client._make_request.side_effect = mock_make_request

        # Create recipient A
        recipient_a = Recipient({"recipient_id": "recipient-A"}, client=mock_client)

        # Get parents of A (includes B)
        parents_a = recipient_a.parents
        assert len(parents_a) == 1

        parent_b = parents_a[0]
        assert parent_b.recipient_id == "recipient-B"

        # Get parents of B (includes A) - should not cause infinite loop
        parents_b = parent_b.parents
        assert len(parents_b) == 1

        back_to_a = parents_b[0]
        assert back_to_a.recipient_id == "recipient-A"

        # This should be a different object, not the same one
        assert back_to_a is not recipient_a

        # Total calls should be reasonable (2 for A and B)
        assert call_count <= 3


class TestRecipientParentsIsolation:
    """Each read of `parents` hands back its own list.

    It was a cached_property building the list, so every caller received the same
    object and one caller's ``pop()`` or ``sort()`` changed what every later
    reader saw, for the model's lifetime. The models inside are still shared,
    which is the pre-existing library stance.
    """

    def _recipient(self, mock_usa_client):
        recipient = Recipient(
            {
                "recipient_id": "a-C",
                "parents": [
                    {"parent_id": "p1-P", "parent_name": "P One"},
                    {"parent_id": "p2-P", "parent_name": "P Two"},
                ],
            },
            mock_usa_client,
        )
        recipient._details_fetched = True
        return recipient

    def test_mutating_the_returned_list_does_not_affect_later_reads(self, mock_usa_client):
        recipient = self._recipient(mock_usa_client)

        recipient.parents.pop()

        assert len(recipient.parents) == 2

    def test_each_read_returns_a_distinct_list(self, mock_usa_client):
        recipient = self._recipient(mock_usa_client)

        assert recipient.parents is not recipient.parents

    def test_the_models_are_built_once_and_shared(self, mock_usa_client):
        """The copy is of the list, not of its contents."""
        recipient = self._recipient(mock_usa_client)

        assert recipient.parents[0] is recipient.parents[0]
