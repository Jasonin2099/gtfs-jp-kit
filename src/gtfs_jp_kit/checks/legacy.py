"""GTFS-JP v3 extension files and GTFS-JP first-edition leftovers.

v4 moved agency_jp.txt, office_jp.txt and pattern_jp.txt to （参考 1）: they
are no longer needed but may still be included when a consumer relies on
them. When they are present, their references are still checked.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from .. import spec
from ..feed import Feed
from ..findings import Finding

_ZIP = re.compile(r"^\d{7}$")


def presence(feed: Feed, profile: spec.Profile | str | None = None) -> Iterator[Finding]:
    legacy_v3 = spec.get_profile(profile).v3_extensions_are_legacy
    for name in spec.V3_EXTENSION_FILES:
        if legacy_v3 and feed.has(name):
            yield Finding(
                "v3-extension-file",
                "info",
                f"{name} is a GTFS-JP v3 extension; v4 no longer requires it",
                f"{name} は GTFS-JP 第3版の拡張ファイルです。第4版では作成不要です（参考扱い）",
                file=name,
                spec="参考1",
            )
    for name in spec.V1_LEGACY_FILES:
        if feed.has(name):
            yield Finding(
                "v1-legacy-file",
                "warning",
                f"{name} is from the first edition of GTFS-JP; use translations.txt and "
                "routes.txt (jp_parent_route_id) instead",
                f"{name} は GTFS-JP 初版のファイルです。"
                "translations.txt と jp_parent_route_id を使ってください",
                file=name,
            )


def references(feed: Feed) -> Iterator[Finding]:
    agencies = {r.get("agency_id", "") for r in feed["agency"]}
    for line, row in feed["agency_jp"].with_lines():
        if row.get("agency_id", "") not in agencies:
            yield Finding(
                "agency-jp-unknown-agency",
                "error",
                f"agency_id {row.get('agency_id')!r} is not in agency.txt",
                f"agency_id「{row.get('agency_id')}」が agency.txt にありません",
                file="agency_jp.txt",
                line=line,
                field="agency_id",
                spec="参考1",
            )
        zipcode = row.get("agency_zip_number", "")
        if zipcode and not _ZIP.match(zipcode):
            yield Finding(
                "agency-jp-zip",
                "warning",
                "agency_zip_number must be 7 half-width digits without a hyphen",
                "agency_zip_number はハイフンなしの半角数字 7 桁で設定します",
                file="agency_jp.txt",
                line=line,
                field="agency_zip_number",
                spec="参考1",
            )
    offices = feed.get("office_jp")
    office_ids: set[str] = set()
    if offices is not None:
        for line, row in offices.with_lines():
            office_ids.add(row.get("office_id", ""))
            if not row.get("office_name"):
                yield Finding(
                    "office-jp-name",
                    "error",
                    "office_name is required in office_jp.txt",
                    "office_jp.txt の office_name は必須です",
                    file="office_jp.txt",
                    line=line,
                    field="office_name",
                    spec="参考1",
                )
    patterns = feed.get("pattern_jp")
    pattern_ids = {r.get("jp_pattern_id", "") for r in patterns} if patterns is not None else None
    bad_office: dict[str, int] = {}
    bad_pattern: dict[str, int] = {}
    for line, row in feed["trips"].with_lines():
        oid = row.get("jp_office_id", "")
        if oid and oid not in office_ids:
            bad_office.setdefault(oid, line)
        pid = row.get("jp_pattern_id", "")
        if pid and pattern_ids is not None and pid not in pattern_ids:
            bad_pattern.setdefault(pid, line)
    for oid, line in bad_office.items():
        yield Finding(
            "trip-unknown-office",
            "error",
            f"jp_office_id {oid!r} is not defined in office_jp.txt",
            f"jp_office_id「{oid}」が office_jp.txt にありません",
            file="trips.txt",
            line=line,
            field="jp_office_id",
            spec="参考1",
        )
    for pid, line in bad_pattern.items():
        yield Finding(
            "trip-unknown-pattern",
            "warning",
            f"jp_pattern_id {pid!r} is not listed in pattern_jp.txt",
            f"jp_pattern_id「{pid}」が pattern_jp.txt にありません",
            file="trips.txt",
            line=line,
            field="jp_pattern_id",
            spec="参考1",
        )
