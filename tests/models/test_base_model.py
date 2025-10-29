"""Tests for BaseModel functionality."""

from __future__ import annotations

import pytest

from usaspending.models.base_model import BaseModel
from usaspending.exceptions import ValidationError


class TestBaseModelGetValue:
    """Test the get_value() method of BaseModel."""

    def test_get_value_returns_first_truthy_value(self):
        """Test that get_value returns the first truthy value from a list of keys."""
        data = {"key1": None, "key2": "value2", "key3": "value3"}
        model = BaseModel(data)

        result = model.get_value(["key1", "key2", "key3"])
        assert result == "value2"

    def test_get_value_with_single_key_as_string(self):
        """Test that get_value works with a single key passed as string."""
        data = {"key1": "value1"}
        model = BaseModel(data)

        result = model.get_value("key1")
        assert result == "value1"

    def test_get_value_with_single_key_as_list(self):
        """Test that get_value works with a single key passed as list."""
        data = {"key1": "value1"}
        model = BaseModel(data)

        result = model.get_value(["key1"])
        assert result == "value1"

    def test_get_value_does_not_return_default_when_all_keys_falsy(self):
        """Test that get_value doest not return default when all keys have falsy values."""
        data = {"key1": None, "key2": "", "key3": 0}
        model = BaseModel(data)

        result = model.get_value(["key1", "key2", "key3"], default="default_value")
        assert result == ""

    def test_get_value_returns_default_when_keys_missing(self):
        """Test that get_value returns default when keys don't exist."""
        data = {"existing_key": "value"}
        model = BaseModel(data)

        result = model.get_value(["missing1", "missing2"], default="default_value")
        assert result == "default_value"

    def test_get_value_returns_none_default_when_not_specified(self):
        """Test that get_value returns None when no default is specified and all values are None."""
        data = {"key1": None, "key2": None}
        model = BaseModel(data)

        result = model.get_value(["key1", "key2", "missing_key"])
        assert result is None

    def test_get_value_does_not_skip_falsy_values(self):
        """Test that get_value skips falsy values and returns the first truthy value."""
        data = {
            "key1": None,
            "key2": "",  # Empty string (falsy)
            "key3": 0,  # Zero (falsy)
            "key4": False,  # False boolean (falsy)
            "key5": [],  # Empty list (falsy)
            "key6": {},  # Empty dict (falsy)
            "key7": "truthy_value",
        }
        model = BaseModel(data)

        # Should skip all falsy values and return the truthy one
        result = model.get_value(
            ["key1", "key2", "key3", "key4", "key5", "key6", "key7"]
        )
        assert result == ""

        # False value should be returned
        result = model.get_value(["key3", "key7"])
        assert not result

        # Default only applies to missing or "None" values:
        data = {"key2": None}
        model = BaseModel(data)

        result = model.get_value(["key1", "key2"], default="default_value")
        assert result == "default_value"

    def test_get_value_with_mixed_existing_and_missing_keys(self):
        """Test get_value with a mix of existing and missing keys."""
        data = {"key2": "found_value", "key4": "another_value"}
        model = BaseModel(data)

        result = model.get_value(["missing1", "key2", "missing2", "key4"])
        assert result == "found_value"

    def test_get_value_raises_error_with_non_dict_data(self):
        """Test that get_value raises TypeError when _data is not a dict."""
        # BaseModel should handle this, but let's test the error condition
        model = BaseModel(None)  # This sets _data to {}
        model._data = "not_a_dict"  # Force non-dict data

        with pytest.raises(TypeError, match="Empty object data"):
            model.get_value(["key1"])

    def test_get_value_with_empty_keys_list(self):
        """Test get_value with an empty list of keys."""
        data = {"key1": "value1"}
        model = BaseModel(data)

        result = model.get_value([], default="default_value")
        assert result == "default_value"

    def test_get_value_with_complex_data_types(self):
        """Test get_value with complex data types as values."""
        nested_dict = {"nested": "value"}
        nested_list = [1, 2, 3]

        data = {
            "key1": None,
            "dict_key": nested_dict,
            "list_key": nested_list,
            "int_key": 42,
            "float_key": 3.14,
        }
        model = BaseModel(data)

        # Should return the nested dict
        result = model.get_value(["key1", "dict_key"])
        assert result == nested_dict

        # Should return the nested list
        result = model.get_value(["key1", "list_key"])
        assert result == nested_list

        # Should return the integer
        result = model.get_value(["key1", "int_key"])
        assert result == 42

        # Should return the float
        result = model.get_value(["key1", "float_key"])
        assert result == 3.14

    def test_get_value_key_order_matters(self):
        """Test that get_value respects the order of keys."""
        data = {"key1": "first_value", "key2": "second_value", "key3": "third_value"}
        model = BaseModel(data)

        # Should return first_value (key1 comes first)
        result = model.get_value(["key1", "key2", "key3"])
        assert result == "first_value"

        # Should return second_value (key2 comes first in this list)
        result = model.get_value(["key2", "key1", "key3"])
        assert result == "second_value"

    def test_get_value_with_falsy_and_missing_keys(self):
        """Test get_value with a combination of falsy values and missing keys."""
        data = {"key1": None, "key2": "", "key4": "found_value"}
        model = BaseModel(data)

        # key1 exists but is None, key2 exists but is empty, key3 doesn't exist, key4 has a truthy value
        result = model.get_value(["key1", "key2", "key3", "key4"], default="default")
        assert result == ""


