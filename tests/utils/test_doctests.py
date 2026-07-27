"""Run the documented examples in modules whose examples are self-contained.

Examples that nothing runs drift silently, and a wrong example is worse than none.

Only modules with no client, no network and no fixtures belong here. Most of the
package documents itself with examples like `client.awards.search()`, which need
a live session; `tests/test_readme_examples.py` covers that surface under the
`integration` marker instead.
"""

from __future__ import annotations

import doctest
from types import ModuleType

import pytest

from usaspending.utils import textcase, validations

#: Modules whose examples run with no client, no network and no fixtures. Only
#: modules that actually carry examples belong here: the test below requires each
#: to contribute at least one, so an entry with none fails rather than passing
#: vacuously. `dates` and `numbers` have none today, which is why they are absent.
SELF_CONTAINED: tuple[ModuleType, ...] = (textcase, validations)


@pytest.mark.parametrize("module", SELF_CONTAINED, ids=lambda m: m.__name__.split(".")[-1])
def test_documented_examples_hold(module: ModuleType) -> None:
    """Every example in the module produces exactly what it claims."""
    result = doctest.testmod(module, verbose=False, report=False)

    assert result.attempted, "no examples found; deleting them must not pass silently"
    assert result.failed == 0, f"{result.failed} of {result.attempted} examples failed"
