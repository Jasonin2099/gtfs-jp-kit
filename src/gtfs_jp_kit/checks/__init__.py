"""GTFS-JP profile checks.

Each check is a function ``(feed) -> Iterable[Finding]`` registered in
:data:`CHECKS`. Checks whose result depends on the spec version also take a
``profile`` argument (see :mod:`gtfs_jp_kit.spec`). :func:`run_checks` runs
them all and sorts the result.
"""

from __future__ import annotations

from collections.abc import Iterable
from inspect import signature
from typing import Callable

from .. import spec
from ..feed import Feed
from ..findings import SEVERITIES, Finding
from . import legacy, references, structure, translations, values

Check = Callable[[Feed], Iterable[Finding]]

CHECKS: list[Check] = [
    structure.required_files,
    structure.conditional_files,
    structure.required_fields,
    structure.recommended_fields,
    structure.unneeded_fields,
    values.feed_info,
    values.agency,
    values.urls,
    values.routes,
    values.fares,
    translations.structure,
    translations.readings,
    references.attributions,
    references.stop_coordinates,
    references.fare_rules,
    references.trip_symbols,
    legacy.presence,
    legacy.references,
]


def run_checks(
    feed: Feed,
    checks: Iterable[Check] | None = None,
    profile: spec.Profile | str | None = None,
) -> list[Finding]:
    """Run the checks against ``feed`` with the ``"v4"`` (default) or ``"v3"`` profile."""
    prof = spec.get_profile(profile)
    found: list[Finding] = []
    for check in checks or CHECKS:
        if "profile" in signature(check).parameters:
            found.extend(check(feed, prof))
        else:
            found.extend(check(feed))
    order = {s: i for i, s in enumerate(SEVERITIES)}
    found.sort(key=lambda f: (order.get(f.severity, 9), f.file, f.line, f.code))
    return found


__all__ = ["CHECKS", "run_checks", "Finding"]