class TestBaseModelOtherMethods:
    """Test other methods of BaseModel for completeness."""

    def test_raw_property(self):
        """Test that raw property returns the _data dict."""
        data = {"key": "value"}
        model = BaseModel(data)

        assert model.raw == data
        assert model.raw is model._data

    def test_to_dict_method(self):
        """Test that to_dict returns the _data dict."""
        data = {"key": "value"}
        model = BaseModel(data)

        assert model.to_dict() == data
        assert model.to_dict() is model._data

    def test_init_with_none_data(self):
        """Test BaseModel initialization with None data."""
        model = BaseModel(None)

        assert model._data == {}
        assert model.raw == {}
        assert model.to_dict() == {}

    def test_init_with_empty_data(self):
        """Test BaseModel initialization with empty dict."""
        model = BaseModel({})

        assert model._data == {}
        assert model.raw == {}
        assert model.to_dict() == {}


class TestBaseModelValidation:
    """Test the validate_init_data() method of BaseModel."""

    def test_validate_init_data_with_none_raises_error(self):
        """Test that validate_init_data raises ValidationError with None input."""
        with pytest.raises(ValidationError, match="Test data cannot be None"):
            BaseModel.validate_init_data(None, "Test")

    def test_validate_init_data_with_empty_string_raises_error(self):
        """Test that validate_init_data raises ValidationError with empty string when string ID allowed."""
        with pytest.raises(ValidationError, match="Test ID cannot be empty"):
            BaseModel.validate_init_data(
                "", "Test", id_field="test_id", allow_string_id=True
            )

    def test_validate_init_data_with_whitespace_string_raises_error(self):
        """Test that validate_init_data raises ValidationError with whitespace-only string."""
        with pytest.raises(ValidationError, match="Test ID cannot be empty"):
            BaseModel.validate_init_data(
                "   \t\n  ", "Test", id_field="test_id", allow_string_id=True
            )

    def test_validate_init_data_with_string_when_not_allowed_raises_error(self):
        """Test that validate_init_data raises ValidationError when string ID not allowed."""
        with pytest.raises(ValidationError, match="Test expects dict, got str"):
            BaseModel.validate_init_data("test-id", "Test", allow_string_id=False)

    def test_validate_init_data_with_invalid_type_raises_error(self):
        """Test that validate_init_data raises ValidationError with invalid types."""
        invalid_inputs = [
            ([], "list"),
            (123, "int"),
            (3.14, "float"),
            (True, "bool"),
            (set(), "set"),
        ]

        for invalid_input, expected_type in invalid_inputs:
            with pytest.raises(
                ValidationError,
                match=f"Test expects dict or string, got {expected_type}",
            ):
                BaseModel.validate_init_data(
                    invalid_input, "Test", id_field="test_id", allow_string_id=True
                )

    def test_validate_init_data_with_valid_dict_returns_copy(self):
        """Test that validate_init_data returns a copy of valid dict input."""
        original_data = {"key": "value", "other": 123}
        result = BaseModel.validate_init_data(original_data, "Test")

        assert result == original_data
        assert result is not original_data  # Should be a copy

        # Modify original to verify it's a copy
        original_data["new_key"] = "new_value"
        assert "new_key" not in result

    def test_validate_init_data_with_valid_string_id_creates_dict(self):
        """Test that validate_init_data converts string ID to dict when allowed."""
        result = BaseModel.validate_init_data(
            "test-123", "Test", id_field="test_id", allow_string_id=True
        )

        assert result == {"test_id": "test-123"}
        assert isinstance(result, dict)

    def test_validate_init_data_without_id_field_raises_error(self):
        """Test that validate_init_data raises error when string provided but no id_field specified."""
        with pytest.raises(ValidationError, match="Test expects dict, got str"):
            BaseModel.validate_init_data("test-123", "Test", allow_string_id=True)

    def test_validate_init_data_with_empty_dict_returns_copy(self):
        """Test that validate_init_data handles empty dict correctly."""
        result = BaseModel.validate_init_data({}, "Test")

        assert result == {}
        assert isinstance(result, dict)

    def test_validate_init_data_error_messages_are_descriptive(self):
        """Test that validate_init_data provides helpful error messages."""
        # Test None error message
        with pytest.raises(
            ValidationError,
            match=r"Recipient data cannot be None.*API or caching issue",
        ):
            BaseModel.validate_init_data(None, "Recipient")

        # Test empty string error message
        with pytest.raises(
            ValidationError, match="Award ID cannot be empty or whitespace"
        ):
            BaseModel.validate_init_data(
                "", "Award", id_field="award_id", allow_string_id=True
            )

        # Test type mismatch error message
        with pytest.raises(ValidationError, match="Agency expects dict, got list"):
            BaseModel.validate_init_data([], "Agency")

    def test_validate_init_data_preserves_dict_contents(self):
        """Test that validate_init_data preserves all dict contents including None values."""
        original_data = {
            "id": "test-123",
            "name": "Test Name",
            "optional_field": None,
            "empty_list": [],
            "empty_dict": {},
            "zero": 0,
            "false": False,
        }

        result = BaseModel.validate_init_data(original_data, "Test")

        assert result == original_data
        assert all(key in result for key in original_data.keys())
        assert result["optional_field"] is None
        assert result["empty_list"] == []
        assert result["empty_dict"] == {}
        assert result["zero"] == 0
        assert result["false"] is False

    def test_validate_init_data_with_different_model_names(self):
        """Test that validate_init_data uses correct model name in error messages."""
        test_cases = [
            ("Recipient", "Recipient data cannot be None"),
            ("Award", "Award data cannot be None"),
            ("Agency", "Agency data cannot be None"),
            ("CustomModel", "CustomModel data cannot be None"),
        ]

        for model_name, expected_message in test_cases:
            with pytest.raises(ValidationError, match=expected_message):
                BaseModel.validate_init_data(None, model_name)

    def test_validate_init_data_string_id_with_special_characters(self):
        """Test that validate_init_data handles string IDs with special characters."""
        special_ids = [
            "abc123-def456",
            "test_id_with_underscores",
            "id.with.dots",
            "id@with@symbols",
            "id with spaces",  # This should work - whitespace validation is only for empty/whitespace-only
            "urn:uuid:12345678-1234-5678-9012-123456789abc",
        ]

        for test_id in special_ids:
            result = BaseModel.validate_init_data(
                test_id, "Test", id_field="test_id", allow_string_id=True
            )
            assert result == {"test_id": test_id}
