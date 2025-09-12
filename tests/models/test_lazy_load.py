# tests/models/test_lazy_load.py
import pytest
from unittest.mock import Mock
from src.usaspending.models.lazy_record import LazyRecord
from tests.mocks.mock_client import MockUSASpendingClient


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

    def test_lazy_get_returns_existing_value_without_calling_ensure_details(
        self, test_lazy_record
    ):
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

    def test_lazy_get_returns_default_when_key_not_found_after_fetch(
        self, test_lazy_record
    ):
        """Test _lazy_get returns default when key is not found even after fetching details."""
        result = test_lazy_record._lazy_get(
            "nonexistent_field", default="default_value"
        )

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
        test_lazy_record.get_value.assert_called_once_with(
            ["any_field"], default="any_default"
        )
        assert result == "mocked_value"

    def test_lazy_get_with_multiple_keys(self, test_lazy_record):
        """Test _lazy_get works with multiple keys."""
        result = test_lazy_record._lazy_get(
            "nonexistent", "existing_field", default="fallback"
        )

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

    def test_lazy_get_only_none_values_trigger_fetch(self, test_lazy_record):
        """Test that only None values (missing keys) trigger fetch."""
        # Add None value to data
        test_lazy_record._data["none_value"] = None

        # Mock _ensure_details to track calls
        original_ensure = test_lazy_record._ensure_details
        test_lazy_record._ensure_details = Mock(side_effect=original_ensure)

        # None value should trigger fetch
        result = test_lazy_record._lazy_get("none_value", default="fallback")
        test_lazy_record._ensure_details.assert_called_once()

        # Should return default since "none_value" not in _fetch_details response
        assert result == "fallback"

    def test_lazy_get_multiple_keys_first_falsy_second_truthy(self, mock_client):
        """Test multiple keys where first is falsy, second is truthy."""
        record = LazyRecord({"empty": "", "truthy": "good_value"}, mock_client)

        # Should return the first non-None value found
        # The loop continues until it finds a non-None value
        result = record._lazy_get("empty", "truthy")
        assert result == ""
        assert record._details_fetched is False

    def test_lazy_get_with_none_value_triggers_load(self, mock_client):
        """Test that _lazy_get triggers loading when value is None."""
        
        class TestModel(LazyRecord):
            def _fetch_details(self):
                return {"test_field": "loaded_value"}
        
        # Create model with None value
        model = TestModel({"test_field": None}, mock_client)
        
        # Access field - should trigger lazy load
        result = model._lazy_get("test_field", default="default")
        
        # Assert: details were fetched and correct value returned
        assert model._details_fetched
        assert result == "loaded_value"
