"""Tests that execute the Python examples embedded in README.md.

Every runnable ``python`` code block in the README is extracted and executed
verbatim against the live USAspending.gov API, so broken or rotted examples
are caught mechanically. The live-execution tests are marked ``integration``
and excluded by default (run with ``pytest -m integration``); the extraction
guard needs no network and runs in the default suite.

Sample-output values shown in README comments (counts, amounts, dates) are
illustrative only. They drift as agencies report new spending, so this module
asserts that the blocks execute without error, not that they print any
particular value.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

from usaspending import USASpendingClient

# README.md lives at the repository root, one directory above ``tests/``.
_README_PATH = Path(__file__).resolve().parent.parent / "README.md"
_README_TEXT = _README_PATH.read_text(encoding="utf-8")

# A block is skipped when it contains any of these substrings. These examples
# either mutate global state, intentionally raise, or make far too many live
# API calls to run as part of a routine integration sweep.
_EXCLUSION_MARKERS: tuple[str, ...] = (
    "client.downloads",  # queues real server-side download jobs
    "DetachedInstanceError",  # example intentionally raises this exception
    "config",  # mutates global library configuration
    ".all()",  # unbounded fetch up to the 10,000-result default limit
    ".limit(100)",  # the N+1 pedagogy blocks; too many API calls for a routine run
)

# Bump this when README examples are added, removed, or switch between the
# runnable and excluded sets. The exact match makes silent coverage drift
# (a runnable example quietly falling out of the run set, or vice versa)
# fail loudly instead.
_EXPECTED_RUNNABLE_BLOCKS = 10


def _extract_python_blocks(text: str) -> list[str]:
    """Return the source of every fenced ``python`` block, in document order."""
    return re.findall(r"```python\n(.*?)```", text, re.DOTALL)


def _is_runnable(block: str) -> bool:
    """Return True when a block exercises the client and hits no exclusion marker."""
    if "client." not in block:
        return False
    return not any(marker in block for marker in _EXCLUSION_MARKERS)


def _block_id(index: int, block: str) -> str:
    """Build a readable parametrize id from a block's first non-comment line.

    The ``index`` is the block's position among all extracted ``python``
    blocks (not just the runnable subset), so ids stay traceable to the README.
    """
    label = ""
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            label = line[:40].replace(" ", "_")
            break
    return f"block{index:02d}-{label}"


# Built at import time so pytest can collect one case per runnable README block.
_ALL_BLOCKS = _extract_python_blocks(_README_TEXT)
_RUNNABLE_BLOCKS: list[tuple[int, str]] = [
    (index, block) for index, block in enumerate(_ALL_BLOCKS) if _is_runnable(block)
]


def test_expected_runnable_blocks_discovered() -> None:
    """Guard against extraction or exclusion drift (runs in the default suite)."""
    assert len(_RUNNABLE_BLOCKS) == _EXPECTED_RUNNABLE_BLOCKS, (
        f"Expected exactly {_EXPECTED_RUNNABLE_BLOCKS} runnable README examples "
        f"but found {len(_RUNNABLE_BLOCKS)}. Either README examples changed "
        f"(update _EXPECTED_RUNNABLE_BLOCKS in tests/test_readme_examples.py) "
        f"or the block extraction/exclusion markers no longer match the README."
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("index", "block"),
    _RUNNABLE_BLOCKS,
    ids=[_block_id(index, block) for index, block in _RUNNABLE_BLOCKS],
)
def test_readme_block_executes(index: int, block: str, client: USASpendingClient) -> None:
    """Execute a runnable README code block verbatim against the live API.

    The namespace is pre-seeded with ``USASpendingClient`` and a live ``client``
    so fragment blocks referencing a bare ``client`` run as written; blocks
    that open their own ``with USASpendingClient() as client:`` simply shadow
    it. Blocks are dedented so examples fenced inside Markdown lists compile.
    """
    source = textwrap.dedent(block)
    namespace = {"USASpendingClient": USASpendingClient, "client": client}
    exec(compile(source, f"README.md:block{index}", "exec"), namespace)
