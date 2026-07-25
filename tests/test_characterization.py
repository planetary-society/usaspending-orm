"""Characterization tests pinning behavior the refactor must not change.

This file covers only behavior that the rest of the suite does **not** already
pin. Where existing tests already cover something, they are named here instead
of being duplicated, because a behavior pinned in two places is a behavior that
can be changed in one and contradicted in the other.

Already covered elsewhere, deliberately not repeated here:

* Absent-key money values, **changed in 0.8.0** from ``Decimal("0.00")`` to
  ``None`` so that an absent figure is distinguishable from a reported zero --
  ``tests/models/test_award_decimal_precision.py`` (the six Award properties,
  both the absent and reported-zero cases) and
  ``tests/models/test_award_account.py`` (the same, plus the ``__repr__`` guard
  that keeps a missing amount rendering as ``$0.00``).
* ``Location.zip5`` and ``Location.district``, **changed in 0.8.0** from ``""``
  to ``None`` to match their declared ``Optional[str]`` --
  ``tests/models/test_location.py``.
* Direct-GET finders raising ``HTTPError`` on 404 --
  ``tests/resources/test_award_resource.py::test_get_award_api_error_propagates``
  and ``tests/resources/test_agency_resource.py::test_get_agency_api_error_propagates``.
* ``SpendingSearch.count()`` honoring ``limit()`` --
  ``tests/queries/test_spending_search_count.py::TestSpendingSearchCountWithLimits``.
* The deprecation warning on constructing the legacy agency searches, and the
  model-side recipient-ID cleaner --
  ``tests/queries/test_agencies_search.py`` and
  ``tests/models/test_recipient.py::TestRecipientIdCleaning``.

Where a later phase intends to change a behavior below, the docstring says so.
"""

from __future__ import annotations

import warnings

import pytest

from tests.mocks import MockUSASpendingClient
from usaspending.models.award import Award
from usaspending.models.contract import Contract
from usaspending.models.grant import Grant
from usaspending.models.loan import Loan
from usaspending.models.recipient import Recipient
from usaspending.models.subaward import SubAward
from usaspending.queries.awarding_agencies_search import AwardingAgenciesSearch
from usaspending.queries.funding_agencies_search import FundingAgenciesSearch
from usaspending.queries.recipient_query import RecipientQuery


def _award_detail_endpoint(award_id: str) -> str:
    """Return the mock endpoint for a single award detail request."""
    return MockUSASpendingClient.Endpoints.AWARD_DETAIL.format(award_id=award_id)


class TestLoanCfdaNumberOverride:
    """Loan.cfda_number deliberately overrides Grant's multi-tier resolution.

    Grant resolves primary_cfda_info -> cfda_info[0] -> cfda_number, while Loan
    reads the flat cfda_number field directly. Phase 3 removes Loan's redundant
    overrides, and deleting this one would silently change which value loans
    report, so the divergence is pinned here.
    """

    @pytest.fixture
    def conflicting_data(self, loan_fixture_data):
        """A real loan record extended so the two resolutions disagree.

        The live fixture carries neither field, so the conflict has to be
        synthesized, but it is layered onto the real record rather than a stub
        so the surrounding shape (including ``category: "loans"``) is genuine.
        """
        return {
            **loan_fixture_data,
            "primary_cfda_info": {"cfda_number": "99.999"},
            "cfda_number": "10.001",
        }

    def test_loan_reads_flat_cfda_number(self, mock_usa_client, conflicting_data):
        loan = Loan(conflicting_data, mock_usa_client)

        assert loan.cfda_number == "10.001"

    def test_grant_prefers_nested_primary_cfda_info(self, mock_usa_client, conflicting_data):
        """The contrasting Grant behavior, to show the two genuinely differ."""
        grant = Grant(conflicting_data, mock_usa_client)

        assert grant.cfda_number == "99.999"


class TestAwardSubtypeUpgradeOnLazyLoad:
    """A bare Award upgrades its class once lazy loading reveals the award type.

    Award._fetch_details reassigns self.__class__ through award_factory. Nothing
    in the suite covered this, so any change to the mechanism would silently
    downgrade ID-only awards and parent_award to a base Award. The plan keeps
    the mechanism and relies on these tests as its guard.
    """

    @pytest.fixture
    def award_id(self, contract_fixture_data):
        return contract_fixture_data["generated_unique_award_id"]

    @pytest.fixture
    def mocked_detail(self, mock_usa_client, contract_fixture_data, award_id):
        mock_usa_client.set_response(_award_detail_endpoint(award_id), contract_fixture_data)
        return mock_usa_client

    @pytest.mark.parametrize(
        "trigger",
        [
            pytest.param(lambda award: award.fetch_all_details(), id="fetch_all_details"),
            pytest.param(lambda award: award.description, id="property_access"),
        ],
    )
    def test_award_upgrades_to_contract(
        self, mocked_detail, contract_fixture_data, award_id, trigger
    ):
        award = Award({"generated_unique_award_id": award_id}, mocked_detail)
        assert type(award) is Award, "An ID-only award should start as the base class"

        trigger(award)

        assert type(award) is Contract
        assert award.piid == contract_fixture_data["piid"]

    def test_subaward_parent_award_upgrades(self, mocked_detail, contract_fixture_data, award_id):
        """SubAward.parent_award builds a bare Award with no finder involved."""
        subaward = SubAward({"prime_award_generated_internal_id": award_id}, mocked_detail)

        parent = subaward.parent_award
        assert type(parent) is Award

        parent.fetch_all_details()

        assert type(parent) is Contract
        assert parent.piid == contract_fixture_data["piid"]


