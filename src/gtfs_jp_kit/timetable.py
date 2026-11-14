"""Japanese-style stop timetables (停留所時刻表).

A stop timetable lists the minutes of each departure in one row per hour,
with one column per day type (平日 / 土曜 / 日曜・祝日), the way timetables
are posted at Japanese bus stops. Departures to a less common destination
and trips with ``jp_trip_desc_symbol`` get a mark that is explained in a
legend.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from .calendar import DAY_TYPE_LABELS, DAY_TYPES, ServiceCalendar
from .feed import Feed


def parse_time(value: str) -> int | None:
    """Seconds after midnight of the service day; GTFS allows hours ≥ 24.

    >>> parse_time("25:10:00")
    90600
    >>> parse_time("7:05:00")
    25500
    """
    parts = value.strip().split(":")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    h, m, s = (int(p) for p in parts)
    return h * 3600 + m * 60 + s


@dataclass(frozen=True)
class Departure:
    seconds: int
    trip_id: str
    route_id: str
    route_name: str
    headsign: str
    service_id: str
    stop_id: str
    symbol: str = ""
    desc: str = ""

    @property
    def hour(self) -> int:
        return self.seconds // 3600

    @property
    def minute(self) -> int:
        return self.seconds // 60 % 60

    @property
    def hhmm(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"


def resolve_stops(feed: Feed, query: str) -> list[str]:
    """Stop IDs for a stop_id, a station (with its platforms) or an exact stop_name."""
    stops = feed["stops"]
    by_id = stops.index("stop_id")
    if query in by_id:
        ids = [query]
    else:
        ids = [r["stop_id"] for r in stops if r.get("stop_name") == query]
    out: list[str] = []
    for sid in ids:
        out.append(sid)
        out.extend(r["stop_id"] for r in stops if r.get("parent_station") == sid)
    return list(dict.fromkeys(out))


def _route_names(feed: Feed) -> dict[str, str]:
    return {
        r.get("route_id", ""): r.get("route_short_name") or r.get("route_long_name", "")
        for r in feed["routes"]
    }


def departures(
    feed: Feed,
    stop_ids: list[str],
    services: set[str],
    routes: set[str] | None = None,
) -> list[Departure]:
    """Boardable departures at ``stop_ids`` for trips of ``services``.

    The last stop of a trip and stops with ``pickup_type=1`` are skipped
    because nobody can board there.
    """
    wanted = set(stop_ids)
    trips = {
        t["trip_id"]: t
        for t in feed["trips"]
        if t.get("service_id") in services and (routes is None or t.get("route_id") in routes)
    }
    by_trip: dict[str, list[dict[str, str]]] = {}
    for st in feed["stop_times"]:
        if st.get("trip_id") in trips:
            by_trip.setdefault(st["trip_id"], []).append(st)
    names = _route_names(feed)
    out: list[Departure] = []
    for trip_id, sts in by_trip.items():
        sts.sort(key=lambda r: int(r.get("stop_sequence") or 0))
        trip = trips[trip_id]
        for st in sts[:-1]:
            if st.get("stop_id") not in wanted or st.get("pickup_type") == "1":
                continue
            secs = parse_time(st.get("departure_time") or st.get("arrival_time", ""))
            if secs is None:
                continue
            out.append(
                Departure(
                    seconds=secs,
                    trip_id=trip_id,
                    route_id=trip.get("route_id", ""),
                    route_name=names.get(trip.get("route_id", ""), ""),
                    headsign=st.get("stop_headsign") or trip.get("trip_headsign", ""),
                    service_id=trip.get("service_id", ""),
                    stop_id=st["stop_id"],
                    symbol=trip.get("jp_trip_desc_symbol", ""),
                    desc=trip.get("jp_trip_desc", ""),
                )
            )
    out.sort(key=lambda d: (d.seconds, d.route_id, d.trip_id))
    return out


@dataclass
class StopTimetable:
    stop_name: str
    columns: list[str]  # labels, e.g. 平日 / 土曜 / 日曜・祝日 or a date
    departures: dict[str, list[Departure]]
    marks: dict[tuple[str, str], str] = field(default_factory=dict)  # (route, headsign) -> mark
    symbols: dict[str, str] = field(default_factory=dict)  # symbol -> description

    @property
    def hours(self) -> list[int]:
        hs = {d.hour for deps in self.departures.values() for d in deps}
        return list(range(min(hs), max(hs) + 1)) if hs else []

    def cell(self, column: str, hour: int) -> list[str]:
        out = []
        for d in self.departures[column]:
            if d.hour == hour:
                mark = self.marks.get((d.route_name, d.headsign), "") + d.symbol
                out.append(f"{mark}{d.minute:02d}")
        return out

    def legend(self, lang: str = "en") -> list[str]:
        lines = []
        for (route, headsign), mark in self.marks.items():
            if lang == "ja":
                label = f"{route} {headsign}行き".strip()
                lines.append(f"{mark or '無印'}：{label}")
            else:
                label = f"route {route} to {headsign}" if route else f"to {headsign}"
                lines.append(f"{mark or '(no mark)'}: {label}")
        for sym, desc in self.symbols.items():
            lines.append(f"{sym}: {desc}")
        return lines


def _assign_marks(deps: list[Departure]) -> dict[tuple[str, str], str]:
    counts = Counter((d.route_name, d.headsign) for d in deps)
    if len(counts) <= 1:
        return {k: "" for k in counts}
    ordered = [k for k, _ in counts.most_common()]
    marks = {ordered[0]: ""}
    used: set[str] = set()
    fallback = iter("ABCDEFGHJKLMNPQRSTUVWXYZ")
    for key in ordered[1:]:
        first = key[1][:1] or key[0][:1]
        mark = first if first and first not in used else next(fallback)
        used.add(mark)
        marks[key] = mark
    return marks


def stop_timetable(
    feed: Feed,
    stop: str,
    *,
    on: date | None = None,
    day_types: tuple[str, ...] = DAY_TYPES,
    routes: set[str] | None = None,
    lang: str = "en",
) -> StopTimetable:
    """Build a stop timetable for one date or for the regular day types."""
    stop_ids = resolve_stops(feed, stop)
    if not stop_ids:
        raise KeyError(f"no stop with id or name {stop!r}")
    stop_name = feed["stops"].index("stop_id")[stop_ids[0]].get("stop_name", stop)
    cal = ServiceCalendar(feed)
    if on is not None:
        groups = {on.isoformat(): cal.active(on)}
    else:
        labels = DAY_TYPE_LABELS.get(lang, DAY_TYPE_LABELS["en"])
        groups = {labels[t]: cal.day_type_services(t) for t in day_types}
    deps = {
        label: departures(feed, stop_ids, services, routes) for label, services in groups.items()
    }
    every = [d for ds in deps.values() for d in ds]
    symbols = {d.symbol: d.desc for d in every if d.symbol}
    return StopTimetable(
        stop_name=stop_name,
        columns=list(groups),
        departures=deps,
        marks=_assign_marks(every),
        symbols=dict(sorted(symbols.items())),
    )
