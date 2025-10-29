"""Tests for StateSpending model."""

from __future__ import annotations

import pytest
from decimal import Decimal

from usaspending.models.state_spending import StateSpending


class TestStateSpending:
    """Test StateSpending model functionality."""

    @pytest.fixture
    def state_fixture_data(self, load_fixture):
        """Load state spending fixture."""
        data = load_fixture("spending_by_state.json")
        return data["results"][0]

    def test_state_spending_properties(self, state_fixture_data, mock_usa_client):
        """Test StateSpending model properties match fixture data."""
        spending = StateSpending(state_fixture_data, mock_usa_client)

        # Test base properties match fixture
        assert spending.id == state_fixture_data.get("id")
        assert spending.code == state_fixture_data["code"]
        assert spending.name == state_fixture_data["name"]
        assert spending.amount == Decimal(str(state_fixture_data["amount"]))
        assert spending.total_outlays == state_fixture_data.get("total_outlays")

        # Test state-specific properties derived from fixture data
        assert spending.state_code == state_fixture_data["code"]
        assert spending.state_name == state_fixture_data["name"]

    def test_state_spending_repr(self, state_fixture_data, mock_usa_client):
        """Test StateSpending string representation."""
        spending = StateSpending(state_fixture_data, mock_usa_client)

        # Build expected repr from fixture data
        name = state_fixture_data["name"]
        amount = Decimal(str(state_fixture_data["amount"]))
        expected_repr = f"<StateSpending {name}: ${amount:,.2f}>"

        assert repr(spending) == expected_repr
