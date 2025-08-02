"""Tests for Spending model functionality."""

from __future__ import annotations

from usaspending.models.spending import Spending


class TestSpendingInitialization:
    """Test Spending model initialization."""

    def test_init_with_dict_data(self, mock_usa_client):
        """Test Spending initialization with dictionary data."""
        data = {
            "id": 12345,
            "name": "Test Spending Record",
            "code": "TEST123",
            "amount": 1000000.50,
            "total_outlays": 950000.25,
            "category": "recipient",
            "spending_level": "transactions",
        }
        spending = Spending(data, mock_usa_client)

        assert spending._data["id"] == 12345
        assert spending._data["name"] == "Test Spending Record"
        assert spending._client is not None
        assert isinstance(spending, Spending)


class TestSpendingProperties:
    """Test spending properties."""

    def test_basic_properties(self, mock_usa_client):
        """Test basic spending properties."""
        data = {
            "id": 12345,
            "name": "Test Entity",
            "code": "TEST123",
            "amount": 1500000.75,
            "total_outlays": 1400000.50,
            "category": "recipient",
            "spending_level": "transactions",
        }
        spending = Spending(data, mock_usa_client)

        assert spending.id == 12345
        assert spending.name == "Test Entity"
        assert spending.code == "TEST123"
        assert spending.amount == 1500000.75
        assert spending.total_outlays == 1400000.50
        assert spending.category == "recipient"
        assert spending.spending_level == "transactions"

    def test_properties_with_none_values(self, mock_usa_client):
        """Test properties when values are None."""
        data = {
            "id": None,
            "name": None,
            "code": None,
            "amount": None,
            "total_outlays": None,
        }
        spending = Spending(data, mock_usa_client)

        assert spending.id is None
        assert spending.name is None
        assert spending.code is None
        assert spending.amount is None
        assert spending.total_outlays is None

    def test_repr(self, mock_usa_client):
        """Test string representation of Spending."""
        data = {"name": "Test Recipient", "amount": 1234567.89}
        spending = Spending(data, mock_usa_client)

        repr_str = repr(spending)
        assert "Test Recipient" in repr_str
        assert "1,234,567.89" in repr_str

    def test_repr_with_none_values(self, mock_usa_client):
        """Test string representation with None values."""
        data = {}
        spending = Spending(data, mock_usa_client)

        repr_str = repr(spending)
        assert "Unknown" in repr_str
        assert "0.00" in repr_str
