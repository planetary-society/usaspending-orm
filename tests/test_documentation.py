"""Structural checks for the MkDocs documentation site.

Documentation examples are checked at two levels. Every fenced ``python`` block
must compile, which runs in the default suite. Most blocks are additionally
executed verbatim against the live USAspending.gov API under the
``integration`` marker, because a syntax check cannot catch the failures that
actually mislead readers: a renamed method, a filter that matches nothing, or a
return value the prose describes incorrectly.

Sample-output values shown in the documentation (counts, amounts, dates) are
illustrative and drift as agencies report new spending, so the live tests
assert that blocks execute without error, not that they print any particular
value.
"""

from __future__ import annotations

import builtins
import inspect
import re
import textwrap
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlparse

import pytest
import requests
import yaml

import usaspending
from tests.markdown_examples import execute_block, extract_blocks_from_tree, is_runnable
from tests.test_public_api_surface import _SURFACE_SUBPACKAGES
from usaspending import USASpendingClient

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
MKDOCS_CONFIG = ROOT / "mkdocs.yml"

# An award used by several documentation examples, and the value seeded as
# ``award`` for blocks that continue from a previous one.
_EXAMPLE_AWARD_ID = "80GSFC18C0008"


class MkDocsConfigLoader(yaml.SafeLoader):
    """Safe YAML loader that understands MkDocs' environment-value tag."""


def _environment_value(loader: MkDocsConfigLoader, node: yaml.Node) -> str:
    """Return the local fallback from ``!ENV [VARIABLE, fallback]``."""
    values = loader.construct_sequence(node)
    return values[-1]


MkDocsConfigLoader.add_constructor("!ENV", _environment_value)


def _navigation_targets(items: list[object]) -> list[str]:
    """Return every local page named in a nested MkDocs navigation list."""
    targets: list[str] = []
    for item in items:
        if isinstance(item, str):
            targets.append(item)
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    targets.append(value)
                elif isinstance(value, list):
                    targets.extend(_navigation_targets(value))
    return targets


def test_mkdocs_navigation_references_existing_pages() -> None:
    """Every local page in the explicit site navigation must exist."""
    config = yaml.load(MKDOCS_CONFIG.read_text(encoding="utf-8"), Loader=MkDocsConfigLoader)
    targets = _navigation_targets(config["nav"])
    local_targets = [target for target in targets if not urlparse(target).scheme]

    missing = [target for target in local_targets if not (DOCS_DIR / target).is_file()]

    assert missing == []


#: Read once at import; every example check below derives from this one walk.
_ALL_BLOCKS: list[tuple[Path, int, str]] = extract_blocks_from_tree(DOCS_DIR)


def test_python_examples_in_documentation_compile() -> None:
    """Python examples should remain syntactically valid as documentation evolves."""
    assert _ALL_BLOCKS, "Expected at least one Python example under docs/"
    for path, _index, block in _ALL_BLOCKS:
        compile(textwrap.dedent(block), str(path.relative_to(ROOT)), "exec")


# A block is skipped when it contains any of these substrings. These examples
# either mutate global state, write files, or make far too many live API calls
# to run as part of a routine integration sweep. Blocks that raise on purpose
# are not excluded when they handle the exception themselves.
_EXCLUSION_MARKERS: tuple[str, ...] = (
    "config.configure",  # mutates global library configuration
    "client.downloads",  # queues a real server-side download job
    "award.download(",  # queues a real server-side download job
    ".limit(100)",  # the N+1 pedagogy block; too many API calls for a routine run
)

# Bump this when documentation examples are added, removed, or switch between
# the runnable and excluded sets. The exact match makes silent coverage drift
# (a runnable example quietly falling out of the run set, or vice versa) fail
# loudly instead.
_EXPECTED_RUNNABLE_BLOCKS = 25


# Built at import time so pytest can collect one case per runnable block.
_RUNNABLE_BLOCKS: list[tuple[Path, int, str]] = [
    entry for entry in _ALL_BLOCKS if is_runnable(entry[2], _EXCLUSION_MARKERS)
]


def test_expected_runnable_blocks_discovered() -> None:
    """Guard against extraction or exclusion drift (runs in the default suite)."""
    assert len(_RUNNABLE_BLOCKS) == _EXPECTED_RUNNABLE_BLOCKS, (
        f"Expected exactly {_EXPECTED_RUNNABLE_BLOCKS} runnable documentation "
        f"examples but found {len(_RUNNABLE_BLOCKS)}. Either the examples "
        f"changed (update _EXPECTED_RUNNABLE_BLOCKS in "
        f"tests/test_documentation.py) or the block extraction and exclusion "
        f"markers no longer match the documentation."
    )


