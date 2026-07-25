"""Guard the public API surface against accidental drift during refactoring.

The refactor is meant to be internal: it reorganizes implementation without
changing what callers can reach. This test snapshots the public surface by
*name* and fails if a name is added, removed, or renamed.

It is deliberately name-based rather than type-based. A type-based check (for
example asserting an attribute is a `property`) would false-fail whenever an
implementation legitimately changes shape, which is exactly what the refactor
does. Names are the contract; shapes are not.

To accept an intentional surface change, regenerate the snapshot:

    USASPENDING_REGEN_API_SURFACE=1 uv run pytest tests/test_public_api_surface.py

and review the resulting diff to tests/fixtures/public_api_surface.json.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import usaspending
from tests.snapshot_support import load_snapshot

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "public_api_surface.json"
REGEN_ENV_VAR = "USASPENDING_REGEN_API_SURFACE"


def _public_names(obj: object) -> list[str]:
    """Return sorted public attribute names for an object.

    Args:
        obj: The class or module to introspect.

    Returns:
        list[str]: Sorted names that do not begin with an underscore.
    """
    return sorted(name for name in dir(obj) if not name.startswith("_"))


def _collect_surface() -> dict[str, object]:
    """Build the current public API surface description.

    Returns:
        dict[str, object]: Mapping with the package's ``__all__`` and the
        public attribute names of every exported class.
    """
    exported = sorted(usaspending.__all__)

    classes: dict[str, list[str]] = {}
    for name in exported:
        attr = getattr(usaspending, name)
        if inspect.isclass(attr):
            classes[name] = _public_names(attr)

    return {"__all__": exported, "classes": classes}


@pytest.fixture(scope="module")
def current_surface() -> dict[str, object]:
    """Introspect the package once and share the result across the module."""
    return _collect_surface()


@pytest.fixture(scope="module")
def expected_surface(current_surface) -> dict[str, object]:
    """Load the recorded surface, regenerating only when explicitly requested."""
    return load_snapshot(SNAPSHOT_PATH, current_surface, REGEN_ENV_VAR)


def test_exported_names_are_unchanged(current_surface, expected_surface):
    """__all__ must not gain, lose, or rename entries.

    The exported-class set is derived from __all__, so this covers class
    additions and removals too.
    """
    assert current_surface["__all__"] == expected_surface["__all__"]


def test_public_class_members_are_unchanged(current_surface, expected_surface):
    """No exported class may gain or lose a public member name."""
    current = current_surface["classes"]

    differences: dict[str, dict[str, list[str]]] = {}
    for class_name, expected_members in expected_surface["classes"].items():
        actual_members = current.get(class_name, [])
        if actual_members == expected_members:
            continue
        differences[class_name] = {
            "removed": sorted(set(expected_members) - set(actual_members)),
            "added": sorted(set(actual_members) - set(expected_members)),
        }

    assert differences == {}, (
        "Public API surface changed. If intentional, regenerate with "
        f"{REGEN_ENV_VAR}=1 and review the snapshot diff. Differences: {differences}"
    )