class TestAwardIdentifierEmptyString:
    """Award.award_identifier returns "" rather than None when unknown.

    The parsing itself lives in tests/models/test_award_identifier.py, so what
    is pinned here is the public property's empty-string contract. Phase 4 left
    it alone deliberately: the property is annotated ``-> str``, so unlike
    ``Location.zip5`` there was no Optional annotation to reconcile it with.
    """

    def test_award_identifier_is_empty_string_when_unknown(self, mock_usa_client):
        award = Award({"generated_unique_award_id": "CONT_AWD_EMPTY"}, mock_usa_client)
        award._details_fetched = True

        assert award.award_identifier == ""


class TestDeprecatedAgencySearchCloning:
    """The legacy agency searches must not re-warn on every chained call.

    Their hand-written _clone() passes warn=False. Phase 2 consolidates those
    clones, and losing the flag would emit a DeprecationWarning per filter call
    on two public classes.
    """

    @pytest.mark.parametrize(
        "search_class",
        [AwardingAgenciesSearch, FundingAgenciesSearch],
    )
    def test_chaining_does_not_rewarn(self, mock_usa_client, search_class):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            search = search_class(mock_usa_client, warn=False)
            # Each of these clones the query builder.
            search.name("Test").limit(5).page_size(10)

        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert deprecations == []

    @pytest.mark.parametrize(
        "search_class,expected_agency_type",
        [
            (AwardingAgenciesSearch, "awarding"),
            (FundingAgenciesSearch, "funding"),
        ],
    )
    def test_clone_preserves_agency_type(self, mock_usa_client, search_class, expected_agency_type):
        clone = search_class(mock_usa_client, warn=False).limit(3)

        assert clone._agency_type == expected_agency_type


class TestCountIgnoresDefaultResultLimit:
    """count() reports the true total, never the default fetch limit.

    config.default_result_limit exists to stop unbounded *fetches*. Letting it
    reach a count would silently report 10,000 (the default) for any larger
    result set, and callers have no way to tell a real total from a capped one.

    SpendingSearch always had its own counting loop and so was unaffected. The
    builders that count by walking pages are the ones at risk, because walking
    via iteration would pick the default up.
    """

    def _paginate(self, mock_usa_client, endpoint, total):
        mock_usa_client.set_paginated_response(
            endpoint, [{"id": i, "name": f"Item {i}", "amount": 1.0} for i in range(total)]
        )

    def test_spending_count_ignores_default_result_limit(self, mock_usa_client, client_config):
        self._paginate(mock_usa_client, MockUSASpendingClient.Endpoints.SPENDING_BY_RECIPIENT, 30)
        client_config(default_result_limit=5)

        query = mock_usa_client.spending.search().by_recipient().fiscal_year(2024)

        assert query.count() == 30

    def test_page_walking_count_ignores_default_result_limit(self, mock_usa_client, client_config):
        """FundingSearch has no count endpoint, so it counts by walking pages."""
        self._paginate(mock_usa_client, "/awards/funding/", 25)
        client_config(default_result_limit=10)

        query = mock_usa_client.funding.award_id("CONT_AWD_1")

        assert query.count() == 25

    def test_explicit_limit_still_caps_the_count(self, mock_usa_client, client_config):
        """An explicit limit() is the caller's own bound, so it does apply."""
        self._paginate(mock_usa_client, "/awards/funding/", 25)
        client_config(default_result_limit=None)

        query = mock_usa_client.funding.award_id("CONT_AWD_1").limit(7)

        assert query.count() == 7


class TestRecipientIdNormalizationIsSingleSourced:
    """Recipient-ID normalization resolves one raw ID to exactly one entity.

    It used to be implemented twice and the two DISAGREED: the model took the
    *first* token of a "-['C','R']" suffix while the query *preferred 'R'*.
    Because the suffix denotes recipient level, the same raw ID resolved to two
    different entities depending on the path taken. Six such IDs appear in the
    captured fixtures, so the defect reached real data.

    Phase 5 consolidated both onto utils.validations.normalize_recipient_id,
    which avoids 'R' whenever another level is available. Measured against the
    live endpoint for all six multi-level IDs in the fixtures, the 'R' record
    reports less spending than its sibling and reports flat zero in four of six,
    so preferring 'R' would have zeroed out real totals. The query path, which
    did prefer 'R', changed to match the model. Avoiding 'R' by membership rather
    than by list position means a list arriving as ['R','C'] cannot reintroduce
    the defect.

    This table now pins that both paths agree, which is the property that was
    broken. The normalizer's own edge cases live in
    tests/utils/test_validations.py.
    """

    @pytest.mark.parametrize(
        "raw,expected",
        [
            # 'R' is avoided whenever another level is available.
            ("abc123-['C','R']", "abc123-C"),
            ("abc123-['R','C']", "abc123-C"),
            ("abc123-['P','R']", "abc123-P"),
            ("abc123-['C']", "abc123-C"),
            ("abc123-['P','C']", "abc123-P"),
            # Already-normal forms pass through.
            ("abc123-R", "abc123-R"),
            ("abc123", "abc123"),
        ],
    )
    def test_both_paths_agree(self, mock_usa_client, raw, expected):
        """The model and the query resolve a raw ID identically."""
        from usaspending.utils.validations import normalize_recipient_id

        assert normalize_recipient_id(raw) == expected

        # The model normalizes on construction...
        recipient = Recipient({"recipient_id": raw}, mock_usa_client)
        assert recipient.recipient_id == expected

        # ...and the query normalizes the ID it will fetch by.
        assert RecipientQuery(mock_usa_client)._clean_resource_id(raw) == expected
