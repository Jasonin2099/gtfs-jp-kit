"""GTFS-JP profile checks.

Each check is a function ``(feed) -> Iterable[Finding]`` registered in
:data:`CHECKS`. :func:`run_checks` runs them all and sorts the result.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Callable

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


def run_checks(feed: Feed, checks: Iterable[Check] | None = None) -> list[Finding]:
    found: list[Finding] = []
    for check in checks or CHECKS:
        found.extend(check(feed))
    order = {s: i for i, s in enumerate(SEVERITIES)}
    found.sort(key=lambda f: (order.get(f.severity, 9), f.file, f.line, f.code))
    return found


__all__ = ["CHECKS", "run_checks", "Finding"]
