"""Passenger-facing differences between two feed versions (ダイヤ改正).

This is deliberately narrow: it answers "what changes at this stop?" and
"which stops and routes appear or disappear?", the things a 改正のお知らせ
needs. For a full semantic diff of two feeds, see gtfs-semantic-diff.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .calendar import DAY_TYPES
from .feed import Feed
from .timetable import stop_timetable

Key = tuple[int, str, str]  # (seconds, route, headsign)


@dataclass
class ColumnDiff:
    column: str
    added: list[Key] = field(default_factory=list)
    removed: list[Key] = field(default_factory=list)
    shifted: list[tuple[Key, Key]] = field(default_factory=list)
    before: int = 0
    after: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed or self.shifted)


def _hhmm(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}"


def diff_departures(old: list[Key], new: list[Key], column: str, window: int = 600) -> ColumnDiff:
    """Multiset difference, pairing removed/added departures of the same
    route and headsign that moved by at most ``window`` seconds.

    >>> d = diff_departures([(25200, "1", "駅"), (28800, "1", "駅")],
    ...                     [(25500, "1", "駅"), (28800, "1", "駅")], "平日")
    >>> d.shifted
    [((25200, '1', '駅'), (25500, '1', '駅'))]
    """
    a, b = Counter(old), Counter(new)
    removed = sorted((a - b).elements())
    added = sorted((b - a).elements())
    shifted: list[tuple[Key, Key]] = []
    for r in list(removed):
        candidates = [x for x in added if x[1:] == r[1:] and abs(x[0] - r[0]) <= window]
        if candidates:
            best = min(candidates, key=lambda x: abs(x[0] - r[0]))
            shifted.append((r, best))
            removed.remove(r)
            added.remove(best)
    return ColumnDiff(column, added, removed, shifted, before=len(old), after=len(new))


def stop_diff(
    old: Feed, new: Feed, stop: str, day_types: tuple[str, ...] = DAY_TYPES, lang: str = "en"
) -> list[ColumnDiff]:
    out = []
    a = stop_timetable(old, stop, day_types=day_types, lang=lang)
    b = stop_timetable(new, stop, day_types=day_types, lang=lang)
    for col in a.columns:
        ka = [(d.seconds, d.route_name, d.headsign) for d in a.departures[col]]
        kb = [(d.seconds, d.route_name, d.headsign) for d in b.departures.get(col, [])]
        out.append(diff_departures(ka, kb, col))
    return out


@dataclass
class FeedDiff:
    version: tuple[str, str]
    period: tuple[str, str]
    stops_added: list[str]
    stops_removed: list[str]
    stops_renamed: list[tuple[str, str, str]]
    routes_added: list[str]
    routes_removed: list[str]


def feed_diff(old: Feed, new: Feed) -> FeedDiff:
    def info(f: Feed) -> dict[str, str]:
        return f["feed_info"].rows[0] if len(f["feed_info"]) else {}

    ia, ib = info(old), info(new)
    sa, sb = old["stops"].index("stop_id"), new["stops"].index("stop_id")
    ra, rb = old["routes"].index("route_id"), new["routes"].index("route_id")

    def rname(r: dict[str, str]) -> str:
        return " ".join(x for x in (r.get("route_short_name"), r.get("route_long_name")) if x)

    return FeedDiff(
        version=(ia.get("feed_version", ""), ib.get("feed_version", "")),
        period=(
            f"{ia.get('feed_start_date', '')}-{ia.get('feed_end_date', '')}",
            f"{ib.get('feed_start_date', '')}-{ib.get('feed_end_date', '')}",
        ),
        stops_added=sorted(f"{sb[k].get('stop_name', '')} ({k})" for k in set(sb) - set(sa)),
        stops_removed=sorted(f"{sa[k].get('stop_name', '')} ({k})" for k in set(sa) - set(sb)),
        stops_renamed=sorted(
            (k, sa[k].get("stop_name", ""), sb[k].get("stop_name", ""))
            for k in set(sa) & set(sb)
            if sa[k].get("stop_name") != sb[k].get("stop_name")
        ),
        routes_added=sorted(f"{rname(rb[k])} ({k})" for k in set(rb) - set(ra)),
        routes_removed=sorted(f"{rname(ra[k])} ({k})" for k in set(ra) - set(rb)),
    )


def render_stop_diff(stop: str, diffs: list[ColumnDiff], lang: str = "en") -> str:
    ja = lang == "ja"
    lines = [f"## {stop}"]
    for d in diffs:
        count = f"{d.before} → {d.after}" + (" 本" if ja else " departures")
        lines.append(f"\n### {d.column} ({count})")
        if not d.changed:
            lines.append("変更なし" if ja else "no change")
            continue
        for r, a in d.shifted:
            lines.append(f"- {_hhmm(r[0])} → {_hhmm(a[0])}  {r[1]} {r[2]}")
        for k in d.added:
            lines.append(f"- {'新設' if ja else 'new'} {_hhmm(k[0])}  {k[1]} {k[2]}")
        for k in d.removed:
            lines.append(f"- {'廃止' if ja else 'removed'} {_hhmm(k[0])}  {k[1]} {k[2]}")
    return "\n".join(lines) + "\n"


def render_feed_diff(d: FeedDiff, lang: str = "en") -> str:
    ja = lang == "ja"
    lines = [
        f"{'版' if ja else 'Version'}: {d.version[0]} → {d.version[1]}",
        f"{'有効期間' if ja else 'Valid'}: {d.period[0]} → {d.period[1]}",
    ]
    renamed = [f"{a} → {b} ({k})" for k, a, b in d.stops_renamed]
    groups = [
        ("新設停留所" if ja else "Stops added", d.stops_added),
        ("廃止停留所" if ja else "Stops removed", d.stops_removed),
        ("名称変更" if ja else "Stops renamed", renamed),
        ("新設路線" if ja else "Routes added", d.routes_added),
        ("廃止路線" if ja else "Routes removed", d.routes_removed),
    ]
    for title, items in groups:
        if items:
            lines.append(f"{title}:")
            lines.extend(f"  - {x}" for x in items)
    return "\n".join(lines) + "\n"
