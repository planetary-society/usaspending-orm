"""Shared support for the suites that execute Markdown code examples.

Two suites extract fenced ``python`` blocks from Markdown and run them against
the live API: ``tests/test_readme_examples.py`` and
``tests/test_documentation.py``. Both need the same extraction, the same
notion of which blocks are safe to run, and the same execution shape, so it
lives here rather than being implemented twice and drifting apart on the one
behavior that makes them trustworthy: which examples actually get run.

Drift here is silent in a specific way. Each suite pins how many runnable
blocks it expects, but that count is computed by the same extraction it is
meant to guard, so a regex that quietly stops matching a fence style lowers the
expected count and the guard stays green. One extractor keeps that failure mode
to one place.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any

#: Fenced ``python`` blocks. Kept deliberately strict: a looser pattern would
#: silently pull in ``console`` and ``text`` blocks, which are not executable.
_PYTHON_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def extract_blocks(text: str) -> list[str]:
    """Return the source of every fenced ``python`` block, in document order.

    Args:
        text: Markdown source.

    Returns:
        list[str]: Each block's body, without the fences.
    """
    return _PYTHON_BLOCK.findall(text)


def extract_blocks_from_tree(root: Path) -> list[tuple[Path, int, str]]:
    """Return every fenced ``python`` block under a directory, in file order.

    Args:
        root: Directory to walk for ``.md`` files.

    Returns:
        list[tuple[Path, int, str]]: One entry per block, carrying the file, the
        block's index within that file, and its source. The index is per-file so
        identifiers stay traceable as pages gain and lose examples.
    """
    blocks: list[tuple[Path, int, str]] = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        blocks.extend((path, index, block) for index, block in enumerate(extract_blocks(text)))
    return blocks


def is_runnable(block: str, exclusion_markers: tuple[str, ...]) -> bool:
    """Return True when a block hits none of the caller's exclusion markers.

    Args:
        block: The block's source.
        exclusion_markers: Substrings that mark a block as unsafe to execute,
            such as one that mutates global configuration or queues a download.

    Returns:
        bool: True when the block may be executed.
    """
    return not any(marker in block for marker in exclusion_markers)


def execute_block(block: str, origin: str, namespace: dict[str, Any]) -> None:
    """Execute one Markdown block verbatim.

    Blocks are dedented so examples fenced inside Markdown lists compile, and
    run against a caller-supplied namespace so fragments that reference a bare
    ``client`` work as written.

    Args:
        block: The block's source.
        origin: Label used as the code object's filename, so a traceback points
            back at the document and block it came from.
        namespace: Globals for the execution, seeded by the caller.
    """
    exec(compile(textwrap.dedent(block), origin, "exec"), namespace)
