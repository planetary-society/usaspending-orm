"""Helpers for building deterministic request payloads."""

from __future__ import annotations

from typing import Any


def canonical_order(values: Any) -> list[Any]:
    """Return match-any payload values in a deterministic order.

    The keys this is applied to are match-any sets upstream, so the order of
    their values carries no meaning to the API. It matters here because the
    response cache keys on the serialized payload, and several of these
    collections originate as a ``frozenset`` of award type codes. Hash
    randomization reorders a set differently in every process, so without this
    the same logical request serializes differently on every run and the
    on-disk cache never hits.

    Apply this wherever a set-derived collection becomes part of a request,
    which is both the filter objects in ``queries/filters.py`` and the query
    builders that assemble GET parameters without going through a filter.

    Args:
        values: The values, in whatever order they were supplied.

    Returns:
        list[Any]: The values sorted, or in their original order when they are
        not mutually comparable (program activities, for instance, are dicts,
        which never come from a set and so are already deterministic).
    """
    try:
        return sorted(values)
    except TypeError:
        return list(values)
