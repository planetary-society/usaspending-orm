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
from usaspending import models, queries, resources

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


#: Subpackages whose ``__all__`` is part of the surface even though the top-level
#: package does not re-export all of it. Resources are the most user-facing classes
#: in the library, since every entry point runs through one, yet none is exported:
#: they are reached as client properties, so walking ``usaspending.__all__`` alone
#: covered none of them. Queries and models are re-exported only in part, and what
#: models holds back includes ``BaseModel``, ``ClientAwareModel`` and ``LazyRecord``,
#: which every user-facing model inherits from.
#:
#: ``utils`` and ``download`` also carry an ``__all__`` and are deliberately left
#: out: nothing reaches them except through the classes above, so their names are
#: implementation rather than surface.
_SURFACE_SUBPACKAGES = {"models": models, "queries": queries, "resources": resources}


def _collect_surface() -> dict[str, object]:
    """Build the current public API surface description.

    Returns:
        dict[str, object]: Mapping with the package's ``__all__``, each covered
        subpackage's ``__all__``, and the public attribute names of every class
        any of them exports.
    """
    exported = sorted(usaspending.__all__)
    subpackages = {name: sorted(mod.__all__) for name, mod in _SURFACE_SUBPACKAGES.items()}

    classes: dict[str, list[str]] = {}
    for module in (usaspending, *_SURFACE_SUBPACKAGES.values()):
        for name in module.__all__:
            attr = getattr(module, name)
            if inspect.isclass(attr):
                # A class re-exported at the top level is the same object here, so
                # recording it once by name is enough.
                classes[name] = _public_names(attr)

    return {"__all__": exported, "subpackages": subpackages, "classes": classes}


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


@pytest.mark.parametrize("subpackage", sorted(_SURFACE_SUBPACKAGES))
def test_subpackage_exports_are_unchanged(subpackage, current_surface, expected_surface):
    """A covered subpackage must not gain, lose, or rename an export.

    Separate from the top-level check because these are reachable without being
    re-exported: a resource is reached as a client property, so nothing in
    ``usaspending.__all__`` names it.
    """
    assert current_surface["subpackages"][subpackage] == expected_surface["subpackages"][subpackage]


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
