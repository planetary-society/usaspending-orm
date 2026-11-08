"""Read-only live check that subaward counts honor the complete search scope."""

import pytest

pytestmark = pytest.mark.integration


def test_filtered_subaward_count_matches_search(client, load_fixture):
    award_id = load_fixture("awards/contract.json")["generated_unique_award_id"]
    query = client.subawards.search().contracts().award_id(award_id)
    assert query.count() > 0

    # This 2018 award has no subawards in FY2008; the unfiltered count cannot answer.
    filtered = query.fiscal_year(2008).limit(2)
    assert filtered.count() == len(filtered.all()) == 0
