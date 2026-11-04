"""Response-backed subaward summary model tests."""

from decimal import Decimal

import pytest

from tests.utils import assert_decimal_equal
from usaspending.models.subaward_summary import SubAwardSummary


def test_recorded_summary(load_fixture):
    row = load_fixture("spending_by_subaward_grouped.json")["results"][0]
    summary = SubAwardSummary(row)

    assert summary.award_id == row["award_id"]
    assert summary.award_generated_internal_id == row["award_generated_internal_id"]
    assert summary.generated_unique_award_id == row["award_generated_internal_id"]
    assert summary.subaward_count == row["subaward_count"]
    assert_decimal_equal(summary.subaward_obligation, row["subaward_obligation"])
    assert_decimal_equal(summary.award_obligation, row["award_obligation"])
    assert_decimal_equal(summary.subaward_to_award_ratio, row["subaward_to_award_ratio"])
    assert summary.raw == row


def test_nullable_ids_and_zero_totals():
    summary = SubAwardSummary(
        {
            "award_id": None,
            "award_generated_internal_id": None,
            "subaward_count": 0,
            "subaward_obligation": 0.0,
            "award_obligation": 0.0,
            "subaward_to_award_ratio": 0.0,
        }
    )
    assert summary.award_id is None
    assert summary.award_generated_internal_id is None
    assert summary.subaward_count == 0
    assert summary.subaward_obligation == Decimal("0.00")
    assert summary.award_obligation == Decimal("0.00")
    assert summary.subaward_to_award_ratio == Decimal("0.0")


def test_ratio_preserves_server_precision_without_recalculating():
    summary = SubAwardSummary(
        {
            "award_obligation": -1.0,
            "subaward_obligation": -0.25,
            "subaward_to_award_ratio": 0.251762,
        }
    )
    assert summary.award_obligation == Decimal("-1.00")
    assert summary.subaward_obligation == Decimal("-0.25")
    assert summary.subaward_to_award_ratio == Decimal("0.251762")
    assert str(summary.subaward_to_award_ratio) == "0.251762"


@pytest.mark.parametrize("value", [None, "not a number", {}])
def test_malformed_ratio_is_none(value):
    # The other fields use to_int/to_decimal, whose tolerance tests/utils covers.
    assert SubAwardSummary({"subaward_to_award_ratio": value}).subaward_to_award_ratio is None
