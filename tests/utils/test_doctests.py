"""Run the documented examples in modules whose examples are self-contained.

Examples that nothing runs drift silently, and a wrong example is worse than none.

Only modules with no client, no network and no fixtures belong here. Most of the
package documents itself with examples like `client.awards.search()`, which need
a live session; `tests/test_readme_examples.py` covers that surface under the
`integration` marker instead.
"""

from __future__ import annotations

import doctest
import importlib
import pkgutil
from types import ModuleType

import pytest

import usaspending
from usaspending.queries import filters
from usaspending.utils import textcase, validations

#: Modules whose examples run with no client, no network and no fixtures. Not only
#: `utils`: `queries.filters` qualifies too, and its one broken example was found
#: by looking outside. Only modules that actually carry examples belong here, since
#: the test below requires each to contribute at least one, so an entry with none
#: fails rather than passing vacuously. `dates` and `numbers` have none today.
SELF_CONTAINED: tuple[ModuleType, ...] = (filters, textcase, validations)


@pytest.mark.parametrize("module", SELF_CONTAINED, ids=lambda m: m.__name__.split(".")[-1])
def test_documented_examples_hold(module: ModuleType) -> None:
    """Every example in the module produces exactly what it claims."""
    result = doctest.testmod(module, verbose=False, report=False)

    assert result.attempted, "no examples found; deleting them must not pass silently"
    assert result.failed == 0, f"{result.failed} of {result.attempted} examples failed"


def test_every_documented_example_is_valid_python() -> None:
    """Every example in the package parses, whether or not anything can run it.

    Most of the package's examples need a live client, so they cannot be executed
    offline. They can still be compiled, which is the check that matters to a
    reader copying one: nine were not valid Python when this was added, all on
    resource entry points, each a chained call split across lines without the
    enclosing parentheses that makes the continuation legal.

    This is the cheap half of the split `tests/test_readme_examples.py` already
    makes, where an unmarked test guards what needs no session and an
    `integration` one runs the rest.
    """
    finder = doctest.DocTestFinder()
    broken = []

    for info in pkgutil.walk_packages(usaspending.__path__, f"{usaspending.__name__}."):
        module = importlib.import_module(info.name)
        for test in finder.find(module):
            for example in test.examples:
                try:
                    compile(example.source, test.name, "single")
                except SyntaxError as error:
                    broken.append(f"{test.name} line {example.lineno}: {error.msg}")

    assert not broken, "examples that a reader could not run:\n" + "\n".join(broken)
