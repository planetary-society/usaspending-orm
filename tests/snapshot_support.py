"""Shared snapshot (golden-file) support for the refactor safety-net tests.

Two suites record a JSON snapshot and compare later runs against it:
``tests/test_public_api_surface.py`` and
``tests/test_golden_master_integration.py``. Both need the same lifecycle, so
it lives here rather than being implemented twice and drifting apart on the one
behavior that makes them trustworthy.

The lifecycle is deliberately strict: a missing snapshot is a failure, not an
invitation to self-heal. Auto-creating would make a suite vacuously green
whenever the snapshot is absent (a fresh checkout that never committed it, or a
file deleted by accident), which is precisely when the guard is needed most.
Recording a new baseline is therefore an explicit, opt-in act.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_snapshot(
    path: Path,
    current: dict[str, Any],
    regen_env_var: str,
) -> dict[str, Any]:
    """Load a recorded JSON snapshot, regenerating it only when asked.

    Args:
        path: Snapshot file location.
        current: Freshly captured data, written only when regenerating.
        regen_env_var: Environment variable that, when set, rewrites the file so
            an intentional change lands as a reviewable diff.

    Returns:
        dict[str, Any]: The recorded snapshot to compare against.

    Raises:
        AssertionError: If the snapshot does not exist and regeneration was not
            requested.
    """
    if os.environ.get(regen_env_var):
        write_snapshot(path, current)

    if not path.exists():
        raise AssertionError(
            f"No recorded snapshot at {path}. This guard cannot pass without a "
            f"baseline. Record one with {regen_env_var}=1 and commit the result."
        )

    # Read back rather than returning `current` directly: the comparison should
    # run against exactly what is committed, so a JSON round-trip difference
    # surfaces now instead of on someone else's machine.
    with open(path) as handle:
        return json.load(handle)


def write_snapshot(path: Path, payload: dict[str, Any]) -> None:
    """Write a snapshot with stable, diff-friendly formatting.

    Args:
        path: Destination file.
        payload: Data to record.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