@pytest.fixture(scope="module")
def seed_award(client: USASpendingClient):
    """Fetch the award that continuation blocks reference, once per module."""
    return client.awards.find_by_award_id(_EXAMPLE_AWARD_ID)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("path", "index", "block"),
    _RUNNABLE_BLOCKS,
    ids=[
        f"{path.relative_to(DOCS_DIR).as_posix()}-block{index}"
        for path, index, _block in _RUNNABLE_BLOCKS
    ],
)
def test_documentation_block_executes(
    path: Path, index: int, block: str, client: USASpendingClient, seed_award
) -> None:
    """Execute a runnable documentation block verbatim against the live API.

    The namespace is pre-seeded so fragment blocks run as written: ``client``
    for blocks that reference a bare client, and ``award`` for blocks that
    continue from an award fetched in a preceding block. Blocks opening their
    own ``with USASpendingClient() as client:`` simply shadow the seeded value.
    """
    namespace = {
        "USASpendingClient": USASpendingClient,
        "client": client,
        "award": seed_award,
    }
    execute_block(block, f"{path.relative_to(ROOT)}:block{index}", namespace)


def _public_member_names() -> set[str]:
    """Return every public member name reachable from the documented modules.

    The module list is ``_SURFACE_SUBPACKAGES``, the same one the public-API
    snapshot uses, so prose is checked against exactly the surface that suite
    defends. Keeping a second list here let the two drift: this one omitted
    ``utils``, and so reported names like ``parse_date_string`` as nonexistent.
    """
    names: set[str] = set(dir(builtins))
    for module in (usaspending, *_SURFACE_SUBPACKAGES.values()):
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__.startswith("usaspending"):
                names.update(name for name in dir(obj) if not name.startswith("_"))
        names.update(name for name in dir(module) if not name.startswith("_"))
    return names


def test_methods_cited_in_prose_exist() -> None:
    """Method names cited in prose must exist on the public API.

    Executing the fenced examples cannot catch a method named only in prose, so
    a list of filters or a sentence recommending a call can go stale silently.
    This checks inline code spans of the form ``.name(`` outside fenced blocks.
    """
    known = _public_member_names()
    unknown: list[str] = []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        prose = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        unknown.extend(
            f"{path.relative_to(ROOT)}: .{match.group(1)}()"
            for match in re.finditer(r"`\.([a-z_][a-z0-9_]*)\(", prose)
            if match.group(1) not in known
        )

    assert unknown == [], f"Documentation cites methods that do not exist: {unknown}"


def _upstream_documentation_links() -> list[str]:
    """Return unique external links from the USAspending context pages."""
    links: set[str] = set()
    for path in sorted((DOCS_DIR / "usaspending-api").glob("*.md")):
        links.update(re.findall(r"https://[^)\s]+", path.read_text(encoding="utf-8")))
    return sorted(links)


def _is_transient_link_failure(status_code: int) -> bool:
    """Distinguish an upstream outage or rate limit from a permanently stale link."""
    return (
        status_code == HTTPStatus.TOO_MANY_REQUESTS
        or status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    )


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (HTTPStatus.OK, False),
        (HTTPStatus.NOT_FOUND, False),
        (HTTPStatus.TOO_MANY_REQUESTS, True),
        (HTTPStatus.INTERNAL_SERVER_ERROR, True),
        (HTTPStatus.SERVICE_UNAVAILABLE, True),
    ],
)
def test_transient_link_failure_classification(status_code, expected) -> None:
    """Only rate limits and server failures are treated as environmental."""
    assert _is_transient_link_failure(status_code) is expected


@pytest.mark.integration
@pytest.mark.parametrize("url", _upstream_documentation_links())
def test_upstream_documentation_link_resolves(url: str) -> None:
    """Canonical references should resolve without mistaking outages for link rot."""
    attempts = 2
    response = None
    for _attempt in range(attempts):
        response = requests.get(url, timeout=20, stream=True)
        if not _is_transient_link_failure(response.status_code):
            break
        response.close()

    assert response is not None
    with response:
        if _is_transient_link_failure(response.status_code):
            pytest.skip(f"Transient {response.status_code} from {url} after {attempts} attempts")
        assert response.status_code < HTTPStatus.BAD_REQUEST, f"{response.status_code} from {url}"
