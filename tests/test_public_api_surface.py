"""Guard the public API surface against accidental drift during refactoring.

The refactor is meant to be internal: it reorganizes implementation without
changing what callers can reach. This test snapshots the public surface and
fails if a name is added, removed, or renamed, or if a public callable changes
the call it accepts.

What it records is deliberately narrow. Names are the contract, and so is the
shape of a call; types are not. So a member is recorded by name plus a signature
carrying parameter names, kinds and defaults, with annotations and return types
left out. Annotations are free to move with the implementation, which is exactly
the kind of internal change this refactor makes, so recording them would
false-fail on it. Defaults are recorded by value when that value is a plain
literal, whose repr the language fixes, and otherwise only as present, because
the repr of anything richer can drift while the call stays the same. Either way,
a required parameter becoming optional, or the reverse, is caught.

``__init__`` is recorded as well, private name notwithstanding: constructing a
model or a filter is the most visible call a class has, and for a dataclass it is
the only place a required field appears at all.

The record is also interpreter-independent. Names a class only has by inheriting
from a builtin are skipped, because that set moves between Python versions:
``BaseException`` gained ``add_note`` in 3.11, which would otherwise make a
snapshot recorded on 3.10 fail on 3.11 with nothing in the library changed. A
constructor is held to the stricter test of being defined inside this package,
since every class has one whether it wrote it or not, and an inherited one is
whatever the interpreter says today: ``Enum`` supplies an ``__init__`` on 3.11 and
3.12 but not on 3.10 or 3.14.

To accept an intentional surface change, regenerate the snapshot:

    USASPENDING_REGEN_API_SURFACE=1 uv run pytest tests/test_public_api_surface.py

and review the resulting diff to tests/fixtures/public_api_surface.json.
"""

from __future__ import annotations

import functools
import importlib
import inspect
from pathlib import Path

import pytest

import usaspending
from tests.snapshot_support import load_snapshot
from usaspending import download, models, queries, resources, utils

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "public_api_surface.json"
REGEN_ENV_VAR = "USASPENDING_REGEN_API_SURFACE"

#: Module a name must not come from to count as ours. Every class inherits from
#: ``object``, and the exception classes from ``BaseException``, so the members
#: those contribute say nothing about this library and vary by Python version.
_BUILTINS_MODULE = "builtins"

#: Package a constructor must be defined in to be recorded. Measured across 3.9 to
#: 3.14, every constructor this library writes is here, and the only other sources
#: are ``builtins`` and, on 3.11 and 3.12 alone, ``enum``.
_PACKAGE_MODULE = usaspending.__name__

#: Types whose defaults are recorded by value rather than only as present. Their
#: reprs are fixed by the language, so recording them cannot false-fail on an
#: interpreter upgrade, and recording them turns values callers depend on, such as
#: a sort direction of ``"desc"``, into guarded contract. Matched by exact type
#: rather than ``isinstance`` to keep enum members out: an ``IntEnum`` member is an
#: ``int``, and enum reprs were rewritten in 3.11 and again in 3.12.
_STABLE_DEFAULT_TYPES = (bool, float, int, str, type(None))

#: Subpackages whose ``__all__`` is part of the surface even though the top-level
#: package does not re-export all of it. Resources are the most user-facing classes
#: in the library, since every entry point runs through one, yet none is exported:
#: they are reached as client properties, so walking ``usaspending.__all__`` alone
#: covered none of them. Queries and models are re-exported only in part, and what
#: models holds back includes ``BaseModel``, ``ClientAwareModel`` and ``LazyRecord``,
#: which every user-facing model inherits from. ``utils`` and ``download`` export
#: names callers import directly, such as ``parse_date_string``, and the README
#: documents ``client.downloads`` as returning a ``DownloadJob``, so both are
#: surface even though nothing at the top level re-exports them.
_SURFACE_SUBPACKAGES = {
    "download": download,
    "models": models,
    "queries": queries,
    "resources": resources,
    "utils": utils,
}

