"""Invariants binding the award-category registry to the code that reads it.

:data:`usaspending.models.award_types.AWARD_CATEGORIES` is the single source of
truth for award-type knowledge, and several call sites rely on its fields
naming something real: ``group`` names a convenience method on ``AwardsSearch``,
``download_type`` names a method on ``DownloadResource``, and ``model_name`` and
``search_fields_model`` name model classes.

Those couplings are what let the library drop its hand-maintained dispatch
tables, so they are asserted here rather than left implicit. A new category that
forgets one of them fails immediately instead of at the call site.

Content of the code groups themselves is owned by
``tests/models/test_award_type_constants.py``, which pins the expected codes as
literals. This file covers only the registry's structure and its couplings.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from usaspending.models.award import Award
from usaspending.models.award_factory import create_award, model_for_name
from usaspending.models.award_types import (
    ALL_AWARD_CODES,
    AWARD_CATEGORIES,
    DOWNLOAD_TYPES,
    AwardCategory,
    categories_for_codes,
    category_for_api_count_key,
    category_for_exclusive_codes,
    category_for_singular,
)
from usaspending.queries.awards_search import AwardsSearch

ALL_CATEGORIES = pytest.mark.parametrize(
    "category", AWARD_CATEGORIES, ids=lambda category: category.group
)
DOWNLOAD_CATEGORIES = pytest.mark.parametrize(
    "category",
    tuple(category for category in AWARD_CATEGORIES if category.download_type is not None),
    ids=lambda category: category.group,
)


class TestRegistryShape:
    """The registry's own keys must be unique and internally consistent."""

    @pytest.mark.parametrize("field", ["group", "singular", "api_count_key"])
    def test_key_fields_are_unique(self, field):
        values = [getattr(category, field) for category in AWARD_CATEGORIES]

        assert len(values) == len(set(values)), f"Duplicate {field} in AWARD_CATEGORIES"

    def test_codes_do_not_overlap_between_categories(self):
        seen: dict[str, str] = {}
        for category in AWARD_CATEGORIES:
            for code in category.codes:
                assert code not in seen, (
                    f"Code {code!r} is in both {seen[code]!r} and {category.group!r}"
                )
                seen[code] = category.group

        assert set(seen) == set(ALL_AWARD_CODES)

    @ALL_CATEGORIES
    def test_registry_entries_are_immutable(self, category: AwardCategory):
        with pytest.raises(FrozenInstanceError):
            category.group = "changed"
        with pytest.raises(TypeError):
            category.types["ZZZ"] = "injected"

    def test_download_types_are_derived_from_the_registry(self):
        assert DOWNLOAD_TYPES == {
            category.download_type for category in AWARD_CATEGORIES if category.download_type
        }


class TestLookups:
    """The lookups must resolve, and reject unknown input."""

    @ALL_CATEGORIES
    def test_categories_for_codes_finds_the_category(self, category: AwardCategory):
        assert categories_for_codes(category.codes) == [category]

    def test_categories_for_codes_preserves_declaration_order(self):
        mixed = set(AWARD_CATEGORIES[-1].codes) | set(AWARD_CATEGORIES[0].codes)

        found = categories_for_codes(mixed)

        assert found == [AWARD_CATEGORIES[0], AWARD_CATEGORIES[-1]]

    def test_unknown_names_resolve_to_none(self):
        assert category_for_singular("nope") is None
        assert category_for_api_count_key("nope") is None
        assert categories_for_codes(set()) == []

    @ALL_CATEGORIES
    def test_exclusive_codes_only_match_categories_with_a_model(self, category: AwardCategory):
        found = category_for_exclusive_codes(category.codes)

        if category.has_dedicated_model:
            assert found is category
        else:
            assert found is None

    def test_exclusive_codes_reject_a_mixed_set(self):
        contracts, grants = AWARD_CATEGORIES[0], category_for_api_count_key("grants")
        mixed = set(contracts.codes) | set(grants.codes)

        assert category_for_exclusive_codes(mixed) is None


class TestCouplingsToOtherLayers:
    """Registry fields must name things that actually exist."""

    @ALL_CATEGORIES
    def test_group_names_a_search_method_selecting_this_category(
        self, category: AwardCategory, mock_usa_client
    ):
        """Each group name is also the AwardsSearch convenience method name."""
        search = getattr(AwardsSearch(mock_usa_client), category.group)()

        assert search._get_award_type_codes() == set(category.codes)

    @ALL_CATEGORIES
    def test_search_fields_model_resolves_to_a_model(self, category: AwardCategory):
        model = model_for_name(category.search_fields_model)

        assert model is not Award, f"Unknown search_fields_model {category.search_fields_model!r}"
        assert isinstance(model.SEARCH_FIELDS, list)

    @DOWNLOAD_CATEGORIES
    def test_download_type_names_a_download_resource_method(
        self, category: AwardCategory, mock_usa_client
    ):
        """Award.download() resolves its resource method from download_type."""
        assert callable(getattr(mock_usa_client.downloads, category.download_type, None)), (
            f"DownloadResource has no {category.download_type}() for {category.group}"
        )

    @ALL_CATEGORIES
    def test_model_download_type_matches_the_registry(self, category: AwardCategory):
        """The model's _download_type must agree with its category.

        Loan does not declare one; it inherits "assistance" from Grant.
        """
        model = model_for_name(category.model_name)

        assert model._download_type == category.download_type

    @ALL_CATEGORIES
    @pytest.mark.parametrize("key", ["category", "type"])
    def test_factory_builds_the_declared_model(self, category: AwardCategory, mock_usa_client, key):
        value = category.singular if key == "category" else sorted(category.codes)[0]

        award = create_award({key: value}, mock_usa_client)

        assert type(award) is model_for_name(category.model_name)
