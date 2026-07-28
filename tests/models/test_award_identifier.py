"""Tests for parsing generated award identifiers.

The identifiers below are real values taken from the fixture data, so the parser
is pinned against the shapes USASpending actually emits rather than invented ones.
"""

from __future__ import annotations

import pytest

from usaspending.models.award_identifier import parse_award_identifier


class TestParseAwardIdentifier:
    """Extracting the PIID, FAIN or URI embedded in a generated award ID."""

    @pytest.mark.parametrize(
        ("generated_id", "expected"),
        [
            # Contract awards: CONT_AWD_<piid>_<agency>_<parent_piid>_<parent_agency>
            ("CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-", "80GSFC18C0008"),
            ("CONT_AWD_NAS1510000_8000_-NONE-_-NONE-", "NAS1510000"),
            ("CONT_AWD_80NM0018F0615_8000_80NM0018D0004_8000", "80NM0018F0615"),
            ("CONT_AWD_NNJ06TA25C_8000_-NONE-_-NONE-", "NNJ06TA25C"),
            ("CONT_AWD_NNM07AB03C_8000_-NONE-_-NONE-", "NNM07AB03C"),
            ("CONT_AWD_NNS16AA07T_8000_NNS14AA17B_8000", "NNS16AA07T"),
            # Contract IDVs: CONT_IDV_<piid>_<agency>
            ("CONT_IDV_80JSC019C0012_8000", "80JSC019C0012"),
            ("CONT_IDV_NNJ09GA02B_8000", "NNJ09GA02B"),
            ("CONT_IDV_NNK10LB00B_8000", "NNK10LB00B"),
            ("CONT_IDV_NNK14MA75C_8000", "NNK14MA75C"),
            # Non-aggregated assistance: ASST_NON_<fain>_<agency>
            ("ASST_NON_NNM11AA01A_080", "NNM11AA01A"),
            ("ASST_NON_P268K115150_091", "P268K115150"),
            ("ASST_NON_NNX16AO69A_080", "NNX16AO69A"),
            ("ASST_NON_NNX12AD05A_080", "NNX12AD05A"),
            ("ASST_NON_NNG11HP16A_080", "NNG11HP16A"),
            # Aggregated assistance: ASST_AGG_<uri>_<agency>
            ("ASST_AGG_1020FA_-NONE-", "1020FA"),
            ("ASST_AGG_15CA35050692501_1251", "15CA35050692501"),
        ],
    )
    def test_extracts_the_embedded_identifier(self, generated_id, expected):
        """Each recognized prefix yields the third segment."""
        assert parse_award_identifier(generated_id) == expected

    @pytest.mark.parametrize(
        "generated_id",
        [
            "CONT_IDV_-NONE-_8000",
            "CONT_AWD_-NONE-_8000_-NONE-_-NONE-",
            "ASST_NON_-NONE-_080",
            "ASST_AGG_-NONE-_1251",
        ],
    )
    def test_placeholder_identifier_yields_none(self, generated_id):
        """USASpending's "-NONE-" placeholder is not an identifier."""
        assert parse_award_identifier(generated_id) is None

    @pytest.mark.parametrize(
        "generated_id",
        [
            None,
            "",
            "CONT_AWD",  # prefix only
            "CONT_AWD_12345",  # fewer segments than the prefix requires
            "CONT_IDV_PIID_8000_EXTRA_EXTRA",  # more segments than it requires
            "INVALID_FORMAT_12345_8000",  # unrecognized prefix
            "NOT_A_VALID_ID",
            "cont_awd_piid_8000_x_y",  # prefixes are case sensitive
            "CONT_AWD__8000_-NONE-_-NONE-",  # empty identifier segment
        ],
    )
    def test_missing_or_malformed_input_yields_none(self, generated_id):
        """A prefix must be recognized and bring the exact segment count it implies."""
        assert parse_award_identifier(generated_id) is None

    def test_segment_count_is_exact_not_a_minimum(self):
        """A CONT_IDV ID padded to a CONT_AWD length is rejected, not truncated."""
        assert parse_award_identifier("CONT_IDV_PIID_8000") == "PIID"
        assert parse_award_identifier("CONT_IDV_PIID_8000_X_Y") is None
