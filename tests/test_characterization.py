"""Characterization tests pinning behavior the refactor must not change.

This file covers only behavior that the rest of the suite does **not** already
pin. Where existing tests already cover something, they are named here instead
of being duplicated, because a behavior pinned in two places is a behavior that
can be changed in one and contradicted in the other.

Already covered elsewhere, deliberately not repeated here:

* Absent-key money defaults of ``Decimal("0.00")`` --
  ``tests/models/test_award_decimal_precision.py::test_zero_default_values``
  (the same six Award properties) and
  ``tests/models/test_award_account.py::test_missing_obligated_amount_returns_zero``.
  **Phase 4 must update those two files**, plus the repr guard below.
* ``Location.zip5`` returning ``""`` --
  ``tests/models/test_location.py::test_zip5_none_returns_empty_string``.
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
from usaspending.models.award_account import AwardAccount
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


class TestUnguardedMoneyFormatting:
    """AwardAccount.__repr__ formats its amount with no None guard.

    Every sibling repr uses ``or 0``, so this is the one place where Phase 4's
    absent-value change would raise TypeError instead of rendering. Phase 4 must
    add the guard before making the amount optional.
    """

    def test_repr_renders_a_missing_amount_as_zero(self, mock_usa_client):
        account = AwardAccount({"federal_account": "080-0131"}, mock_usa_client)

        assert "$0.00" in repr(account)


class TestAwardIdentifierEmptyString:
    """Award.award_identifier returns "" rather than None when unknown.

    Only the private _derived_award_identifier is covered elsewhere, so the
    public property's empty-string contract is pinned here. Phase 4 normalizes
    it to None.
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


class TestSpendingSearchCountIgnoresDefaultLimit:
    """SpendingSearch.count() applies explicit limits only.

    It counts with its own loop rather than going through
    QueryBuilder.__iter__, so config.default_result_limit does not cap it.
    Phase 2 replaces that loop, and routing it through plain iteration would
    silently start applying the default.
    """

    def test_count_ignores_default_result_limit(self, mock_usa_client, client_config):
        items = [{"id": i, "name": f"Recipient {i}", "amount": 1.0} for i in range(30)]
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.SPENDING_BY_RECIPIENT, items
        )
        client_config(default_result_limit=5)

        query = mock_usa_client.spending.search().by_recipient().fiscal_year(2024)

        assert query.count() == 30


class TestRecipientIdNormalizationDiverges:
    """Recipient-ID normalization is implemented twice, and the two DISAGREE.

    Recipient._clean_recipient_id takes the *first* token of a "-['C','R']"
    suffix, while RecipientQuery._clean_recipient_id *prefers 'R'*. Because the
    suffix denotes recipient level (R=recipient, P=parent, C=child), the same
    raw ID resolves to two different entities depending on the path taken.

    This is a live defect, not merely duplication. Phase 5 consolidates the two
    onto one algorithm and must update this table, which makes the chosen
    semantics explicit. The model-side cleaner in isolation is already covered
    by tests/models/test_recipient.py::TestRecipientIdCleaning.
    """

    @pytest.mark.parametrize(
        "raw,model_result,query_result",
        [
            # Agreement: a single token, or 'R' already first.
            ("abc123-['R','C']", "abc123-R", "abc123-R"),
            ("abc123-['C']", "abc123-C", "abc123-C"),
            ("abc123-R", "abc123-R", "abc123-R"),
            ("abc123", "abc123", "abc123"),
            # Divergence: 'R' present but not first.
            ("abc123-['C','R']", "abc123-C", "abc123-R"),
            ("abc123-['P','R']", "abc123-P", "abc123-R"),
        ],
    )
    def test_normalization_results(self, mock_usa_client, raw, model_result, query_result):
        assert Recipient._clean_recipient_id(raw) == model_result
        assert RecipientQuery(mock_usa_client)._clean_recipient_id(raw) == query_result
