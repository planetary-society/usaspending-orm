"""Parsing for the generated award identifiers USASpending assigns.

Every award carries a ``generated_unique_award_id``, built by USASpending and its
Broker systems from the award type, the awarding agency codes, and the award's
own identifier. That embedded identifier is the PIID, FAIN or URI a caller
actually recognizes, so it can be recovered without a second request.
"""

from __future__ import annotations

# Underscore-delimited segment count for each known prefix. The identifier is
# always the third segment:
#
#   CONT_AWD_<piid>_<agency>_<parent_piid>_<parent_agency>
#   CONT_IDV_<piid>_<agency>
#   ASST_NON_<fain>_<agency>
#   ASST_AGG_<uri>_<agency>
#
# The counts are exact rather than minimums: a mismatch means the ID does not
# have the shape its prefix claims, so no segment can be trusted to be the
# identifier.
_EXPECTED_SEGMENTS: dict[str, int] = {
    "CONT_AWD": 6,
    "CONT_IDV": 4,
    "ASST_NON": 4,
    "ASST_AGG": 4,
}

_IDENTIFIER_SEGMENT = 2

# USASpending writes this in place of a value it does not have, most often for
# the parent-award segments of a contract that has no parent.
_PLACEHOLDER = "-NONE-"


def parse_award_identifier(generated_unique_award_id: str | None) -> str | None:
    """Extract the PIID, FAIN or URI embedded in a generated award ID.

    Args:
        generated_unique_award_id: The award's ``generated_unique_award_id``,
            such as ``"CONT_AWD_NAS1510000_8000_-NONE-_-NONE-"``.

    Returns:
        Optional[str]: The embedded identifier, or None when the ID is missing,
        carries an unrecognized prefix, does not have the segment count its
        prefix requires, or holds a placeholder in the identifier position.

    Examples:
        >>> parse_award_identifier("CONT_IDV_NNK14MA75C_8000")
        'NNK14MA75C'
        >>> parse_award_identifier("ASST_NON_NNG11HP16A_080")
        'NNG11HP16A'
        >>> parse_award_identifier("CONT_AWD_-NONE-_8000_-NONE-_-NONE-") is None
        True
    """
    if not generated_unique_award_id:
        return None

    segments = generated_unique_award_id.split("_")
    if len(segments) <= _IDENTIFIER_SEGMENT:
        return None

    # An unrecognized prefix has no expected count, so the comparison fails and
    # the ID is rejected along with the malformed ones.
    prefix = "_".join(segments[:_IDENTIFIER_SEGMENT])
    if len(segments) != _EXPECTED_SEGMENTS.get(prefix, -1):
        return None

    identifier = segments[_IDENTIFIER_SEGMENT]
    if not identifier or identifier == _PLACEHOLDER:
        return None

    return identifier
