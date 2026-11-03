"""Bounded live checks for grouped summaries and their award-count endpoint."""

import pytest

pytestmark = pytest.mark.integration


def test_two_small_pages_match_one_larger_page(client):
    query = (
        client.awards.subaward_summary()
        .grants()
        .agency("National Aeronautics and Space Administration")
        .fiscal_year(2024)
        .limit(6)
    )
    split = query.page_size(3).all()
    combined = query.page_size(6).all()

    assert len(split) == len(combined) == 6
    assert [row.raw for row in split] == [row.raw for row in combined]
    assert len({row.award_generated_internal_id for row in split}) == 6


@pytest.mark.parametrize("award_kind", ["contract", "grant"])
def test_generated_id_count_matches_bounded_rows(client, load_fixture, award_kind):
    generated_id = load_fixture(f"awards/{award_kind}.json")["generated_unique_award_id"]
    query = client.awards.subaward_summary().contracts().grants().award_id(generated_id)

    rows = query.limit(2).all()

    assert query.count() == len(rows) == 1
    assert rows[0].award_generated_internal_id == generated_id
