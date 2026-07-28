"""Tests for TASAgenciesQuery, the root level of the TAS filter tree."""

from __future__ import annotations

import pytest

from usaspending.models.agency import Agency
from usaspending.queries.tas_agencies_query import TASAgenciesQuery

ENDPOINT = "/references/filter_tree/tas/"


@pytest.fixture
def query(mock_usa_client, load_fixture):
    mock_usa_client.set_response(ENDPOINT, load_fixture("tas_agencies.json"))
    return TASAgenciesQuery(mock_usa_client)


class TestTASAgenciesQuery:
    """The root level takes no scope and still fetches."""

    def test_fetches_and_builds_agencies(self, query):
        """A row's id and description become the Agency's code and name."""
        agencies = query.all()

        assert len(agencies) == 91
        assert all(isinstance(a, Agency) for a in agencies)

        nasa = next(a for a in agencies if a.code == "080")
        assert "National Aeronautics and Space Administration" in nasa.name
        assert nasa.toptier_code == "080"

    def test_root_level_is_not_treated_as_unscoped(self, query, mock_usa_client):
        """An empty scope must not short-circuit to an empty result set.

        The base skips the request when a scope's values are empty. The root has
        no values at all, which is a different thing, and ``all(())`` is True.
        """
        assert len(query) == 91
        assert mock_usa_client.get_request_count() == 1

    def test_fetches_once_across_filters(self, query, mock_usa_client):
        """The level is fetched once and shared with every clone."""
        len(query)
        query.code("080").all()
        query.description("agriculture").all()

        assert mock_usa_client.get_request_count() == 1

    def test_code_filter_matches_the_agency_code(self, query):
        """CODE_KEY is overridden, because Agency.id is not the agency code."""
        match = query.code("080").first()

        assert match is not None
        assert match.code == "080"

    def test_codes_filter_matches_several(self, query):
        """Multiple codes select multiple agencies."""
        codes = {a.code for a in query.codes("080", "012")}

        assert codes == {"080", "012"}

    def test_description_filter_searches_the_name(self, query):
        """KEYWORD_FIELDS is overridden, because Agency has no description."""
        matches = query.description("national aeronautics").all()

        assert matches
        assert all("National Aeronautics" in a.name for a in matches)

    def test_tas_count_is_retained_on_raw(self, query):
        """The node's TAS count stays reachable even though Agency has no field for it."""
        nasa = query.code("080").first()

        assert nasa.raw.get("_tas_count") is not None

    def test_empty_results(self, mock_usa_client):
        """An empty level yields an empty list, not an error."""
        mock_usa_client.set_response(ENDPOINT, {"results": []})

        assert TASAgenciesQuery(mock_usa_client).all() == []

    def test_repr_omits_the_absent_scope(self, mock_usa_client):
        """A scope-less level must not render a doubled space."""
        assert repr(TASAgenciesQuery(mock_usa_client)) == "<TASAgenciesQuery [not fetched]>"
