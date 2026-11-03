"""Tests for deterministic payload helpers."""

from __future__ import annotations

from usaspending.utils.payloads import canonical_order


def test_canonical_order_keeps_generator_values_when_unsortable() -> None:
    """A generator of incomparable values falls back to its original order intact."""
    values = ["B", 1, "A"]

    assert canonical_order(value for value in values) == values
