"""Cross-file checks for GTFS-JP specific fields and files."""

from __future__ import annotations

from collections.abc import Iterator

from ..feed import Feed
from ..findings import Finding

#: Rough bounding box of Japan, including remote islands (南鳥島, 与那国島, 沖ノ鳥島).
JAPAN_LAT = (20.0, 46.0)
JAPAN_LON = (122.0, 154.0)


def attributions(feed: Feed) -> Iterator[Finding]:
    for line, row in feed["attributions"].with_lines():
        if not any(row.get(c) == "1" for c in ("is_producer", "is_operator", "is_authority")):
            yield Finding(
                "attribution-role",
                "error",
                "one of is_producer, is_operator, is_authority must be 1",
                "is_producer・is_operator・is_authority のいずれかを 1 にします",
                file="attributions.txt",
                line=line,
                spec="参考3",
            )


def stop_coordinates(feed: Feed) -> Iterator[Finding]:
    for line, row in feed["stops"].with_lines():
        try:
            lat, lon = float(row.get("stop_lat", "")), float(row.get("stop_lon", ""))
        except ValueError:
            continue
        in_lat = JAPAN_LAT[0] <= lat <= JAPAN_LAT[1]
        in_lon = JAPAN_LON[0] <= lon <= JAPAN_LON[1]
        if in_lat and in_lon:
            continue
        swapped = JAPAN_LAT[0] <= lon <= JAPAN_LAT[1] and JAPAN_LON[0] <= lat <= JAPAN_LON[1]
        yield Finding(
            "stop-outside-japan",
            "warning",
            f"stop {row.get('stop_id')} ({lat}, {lon}) is outside Japan"
            + ("; stop_lat and stop_lon look swapped" if swapped else ""),
            f"停留所 {row.get('stop_id')}（{lat}, {lon}）が日本の範囲外です"
            + ("。緯度と経度が逆になっている可能性があります" if swapped else ""),
            file="stops.txt",
            line=line,
            field="stop_lat",
        )


def fare_rules(feed: Feed) -> Iterator[Finding]:
    fares = {r.get("fare_id", "") for r in feed["fare_attributes"]}
    routes = {r.get("route_id", "") for r in feed["routes"]}
    zones = {r.get("zone_id", "") for r in feed["stops"]} - {""}
    for line, row in feed["fare_rules"].with_lines():
        problems = []
        if row.get("fare_id", "") not in fares:
            problems.append(("fare_id", row.get("fare_id", ""), "fare_attributes.txt"))
        if row.get("route_id") and row["route_id"] not in routes:
            problems.append(("route_id", row["route_id"], "routes.txt"))
        for col in ("origin_id", "destination_id", "contains_id"):
            if row.get(col) and zones and row[col] not in zones:
                problems.append((col, row[col], "stops.txt zone_id"))
        for col, value, target in problems:
            yield Finding(
                "fare-rule-reference",
                "error",
                f"{col} {value!r} is not defined in {target}",
                f"{col}「{value}」が {target} にありません",
                file="fare_rules.txt",
                line=line,
                field=col,
            )


def trip_symbols(feed: Feed) -> Iterator[Finding]:
    seen: set[str] = set()
    for line, row in feed["trips"].with_lines():
        sym = row.get("jp_trip_desc_symbol", "")
        if sym and not row.get("jp_trip_desc") and sym not in seen:
            seen.add(sym)
            yield Finding(
                "trip-symbol-without-desc",
                "warning",
                f"jp_trip_desc_symbol {sym!r} has no jp_trip_desc to explain it",
                f"jp_trip_desc_symbol「{sym}」の説明（jp_trip_desc）がありません",
                file="trips.txt",
                line=line,
                field="jp_trip_desc",
                spec="trips.txt",
            )
