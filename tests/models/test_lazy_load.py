# tests/models/test_lazy_load.py
from unittest.mock import Mock

import pytest
import requests

from tests.conftest import load_json_fixture
from tests.mocks.mock_client import MockUSASpendingClient
from usaspending.exceptions import DetachedInstanceError, HTTPError, RateLimitError
from usaspending.models.agency import Agency
from usaspending.models.lazy_record import LazyRecord
from usaspending.models.recipient import Recipient


class TestLazyRecord:
    """Test LazyRecord lazy loading behavior."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock USASpending client."""
        return MockUSASpendingClient()

    @pytest.fixture
    def test_lazy_record(self, mock_client):
        """Create a test LazyRecord subclass."""

        class TestRecord(LazyRecord):
            def _fetch_details(self):
                return {
                    "detail_field": "detail_value",
                    "existing_field": "updated_value",
                }

        return TestRecord(
            {"existing_field": "original_value", "empty_string_field": ""}, mock_client
        )

    def test_lazy_get_returns_existing_value_without_calling_ensure_details(self, test_lazy_record):
        """Test _lazy_get returns value already present in data without calling _ensure_details."""
        # Spy on _ensure_details to verify it's not called
        test_lazy_record._ensure_details = Mock()

        # Call _lazy_get for existing field
        result = test_lazy_record._lazy_get("existing_field")

        # Should return the existing value
        assert result == "original_value"

        # _ensure_details should not have been called
        test_lazy_record._ensure_details.assert_not_called()

        # _details_fetched should still be False
        assert test_lazy_record._details_fetched is False

        # Now ensure that an empty string field is not considered "missing"
        # i.e. only None or missing fields should trigger a fetch
        assert test_lazy_record._data["empty_string_field"] == ""
        test_lazy_record._lazy_get("empty_string_field")
        # assert result_empty == ""

        test_lazy_record._ensure_details.assert_not_called()

    def test_lazy_get_triggers_ensure_details_when_key_is_none_and_not_detailed_fetched(
        self, test_lazy_record
    ):
        """Test _lazy_get triggers _ensure_details() if requested key is None and _details_fetched is False."""
        # Spy on _ensure_details to verify it's called
        original_ensure_details = test_lazy_record._ensure_details
        test_lazy_record._ensure_details = Mock(side_effect=original_ensure_details)

        # Call _lazy_get for non-existing field
        result = test_lazy_record._lazy_get("detail_field")

        # Should return the value from fetched details
        assert result == "detail_value"

        # _ensure_details should have been called exactly once
        test_lazy_record._ensure_details.assert_called_once()

        # _details_fetched should now be True
        assert test_lazy_record._details_fetched is True

        # Access the same value again to ensure it uses cached data
        result_again = test_lazy_record._lazy_get("detail_field")

        assert result_again == result

        test_lazy_record._ensure_details.assert_called_once()

    def test_lazy_get_returns_default_when_key_not_found_after_fetch(self, test_lazy_record):
        """Test _lazy_get returns default when key is not found even after fetching details."""
        result = test_lazy_record._lazy_get("nonexistent_field", default="default_value")

        # Should return the default value
        assert result == "default_value"

        # Details should have been fetched
        assert test_lazy_record._details_fetched is True

    def test_lazy_get_uses_get_value_after_details_fetched(self, test_lazy_record):
        """Test _lazy_get uses get_value when _details_fetched is True."""
        # First trigger details fetch
        test_lazy_record._lazy_get("detail_field")

        # Spy on get_value
        test_lazy_record.get_value = Mock(return_value="mocked_value")

        # Call _lazy_get again
        result = test_lazy_record._lazy_get("any_field", default="any_default")

        # Should use get_value with the provided default
        # A tuple, not a list: _lazy_get passes its *keys through untouched, since
        # get_value takes any iterable of keys.
        test_lazy_record.get_value.assert_called_once_with(("any_field",), default="any_default")
        assert result == "mocked_value"

    def test_lazy_get_with_multiple_keys(self, test_lazy_record):
        """Test _lazy_get works with multiple keys."""
        result = test_lazy_record._lazy_get("nonexistent", "existing_field", default="fallback")

        # Should return the existing field value without fetching details
        assert result == "original_value"
        assert test_lazy_record._details_fetched is False

    def test_lazy_get_falsy_values_do_not_trigger_fetch(self, mock_client):
        """Test that falsy values (empty string, 0, False, []) do NOT trigger fetch."""

        class TestRecordFalsy(LazyRecord):
            def _fetch_details(self):
                return {"fetched": "should_not_be_called"}

        record = TestRecordFalsy(
            {"zero": 0, "false": False, "empty_list": [], "empty_string": ""},
            mock_client,
        )

        # Mock _ensure_details to verify it's not called
        record._ensure_details = Mock()

        # All falsy values should return as-is without triggering fetch
        assert record._lazy_get("zero") == 0
        assert record._lazy_get("false") is False
        assert record._lazy_get("empty_list") == []
        assert record._lazy_get("empty_string") == ""

        # _ensure_details should never have been called
        record._ensure_details.assert_not_called()
        assert record._details_fetched is False

    def test_ensure_details_early_return_when_already_fetched(self, test_lazy_record):
        """Test _ensure_details returns early if already fetched."""
        # First trigger fetch
        test_lazy_record._lazy_get("detail_field")
        assert test_lazy_record._details_fetched is True

        # Mock _fetch_details to verify it's not called again
        test_lazy_record._fetch_details = Mock()

        # Call _ensure_details directly
        test_lazy_record._ensure_details()

        # Should not call _fetch_details since already fetched
        test_lazy_record._fetch_details.assert_not_called()

    def test_ensure_details_handles_none_response(self, mock_client):
        """Test _ensure_details handles None response from _fetch_details."""

        class TestRecordNone(LazyRecord):
            def _fetch_details(self):
                return None

        record = TestRecordNone({"existing": "value"}, mock_client)

        # Should not crash when _fetch_details returns None
        record._ensure_details()
        assert record._details_fetched is True
        assert record._data == {"existing": "value"}  # Data unchanged

    def test_fetch_details_raises_not_implemented(self, mock_client):
        """Test _fetch_details raises NotImplementedError when not overridden."""
        record = LazyRecord({"test": "data"}, mock_client)

        with pytest.raises(NotImplementedError):
            record._fetch_details()

    def test_lazy_get_none_value_does_not_trigger_fetch(self, test_lazy_record):
        """Test that a key present with None value does NOT trigger fetch.

        When a key exists in _data but its value is None, this represents a
        legitimately null value from the API -- not missing data. The fetch
        should only be triggered when the key itself is absent.
        """
        # Add None value to data
        test_lazy_record._data["none_value"] = None

        # Mock _ensure_details to track calls
        test_lazy_record._ensure_details = Mock()

        # None value should NOT trigger fetch -- the key exists
        result = test_lazy_record._lazy_get("none_value", default="fallback")
        test_lazy_record._ensure_details.assert_not_called()

        # Should return default since value is None
        assert result == "fallback"
        assert test_lazy_record._details_fetched is False

    def test_lazy_get_multiple_keys_first_falsy_second_truthy(self, mock_client):
        """Test multiple keys where first is falsy, second is truthy."""
        record = LazyRecord({"empty": "", "truthy": "good_value"}, mock_client)

        # Should return the first non-None value found
        # The loop continues until it finds a non-None value
        result = record._lazy_get("empty", "truthy")
        assert result == ""
        assert record._details_fetched is False

    def test_lazy_get_with_none_value_returns_default_without_load(self, mock_client):
        """Test that _lazy_get returns default when key exists but value is None.

        A key present with None value means the API returned null for this field.
        This should NOT trigger a fetch -- the data is present, just null.
        """

        class TestModel(LazyRecord):
            def _fetch_details(self):
                return {"test_field": "loaded_value"}

        # Create model with None value
        model = TestModel({"test_field": None}, mock_client)

        # Mock _ensure_details to verify it's not called
        model._ensure_details = Mock()

        # Access field - should return default without triggering lazy load
        result = model._lazy_get("test_field", default="default")

        # Assert: details were NOT fetched, default returned
        model._ensure_details.assert_not_called()
        assert model._details_fetched is False
        assert result == "default"


