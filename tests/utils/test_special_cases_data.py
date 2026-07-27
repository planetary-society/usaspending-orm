"""Verify the real special_cases.yaml ships, loads, and is actually applied.

The rest of the casing suite injects a mock special-cases list
(``tests/utils/test_textcase.py`` patches both the cache and ``open``), so every
existing test would pass even if the real YAML never loaded. That matters because
``TextFormatter._load_special_cases`` degrades to an empty list on failure:
title casing would silently lose every acronym, and while a corrupt file now
warns, a merely absent one does not, so no test would fail.

These tests close that gap, and they were the guard for the move of TextFormatter
into ``utils/textcase.py``. The data file is resolved relative to the module that
loads it, so the path is derived the same way here rather than hardcoding the
repository layout, which would have broken on that move even though the library
kept working.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from usaspending.utils.textcase import TextFormatter, titlecase_name

EXPECTED_ACRONYMS = frozenset({"NASA", "JPL", "EPSCoR", "STEM"})


def _special_cases_path() -> Path:
    """Return the data file path as the loader itself resolves it."""
    return Path(inspect.getfile(TextFormatter)).parent / "special_cases.yaml"


@pytest.fixture(autouse=True, scope="module")
def real_special_cases():
    """Force one real load of the YAML for this module, then restore the cache.

    Module scoped so the file is parsed once rather than per test. The first
    real parse still happens inside this module, which is all the guard needs.
    """
    original = TextFormatter._special_cases_cache
    TextFormatter._special_cases_cache = None
    yield
    TextFormatter._special_cases_cache = original


def test_data_file_sits_beside_its_loader():
    """The YAML must live next to the module that resolves it via __file__."""
    assert _special_cases_path().exists(), (
        f"Expected special_cases.yaml beside {inspect.getfile(TextFormatter)}"
    )


def test_real_special_cases_load_with_expected_acronyms():
    """A swallowed load failure yields an empty list; fail loudly on that."""
    special_cases = TextFormatter._load_special_cases()

    assert isinstance(special_cases, list)
    assert len(special_cases) > 100, (
        "Expected the full special-cases list. An empty or tiny list means the "
        "YAML failed to load and the error was swallowed."
    )
    assert EXPECTED_ACRONYMS <= set(special_cases)


def test_mixed_case_acronym_is_preserved_through_titlecase():
    """EPSCoR is the canary: naive casing would render it "Epscor"."""
    assert titlecase_name("epscor research program") == "EPSCoR Research Program"


def test_acronym_is_preserved_through_sentence_case():
    """Sentence casing must also honor the real special-cases list."""
    assert "NASA" in TextFormatter.to_sentence_case("NASA RESEARCH GRANT")


class TestSpecialCasesShapeInvariants:
    """Shape rules the casing lookup depends on for correctness.

    Title casing resolves through a lookup keyed on lowercase forms rather than by
    scanning the list. Lookup and scan agree on the current data, but that is a
    property of the data, not of the code: the two disagree whenever one entry's
    lowercase form collides with another's. (The sentence-casing lookup keys on
    uppercase forms only, so it is unaffected.)

    Concretely, a list containing both ``Inc`` and ``INC.`` casts ``"inc."`` to
    ``"Inc."`` under a scan and ``"INC."`` under the index. The list already
    contains ``Inc``, so adding ``INC.`` would silently change output for every
    company name ending in it. These assertions turn that into a failing test.
    """

    def _entries(self):
        """Read through the loader, so the invariant covers what the code sees."""
        return [c for c in TextFormatter._load_special_cases() if isinstance(c, str)]

    def test_no_two_entries_share_a_lowercase_form(self):
        """Duplicates make which spelling wins depend on lookup order."""
        seen: dict[str, str] = {}
        collisions = []
        for entry in self._entries():
            key = entry.lower()
            if key in seen:
                collisions.append((seen[key], entry))
            seen[key] = entry

        assert not collisions, f"entries collide on lowercase form: {collisions}"

    def test_no_entry_is_another_plus_a_period(self):
        """An X / X-plus-period pair is the case where scan and index disagree."""
        entries = self._entries()
        lowered = {entry.lower() for entry in entries}
        offenders = [
            entry for entry in entries if entry.endswith(".") and entry[:-1].lower() in lowered
        ]

        assert not offenders, (
            f"these entries duplicate another entry with a trailing period: {offenders}. "
            "Casing would depend on whether the lookup scans or indexes."
        )
