"""Response-backed subaward summary model tests."""

from decimal import Decimal

import pytest

from usaspending.models.subaward_summary import SubAwardSummary


def test_recorded_summary(load_fixture):
    row = load_fixture("spending_by_subaward_grouped.json")["results"][0]
    summary = SubAwardSummary(row)

    assert summary.award_id == "80NSSC20M0027"
    assert summary.award_generated_internal_id == "ASST_NON_80NSSC20M0027_080"
    assert summary.subaward_count == 792
    assert summary.subaward_obligation == Decimal("41584357.42")
    assert summary.award_obligation == Decimal("6756953.00")
    assert summary.subaward_to_award_ratio == Decimal("6.15430615")
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
def test_malformed_manual_rows_keep_tolerant_numeric_coercion(value):
    summary = SubAwardSummary(
        dict.fromkeys(
            [
                "subaward_count",
                "subaward_obligation",
                "award_obligation",
                "subaward_to_award_ratio",
            ],
            value,
        )
    )
    assert summary.subaward_count is None
    assert summary.subaward_obligation is None
    assert summary.award_obligation is None
    assert summary.subaward_to_award_ratio is None