#: Deep import paths that must keep resolving. The snapshot above records what each
#: module exports, not where it lives, so moving a module leaves it green while
#: breaking ``from usaspending.models.award import Award`` for anyone who pinned the
#: path rather than the package export. Which paths to pin is a judgment call: the
#: README uses none of them, so this is a guess at what caller code written against
#: 0.7.3 reaches for, biased toward the modules the refactor moved most. The
#: exception is ``usaspending.utils.current_fiscal_year``, which is new this cycle
#: (it moved up from ``usaspending.utils.formatter``); it is pinned here because the
#: CHANGELOG publishes the new path.
_COMPAT_IMPORT_PATHS = [
    "usaspending.download.job.DownloadJob",
    "usaspending.exceptions.USASpendingError",
    "usaspending.models.award.Award",
    "usaspending.queries.query_builder.QueryBuilder",
    "usaspending.utils.current_fiscal_year",
    "usaspending.utils.parse_date_string",
]


class _HasDefault:
    """Stand-in for a default value recorded only as present.

    Rendering as the empty string makes ``inspect.Signature`` write the parameter
    as ``name=``, which says a default exists without pinning what it is.
    """

    def __repr__(self) -> str:
        """Return the empty string, so the signature reads ``name=``."""
        return ""


_HAS_DEFAULT = _HasDefault()


def _defining_module(cls: type, name: str) -> str:
    """Return the module of the class that gives ``cls`` its ``name`` attribute.

    Args:
        cls: Class whose method resolution order is walked.
        name: Attribute name to locate.

    Returns:
        str: ``__module__`` of the first class in the MRO whose own ``__dict__``
        carries the name.
    """
    for klass in cls.__mro__:
        if name in vars(klass):
            return klass.__module__

    # Unreachable for what this walk feeds in: ``dir()`` on a class is assembled
    # from the MRO dicts and lists nothing a metaclass contributes, and every
    # class has an ``__init__`` from ``object`` at worst (probed across all
    # covered classes: no name misses). Answering with the class's own module
    # rather than raising means a surprise gets recorded instead of dropped.
    return cls.__module__


def _record_parameter(param: inspect.Parameter) -> inspect.Parameter:
    """Reduce a parameter to what the snapshot records.

    Args:
        param: Parameter to reduce.

    Returns:
        inspect.Parameter: The same name and kind with the annotation dropped,
        keeping a default that is a stable literal and replacing any other with a
        marker that records only that a default exists.
    """
    default = param.default
    if default is not inspect.Parameter.empty and type(default) not in _STABLE_DEFAULT_TYPES:
        default = _HAS_DEFAULT

    return param.replace(annotation=inspect.Parameter.empty, default=default)


def _signature(name: str, obj: object) -> str:
    """Describe a callable as a readable, annotation-free call shape.

    Args:
        name: Name the callable is reached by.
        obj: The function or method to inspect.

    Returns:
        str: Something like ``"limit(self, num)"`` or
        ``"order_by(self, field, direction='desc')"``. A callable with no
        introspectable signature, which C-implemented ones can be, records as
        ``"name(...)"`` so the name is still guarded.
    """
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return f"{name}(...)"

    recorded = signature.replace(
        parameters=[_record_parameter(param) for param in signature.parameters.values()],
        return_annotation=inspect.Signature.empty,
    )
    return f"{name}{recorded}"


def _describe_member(cls: type, name: str) -> str:
    """Describe one public member of a class.

    Args:
        cls: Class the member belongs to.
        name: Member name.

    Returns:
        str: The call shape for a method, ``"name (property)"`` for anything
        reached as an attribute but computed on access, and ``"name (attribute)"``
        for plain class data such as a constant or an enum member.
    """
    # A property is a data descriptor; cached_property is not, so it needs naming.
    static = inspect.getattr_static(cls, name, None)
    if isinstance(static, functools.cached_property) or inspect.isdatadescriptor(static):
        return f"{name} (property)"

    # getattr rather than the static lookup, because it unwraps classmethod and
    # staticmethod into the callable a caller actually reaches.
    value = getattr(cls, name, None)
    if inspect.isroutine(value):
        return _signature(name, value)

    return f"{name} (attribute)"


