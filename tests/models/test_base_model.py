"""Tests for BaseModel functionality."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from usaspending.models.base_model import BaseModel, ClientAwareModel


class TestBaseModelGetValue:
    """Test the get_value() method of BaseModel."""
    
    def test_get_value_returns_first_truthy_value(self):
        """Test that get_value returns the first truthy value from a list of keys."""
        data = {
            "key1": None,
            "key2": "value2", 
            "key3": "value3"
        }
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
    
    def test_get_value_returns_default_when_all_keys_falsy(self):
        """Test that get_value returns default when all keys have falsy values."""
        data = {
            "key1": None,
            "key2": "",
            "key3": 0
        }
        model = BaseModel(data)
        
        result = model.get_value(["key1", "key2", "key3"], default="default_value")
        assert result == "default_value"
    
    def test_get_value_returns_default_when_keys_missing(self):
        """Test that get_value returns default when keys don't exist."""
        data = {"existing_key": "value"}
        model = BaseModel(data)
        
        result = model.get_value(["missing1", "missing2"], default="default_value")
        assert result == "default_value"
    
    def test_get_value_returns_none_default_when_not_specified(self):
        """Test that get_value returns None when no default is specified and all values are falsy."""
        data = {"key1": None, "key2": ""}
        model = BaseModel(data)
        
        result = model.get_value(["key1", "key2", "missing_key"])
        assert result is None
    
    def test_get_value_skips_falsy_values(self):
        """Test that get_value skips falsy values and returns the first truthy value."""
        data = {
            "key1": None,
            "key2": "",        # Empty string (falsy)
            "key3": 0,         # Zero (falsy)
            "key4": False,     # False boolean (falsy)
            "key5": [],        # Empty list (falsy)
            "key6": {},        # Empty dict (falsy)
            "key7": "truthy_value"
        }
        model = BaseModel(data)
        
        # Should skip all falsy values and return the truthy one
        result = model.get_value(["key1", "key2", "key3", "key4", "key5", "key6", "key7"])
        assert result == "truthy_value"
        
        # When all values are falsy, should return default
        result = model.get_value(["key1", "key2", "key3"], default="default_value")
        assert result == "default_value"
    
    def test_get_value_with_mixed_existing_and_missing_keys(self):
        """Test get_value with a mix of existing and missing keys."""
        data = {
            "key2": "found_value",
            "key4": "another_value"
        }
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
            "float_key": 3.14
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
        data = {
            "key1": "first_value",
            "key2": "second_value",
            "key3": "third_value"
        }
        model = BaseModel(data)
        
        # Should return first_value (key1 comes first)
        result = model.get_value(["key1", "key2", "key3"])
        assert result == "first_value"
        
        # Should return second_value (key2 comes first in this list)
        result = model.get_value(["key2", "key1", "key3"])
        assert result == "second_value"
    
    def test_get_value_with_falsy_and_missing_keys(self):
        """Test get_value with a combination of falsy values and missing keys."""
        data = {
            "key1": None,
            "key2": "",
            "key4": "found_value"
        }
        model = BaseModel(data)
        
        # key1 exists but is None, key2 exists but is empty, key3 doesn't exist, key4 has a truthy value
        result = model.get_value(["key1", "key2", "key3", "key4"], default="default")
        assert result == "found_value"


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