class TestFailedFetchIsRetried:
    """Only the API's answer that a record is absent may be recorded as absent.

    `_ensure_details` latches on a return, so a model whose fetch reported a
    server error, a dropped connection or a closed session as absent data would
    answer None for every later read of every lazy property, for as long as it
    lived. Those all raise instead, leaving the flag unset so the next access
    tries again. A 404 or a rejected id still latches: asking again would not
    change the answer.
    """

    def test_agency_retries_after_a_server_error(self, mock_usa_client):
        """A 500 reaches the caller and leaves the agency ready to fetch again."""
        endpoint = "/agency/080/"
        mock_usa_client.set_error_response(endpoint, 500, error_message="Server Error")
        agency = Agency({"code": "080"}, mock_usa_client)

        with pytest.raises(HTTPError):
            _ = agency.name

        assert agency._details_fetched is False

        mock_usa_client.clear_error_response(endpoint)
        mock_usa_client.set_fixture_response(endpoint, "agency")

        assert agency.name == "National Aeronautics and Space Administration"
        assert agency._details_fetched is True
        assert mock_usa_client.get_request_count(endpoint) == 2

    def test_recipient_retries_after_a_server_error(self, mock_usa_client):
        """A 503 reaches the caller and leaves the recipient ready to fetch again."""
        fixture = load_json_fixture("recipient_university.json")
        recipient_id = fixture["recipient_id"]
        endpoint = f"/recipient/{recipient_id}/"
        mock_usa_client.set_error_response(endpoint, 503, error_message="Service Unavailable")
        recipient = Recipient({"recipient_id": recipient_id}, mock_usa_client)

        with pytest.raises(HTTPError):
            _ = recipient.uei

        assert recipient._details_fetched is False

        mock_usa_client.clear_error_response(endpoint)
        mock_usa_client.set_fixture_response(endpoint, "recipient_university")

        assert recipient.uei == fixture["uei"]
        assert recipient._details_fetched is True
        assert mock_usa_client.get_request_count(endpoint) == 2

    def test_a_rate_limited_recipient_does_not_latch(self, mock_usa_client):
        """A rate limit reaches the caller, whose option is to wait and ask again."""
        fixture = load_json_fixture("recipient_university.json")
        recipient_id = fixture["recipient_id"]
        endpoint = f"/recipient/{recipient_id}/"
        mock_usa_client.set_error_response(endpoint, 429, error_message="Rate limit exceeded")
        recipient = Recipient({"recipient_id": recipient_id}, mock_usa_client)

        with pytest.raises(RateLimitError):
            _ = recipient.uei

        assert recipient._details_fetched is False

        mock_usa_client.clear_error_response(endpoint)
        mock_usa_client.set_fixture_response(endpoint, "recipient_university")

        assert recipient.uei == fixture["uei"]
        assert mock_usa_client.get_request_count(endpoint) == 2

    def test_recipient_retries_after_a_dropped_connection(self, mock_usa_client, monkeypatch):
        """A request that never reached the API is not an answer about the record.

        The client re-raises the transport's own exception rather than wrapping
        it, so this arrives at the model as a `requests` error carrying no status.
        """
        fixture = load_json_fixture("recipient_university.json")
        recipient_id = fixture["recipient_id"]
        endpoint = f"/recipient/{recipient_id}/"
        mock_usa_client.set_fixture_response(endpoint, "recipient_university")
        recipient = Recipient({"recipient_id": recipient_id}, mock_usa_client)

        answer_request = mock_usa_client._make_request
        attempts = []

        def drop_the_first_connection(*args, **kwargs):
            attempts.append(args)
            if len(attempts) == 1:
                raise requests.exceptions.ConnectionError("connection reset by peer")
            return answer_request(*args, **kwargs)

        monkeypatch.setattr(mock_usa_client, "_make_request", drop_the_first_connection)

        with pytest.raises(requests.exceptions.ConnectionError):
            _ = recipient.uei

        assert recipient._details_fetched is False

        assert recipient.uei == fixture["uei"]
        assert recipient._details_fetched is True
        assert len(attempts) == 2

    def test_a_detached_agency_does_not_latch(self, mock_usa_client):
        """A closed session is the caller's to fix, so reattach() must still work."""
        agency = Agency({"code": "080"}, mock_usa_client)
        mock_usa_client.close()

        with pytest.raises(DetachedInstanceError):
            _ = agency.name

        assert agency._details_fetched is False

        new_client = MockUSASpendingClient()
        new_client.set_fixture_response("/agency/080/", "agency")
        agency.reattach(new_client)

        assert agency.name == "National Aeronautics and Space Administration"
        assert agency._details_fetched is True

    def test_a_not_found_agency_latches(self, mock_usa_client):
        """A 404 is the API's answer, so it stays absent data rather than an error."""
        endpoint = "/agency/999/"
        mock_usa_client.set_error_response(endpoint, 404, error_message="Agency not found")
        agency = Agency({"code": "999"}, mock_usa_client)

        assert agency.name is None
        assert agency._details_fetched is True

        assert agency.mission is None
        assert mock_usa_client.get_request_count(endpoint) == 1

    def test_a_rejected_recipient_id_latches(self, mock_usa_client):
        """A 400 is the API's verdict on the id, so it does not retry either."""
        endpoint = "/recipient/not-a-hash/"
        mock_usa_client.set_error_response(endpoint, 400, detail="Invalid recipient_id")
        recipient = Recipient({"recipient_id": "not-a-hash"}, mock_usa_client)

        assert recipient.name is None
        assert recipient._details_fetched is True

        assert recipient.uei is None
        assert mock_usa_client.get_request_count(endpoint) == 1

    def test_a_recipient_without_an_id_latches_without_a_request(self, mock_usa_client):
        """There is nothing to fetch with, so the model must not keep trying."""
        recipient = Recipient({"Recipient Name": "ACME CORPORATION"}, mock_usa_client)

        assert recipient.uei is None
        assert recipient._details_fetched is True
        assert mock_usa_client.get_request_count() == 0

        assert recipient.duns is None
        assert mock_usa_client.get_request_count() == 0
