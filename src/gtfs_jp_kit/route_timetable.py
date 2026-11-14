"""Route timetables: stops down, trips across (路線時刻表)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .calendar import DAY_TYPE_LABELS, ServiceCalendar
from .feed import Feed
from .timetable import parse_time


@dataclass
class RouteTimetable:
    route_name: str
    title: str
    stops: list[tuple[str, str]]  # (stop_id, stop_name)
    trips: list[dict[str, str]]  # trip rows, in departure order
    times: dict[str, dict[str, str]]  # trip_id -> stop_id -> "HH:MM"

    def row(self, stop_id: str) -> list[str]:
        return [self.times[t["trip_id"]].get(stop_id, "") for t in self.trips]


def merge_stop_orders(sequences: list[list[str]]) -> list[str]:
    """Merge stop sequences of several trips into one top-to-bottom order.

    Stops missing from the longest pattern are inserted just before the next
    stop of their own trip that is already placed (or at the end).

    >>> merge_stop_orders([["A", "B", "D"], ["A", "C", "D"]])
    ['A', 'B', 'C', 'D']
    """
    order: list[str] = []
    for seq in sorted(sequences, key=len, reverse=True):
        for i, sid in enumerate(seq):
            if sid in order:
                continue
            nxt = next((s for s in seq[i + 1 :] if s in order), None)
            if nxt is not None:
                order.insert(order.index(nxt), sid)
            else:
                order.append(sid)
    return order


def _hhmm(value: str, wrap: bool = False) -> str:
    secs = parse_time(value)
    if secs is None:
        return ""
    hour = secs // 3600
    return f"{hour % 24 if wrap else hour:02d}:{secs // 60 % 60:02d}"


def route_timetable(
    feed: Feed,
    route_id: str,
    *,
    direction: str | None = None,
    on: date | None = None,
    day_type: str = "weekday",
    lang: str = "en",
    wrap_midnight: bool = False,
) -> RouteTimetable:
    routes = feed["routes"].index("route_id")
    if route_id not in routes:
        raise KeyError(f"no route {route_id!r}")
    route = routes[route_id]
    cal = ServiceCalendar(feed)
    if on is not None:
        services, title = cal.active(on), on.isoformat()
    else:
        services = cal.day_type_services(day_type)
        title = DAY_TYPE_LABELS.get(lang, DAY_TYPE_LABELS["en"])[day_type]
    trips = [
        t
        for t in feed["trips"]
        if t.get("route_id") == route_id
        and t.get("service_id") in services
        and (direction is None or t.get("direction_id", "") == direction)
    ]
    ids = {t["trip_id"] for t in trips}
    seqs: dict[str, list[tuple[int, str, str]]] = {}
    for st in feed["stop_times"]:
        if st.get("trip_id") in ids:
            seqs.setdefault(st["trip_id"], []).append(
                (
                    int(st.get("stop_sequence") or 0),
                    st.get("stop_id", ""),
                    st.get("departure_time") or st.get("arrival_time", ""),
                )
            )
    times: dict[str, dict[str, str]] = {}
    orders: list[list[str]] = []
    first: dict[str, int] = {}
    for tid, rows in seqs.items():
        rows.sort()
        orders.append([sid for _, sid, _ in rows])
        times[tid] = {sid: _hhmm(t, wrap_midnight) for _, sid, t in rows}
        first[tid] = min((parse_time(t) or 0) for _, _, t in rows)
    trips = sorted((t for t in trips if t["trip_id"] in times), key=lambda t: first[t["trip_id"]])
    names = feed["stops"].index("stop_id")
    stops = [(sid, names.get(sid, {}).get("stop_name", sid)) for sid in merge_stop_orders(orders)]
    return RouteTimetable(
        route_name=route.get("route_short_name") or route.get("route_long_name", route_id),
        title=title,
        stops=stops,
        trips=trips,
        times=times,
    )
