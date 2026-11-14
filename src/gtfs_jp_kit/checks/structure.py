"""File and field presence rules (§8.2 and （参考 3）)."""

from __future__ import annotations

from collections.abc import Iterator

from .. import spec
from ..feed import Feed
from ..findings import Finding

#: Report at most this many row-level findings per rule and file; the rest is
#: folded into one summary finding so that a broken feed stays readable.
MAX_ROWS = 20


def required_files(feed: Feed) -> Iterator[Finding]:
    for name in spec.REQUIRED_FILES:
        if not feed.has(name):
            yield Finding(
                "missing-required-file",
                "error",
                f"{name} is required by GTFS-JP",
                f"{name} は GTFS-JP で必須のファイルです",
                file=name,
                spec="§8.2",
            )
    if not any(feed.has(n) for n in spec.CALENDAR_FILES):
        yield Finding(
            "missing-calendar",
            "error",
            "either calendar.txt or calendar_dates.txt is required",
            "calendar.txt と calendar_dates.txt のどちらかが必要です",
            spec="§8.2",
        )
    for name in spec.RECOMMENDED_FILES:
        if not feed.has(name):
            yield Finding(
                "missing-recommended-file",
                "info",
                f"{name} is recommended by GTFS-JP",
                f"{name} の作成が推奨されています",
                file=name,
                spec="§8.2",
            )


def _uses_continuous_stops(feed: Feed) -> bool:
    for table in ("routes", "stop_times"):
        for row in feed[table]:
            for col in ("continuous_pickup", "continuous_drop_off"):
                if row.get(col, "") in ("0", "2", "3"):
                    return True
    return False


def conditional_files(feed: Feed) -> Iterator[Finding]:
    # fare_rules.txt: required unless every route has the same flat fare.
    fares = {r.get("fare_id", "") for r in feed["fare_attributes"]} - {""}
    if len(fares) > 1 and not feed.has("fare_rules"):
        yield Finding(
            "missing-fare-rules",
            "error",
            "fare_rules.txt is required when there is more than one fare",
            "運賃が複数あるため fare_rules.txt が必要です（均一運賃以外は必須）",
            file="fare_rules.txt",
            spec="§8.2",
        )
    # shapes.txt: required with continuous pickup/drop-off (フリー乗降).
    if not feed.has("shapes"):
        if _uses_continuous_stops(feed):
            yield Finding(
                "missing-shapes",
                "error",
                "shapes.txt is required when continuous pickup/drop-off is used",
                "フリー乗降（continuous_pickup/drop_off）があるため shapes.txt が必要です",
                file="shapes.txt",
                spec="§8.2",
            )
        else:
            yield Finding(
                "missing-shapes",
                "info",
                "shapes.txt is recommended for fixed-route services",
                "定路線のルートでは shapes.txt の作成が推奨されています",
                file="shapes.txt",
                spec="§8.2",
            )
    # levels.txt: required when a pathway is an elevator (pathway_mode=5).
    if any(r.get("pathway_mode") == "5" for r in feed["pathways"]) and not feed.has("levels"):
        yield Finding(
            "missing-levels",
            "error",
            "levels.txt is required when pathways.txt has elevators",
            "pathways.txt にエレベーターがあるため levels.txt が必要です",
            file="levels.txt",
            spec="§8.2",
        )
    # networks.txt / route_networks.txt: forbidden when routes.network_id is used.
    if any(r.get("network_id") for r in feed["routes"]):
        for name in ("networks.txt", "route_networks.txt"):
            if feed.has(name):
                yield Finding(
                    "forbidden-file",
                    "error",
                    f"{name} must not exist when routes.txt uses network_id",
                    f"routes.txt に network_id があるため {name} は禁止です",
                    file=name,
                    spec="§8.2",
                )


def required_fields(feed: Feed) -> Iterator[Finding]:
    for name, fields in spec.REQUIRED_FIELDS.items():
        table = feed.get(name)
        if table is None:
            continue
        for col in fields:
            if col not in table.columns:
                yield Finding(
                    "missing-required-field",
                    "error",
                    f"column {col} is required by GTFS-JP",
                    f"{col} は GTFS-JP で必須の項目です",
                    file=name,
                    field=col,
                    spec="参考3",
                )
                continue
            empty = [line for line, row in table.with_lines() if not row.get(col)]
            for line in empty[:MAX_ROWS]:
                yield Finding(
                    "empty-required-field",
                    "error",
                    f"{col} is empty",
                    f"必須項目 {col} が空です",
                    file=name,
                    line=line,
                    field=col,
                    spec="参考3",
                )
            if len(empty) > MAX_ROWS:
                yield Finding(
                    "empty-required-field",
                    "error",
                    f"{len(empty) - MAX_ROWS} more rows with empty {col}",
                    f"ほかに {len(empty) - MAX_ROWS} 行で {col} が空です",
                    file=name,
                    field=col,
                    spec="参考3",
                )


def recommended_fields(feed: Feed) -> Iterator[Finding]:
    for name, fields in spec.RECOMMENDED_FIELDS.items():
        table = feed.get(name)
        if table is None or not len(table):
            continue
        for col in fields:
            rows = table.rows
            if col == "platform_code":
                # Only platforms/poles inside a station can have a platform code.
                rows = [r for r in rows if r.get("parent_station")]
            missing = sum(1 for row in rows if not row.get(col))
            if missing:
                yield Finding(
                    "recommended-field-empty",
                    "info",
                    f"{col} is recommended but empty in {missing} of {len(rows)} rows",
                    f"推奨項目 {col} が {len(rows)} 行中 {missing} 行で未設定です",
                    file=name,
                    field=col,
                    spec="参考3",
                )


def unneeded_fields(feed: Feed) -> Iterator[Finding]:
    for name, fields in spec.UNNEEDED_FIELDS.items():
        table = feed.get(name)
        if table is None:
            continue
        for col in fields:
            if any(row.get(col) for row in table):
                yield Finding(
                    "unneeded-field",
                    "info",
                    f"{col} is not needed for domestic feeds",
                    f"{col} は国内向けデータでは設定不要です",
                    file=name,
                    field=col,
                    spec="参考3",
                )
