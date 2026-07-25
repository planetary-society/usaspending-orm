"""Verify the real special_cases.yaml ships, loads, and is actually applied.

The rest of the formatter suite injects a mock special-cases list
(``tests/utils/test_formatter.py`` patches the cache, and
``tests/utils/test_text_formatter.py`` patches ``open``), so every existing test
would pass even if the real YAML never loaded. That matters because
``TextFormatter._load_special_cases`` catches the failure, logs a warning, and
falls back to an empty list: title casing would silently lose every acronym,
with no exception and no failing test.

These tests close that gap, and they are the guard for Phase 6, which moves
TextFormatter into ``utils/textcase.py``. The data file is resolved relative to
the module that loads it, so the path is derived the same way here rather than
hardcoding the repository layout, which would break on that move even though
the library kept working.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from usaspending.utils.formatter import TextFormatter, titlecase_name

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