def _public_members(cls: type) -> dict[str, str]:
    """Describe every public member a class contributes to the surface.

    Args:
        cls: Class to introspect.

    Returns:
        dict[str, str]: Member name to its recorded shape, skipping private names
        and anything the class only has by inheriting from a builtin. Known gap:
        ``dir()`` does not list methods defined on an ``Enum`` subclass, so those
        would go unrecorded; no exported enum has one today.
    """
    members = {
        name: _describe_member(cls, name)
        for name in dir(cls)
        if not name.startswith("_") and _defining_module(cls, name) != _BUILTINS_MODULE
    }

    # The one private name worth recording: the constructor is how callers reach
    # the class, and for a dataclass it is where a required field is declared,
    # since a field without a default leaves no class attribute for dir() to find.
    # Only one this package defines, though. Every class has a constructor, so an
    # inherited one records the interpreter rather than the library.
    constructor_module = _defining_module(cls, "__init__")
    if constructor_module.split(".")[0] == _PACKAGE_MODULE:
        members["__init__"] = _signature("__init__", cls.__init__)

    return members


def _collect_surface() -> dict[str, object]:
    """Build the current public API surface description.

    Returns:
        dict[str, object]: Mapping with the package's ``__all__``, each covered
        subpackage's ``__all__``, the public members of every class any of them
        exports, and the call shape of every function they export.
    """
    exported = sorted(usaspending.__all__)
    subpackages = {name: sorted(mod.__all__) for name, mod in _SURFACE_SUBPACKAGES.items()}

    classes: dict[str, dict[str, str]] = {}
    functions: dict[str, str] = {}
    for module in (usaspending, *_SURFACE_SUBPACKAGES.values()):
        for name in module.__all__:
            attr = getattr(module, name)
            if inspect.isclass(attr):
                # A class re-exported at the top level is the same object here, so
                # recording it once by name is enough. The same goes for functions.
                classes[name] = _public_members(attr)
            elif inspect.isroutine(attr):
                functions[name] = _signature(name, attr)

    return {
        "__all__": exported,
        "subpackages": subpackages,
        "classes": classes,
        "functions": functions,
    }


def _differences(expected: dict[str, str], actual: dict[str, str]) -> dict[str, object]:
    """Compare two records of name to shape, reporting only what differs.

    Args:
        expected: The recorded record.
        actual: The record just collected.

    Returns:
        dict[str, object]: Any of ``removed``, ``added`` and ``changed`` that is
        non-empty, so a signature change reads as one entry rather than as a
        removal paired with an addition. Empty when the two records match.
    """
    report: dict[str, object] = {}

    removed = sorted(set(expected) - set(actual))
    if removed:
        report["removed"] = removed

    added = sorted(set(actual) - set(expected))
    if added:
        report["added"] = added

    changed = {
        name: f"{expected[name]} -> {actual[name]}"
        for name in sorted(set(expected) & set(actual))
        if expected[name] != actual[name]
    }
    if changed:
        report["changed"] = changed

    return report


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
    """No exported class may gain, lose, or reshape a public member."""
    current = current_surface["classes"]

    differences: dict[str, dict[str, object]] = {}
    for class_name, expected_members in expected_surface["classes"].items():
        actual_members = current.get(class_name, {})
        if actual_members == expected_members:
            continue
        differences[class_name] = _differences(expected_members, actual_members)

    assert differences == {}, (
        "Public API surface changed. If intentional, regenerate with "
        f"{REGEN_ENV_VAR}=1 and review the snapshot diff. Differences: {differences}"
    )


def test_exported_function_signatures_are_unchanged(current_surface, expected_surface):
    """No exported function may change the call it accepts.

    Separate from the class check because these are reached as module attributes,
    so nothing in the class walk sees them.
    """
    differences = _differences(expected_surface["functions"], current_surface["functions"])

    assert differences == {}, (
        "Exported function surface changed. If intentional, regenerate with "
        f"{REGEN_ENV_VAR}=1 and review the snapshot diff. Differences: {differences}"
    )


@pytest.mark.parametrize("dotted_path", _COMPAT_IMPORT_PATHS)
def test_compat_import_path_still_resolves(dotted_path):
    """A deep import path callers already pinned must keep working."""
    module_path, _, attribute = dotted_path.rpartition(".")

    try:
        resolved = hasattr(importlib.import_module(module_path), attribute)
    except ModuleNotFoundError:
        # Reported through the assertion below rather than as a collection-time
        # error, so a moved module reads as the contract break it is.
        resolved = False

    assert resolved, (
        f"{dotted_path} no longer resolves. Callers import it directly, so the "
        "name has to stay reachable at this path even if the implementation moved."
    )
