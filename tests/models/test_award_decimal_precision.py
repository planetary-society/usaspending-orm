"""Tests for Award model Decimal precision behavior."""

from __future__ import annotations

from decimal import Decimal
from usaspending.models import Award
from tests.utils import decimal_equal, assert_decimal_equal


class TestAwardDecimalPrecision:
    """Test Award model Decimal precision behavior."""

    def test_total_obligation_preserves_precision(self, mock_usa_client):
        """Test that total_obligation maintains precise decimal values."""
        # Use a value that would lose precision as a float
        precise_amount = "172213419.67"
        data = {
            "generated_unique_award_id": "TEST_AWARD_123",
            "total_obligation": precise_amount,
        }

        award = Award(data, mock_usa_client)
        result = award.total_obligation

        # Should be exactly the same as the original value
        assert isinstance(result, Decimal)
        assert result == Decimal(precise_amount)
        assert str(result) == precise_amount

    def test_decimal_arithmetic_accuracy(self, mock_usa_client):
        """Test that Decimal arithmetic remains accurate."""
        data = {
            "generated_unique_award_id": "TEST_AWARD_123",
            "total_obligation": "100.33",
            "covid19_obligations": "50.67",
        }

        award = Award(data, mock_usa_client)

        # Test arithmetic operations
        total = award.total_obligation + award.covid19_obligations
        expected = Decimal("151.00")

        assert isinstance(total, Decimal)
        assert total == expected

    def test_large_monetary_values_precision(self, mock_usa_client):
        """Test precision with large monetary values common in government contracts."""
        large_amount = "2770845719.63"  # From IDV fixture
        data = {
            "generated_unique_award_id": "TEST_AWARD_LARGE",
            "total_obligation": large_amount,
        }

        award = Award(data, mock_usa_client)
        result = award.total_obligation

        assert isinstance(result, Decimal)
        assert str(result) == large_amount

        # Test that precision is maintained in calculations
        doubled = result * Decimal("2")
        expected = Decimal("5541691439.26")
        assert doubled == expected

    def test_zero_default_values(self, mock_usa_client):
        """Test that zero default values are proper Decimal objects."""
        data = {"generated_unique_award_id": "TEST_AWARD_ZERO"}
        award = Award(data, mock_usa_client)

        # These properties should return Decimal('0.00') for missing values
        assert award.covid19_obligations == Decimal("0.00")
        assert award.covid19_outlays == Decimal("0.00")
        assert award.infrastructure_obligations == Decimal("0.00")
        assert award.infrastructure_outlays == Decimal("0.00")
        assert award.total_obligation == Decimal("0.00")
        assert award.award_amount == Decimal("0.00")

    def test_none_values_remain_none(self, mock_usa_client):
        """Test that optional monetary properties remain None when not provided."""
        data = {"generated_unique_award_id": "TEST_AWARD_NONE"}
        award = Award(data, mock_usa_client)

        # These optional properties should return None for missing values
        assert award.total_subaward_amount is None
        assert award.total_account_outlay is None
        assert award.total_account_obligation is None
        assert award.total_outlay is None

    def test_rounding_behavior(self, mock_usa_client):
        """Test that values are properly quantized to 2 decimal places."""
        # Test value with more than 2 decimal places
        data = {
            "generated_unique_award_id": "TEST_AWARD_ROUNDING",
            "total_obligation": "100.999",  # Should round to 101.00
        }

        award = Award(data, mock_usa_client)
        result = award.total_obligation

        assert isinstance(result, Decimal)
        assert result == Decimal("101.00")
        assert str(result) == "101.00"

    def test_string_number_conversion(self, mock_usa_client):
        """Test conversion from various string number formats."""
        test_cases = [
            ("1000", Decimal("1000.00")),
            ("1000.0", Decimal("1000.00")),
            ("1000.50", Decimal("1000.50")),
            ("0.01", Decimal("0.01")),
        ]

        for input_value, expected in test_cases:
            data = {
                "generated_unique_award_id": f"TEST_AWARD_{input_value}",
                "total_obligation": input_value,
            }

            award = Award(data, mock_usa_client)
            result = award.total_obligation

            assert isinstance(result, Decimal)
            assert result == expected, f"Failed for input {input_value}"

    def test_comparison_with_float_fixture_values(self, mock_usa_client):
        """Test that our Decimal helper correctly compares with float fixture values."""
        float_value = 172213419.67
        data = {
            "generated_unique_award_id": "TEST_COMPARISON",
            "total_obligation": str(float_value),
        }

        award = Award(data, mock_usa_client)
        result = award.total_obligation

        # This should work with our decimal_equal helper
        assert decimal_equal(result, float_value)
        assert_decimal_equal(result, float_value)

    def test_edge_cases(self, mock_usa_client):
        """Test edge cases for Decimal conversion."""
        edge_cases = [
            ("0", Decimal("0.00")),
            ("0.00", Decimal("0.00")),
            ("-100.50", Decimal("-100.50")),  # Negative values
        ]

        for input_value, expected in edge_cases:
            data = {
                "generated_unique_award_id": f"TEST_EDGE_{input_value}",
                "total_obligation": input_value,
            }

            award = Award(data, mock_usa_client)
            result = award.total_obligation

            assert isinstance(result, Decimal)
            assert result == expected, f"Failed for edge case {input_value}"
