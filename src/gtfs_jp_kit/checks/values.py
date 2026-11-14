"""Value rules that GTFS-JP adds on top of GTFS (the [JP] notes in v4)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date

from .. import corpnum
from ..feed import Feed
from ..findings import Finding

_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")


def _date(value: str) -> date | None:
    if len(value) != 8 or not value.isdigit():
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError:
        return None


def feed_info(feed: Feed) -> Iterator[Finding]:
    table = feed.get("feed_info")
    if table is None:
        return
    if len(table) != 1:
        yield Finding(
            "feed-info-rows",
            "error",
            f"feed_info.txt must have exactly one row (found {len(table)})",
            f"feed_info.txt はちょうど 1 行である必要があります（{len(table)} 行）",
            file="feed_info.txt",
            spec="§10",
        )
    for line, row in table.with_lines():
        lang = row.get("feed_lang", "")
        if lang and lang != "ja":
            yield Finding(
                "feed-lang-not-ja",
                "error",
                f'feed_lang must be "ja" (found "{lang}")',
                f"feed_lang は「ja」を設定します（現在「{lang}」）",
                file="feed_info.txt",
                line=line,
                field="feed_lang",
                spec="feed_info.txt",
            )
        start = _date(row.get("feed_start_date", ""))
        end = _date(row.get("feed_end_date", ""))
        for col, val in (("feed_start_date", start), ("feed_end_date", end)):
            if row.get(col) and val is None:
                yield Finding(
                    "bad-date",
                    "error",
                    f"{col} must be YYYYMMDD",
                    f"{col} は YYYYMMDD 形式で設定します",
                    file="feed_info.txt",
                    line=line,
                    field=col,
                )
        if start and end and start > end:
            yield Finding(
                "feed-period-reversed",
                "error",
                "feed_start_date is after feed_end_date",
                "feed_start_date が feed_end_date より後です",
                file="feed_info.txt",
                line=line,
            )
        elif start and end:
            yield from _calendar_outside_period(feed, start, end)


def _calendar_outside_period(feed: Feed, start: date, end: date) -> Iterator[Finding]:
    for line, row in feed["calendar"].with_lines():
        s, e = _date(row.get("start_date", "")), _date(row.get("end_date", ""))
        if (s and e) and (e < start or s > end):
            yield Finding(
                "service-outside-feed-period",
                "warning",
                f"service {row.get('service_id')} does not overlap the feed validity period",
                f"運行区分 {row.get('service_id')} がデータの有効期間と重なっていません",
                file="calendar.txt",
                line=line,
                field="service_id",
            )


def agency(feed: Feed) -> Iterator[Finding]:
    for line, row in feed["agency"].with_lines():
        tz = row.get("agency_timezone", "")
        if tz and tz != "Asia/Tokyo":
            yield Finding(
                "agency-timezone",
                "warning",
                f'agency_timezone is "{tz}"; domestic services use "Asia/Tokyo"',
                f"agency_timezone が「{tz}」です。国内は「Asia/Tokyo」を設定します",
                file="agency.txt",
                line=line,
                field="agency_timezone",
                spec="agency.txt",
            )
        lang = row.get("agency_lang", "")
        if lang and lang != "ja":
            yield Finding(
                "agency-lang",
                "warning",
                f'agency_lang is "{lang}"; domestic services use "ja"',
                f"agency_lang が「{lang}」です。国内は「ja」を設定します",
                file="agency.txt",
                line=line,
                field="agency_lang",
                spec="agency.txt",
            )
        agency_id = row.get("agency_id", "")
        if not agency_id:
            continue
        parsed = corpnum.parse_agency_id(agency_id)
        if parsed is None:
            yield Finding(
                "agency-id-not-corporate-number",
                "info",
                "agency_id is not a 13-digit corporate number (法人番号); this is recommended",
                "agency_id に法人番号（13 桁）を設定することが推奨されています",
                file="agency.txt",
                line=line,
                field="agency_id",
                spec="agency.txt",
            )
        elif not corpnum.is_valid(parsed[0]):
            yield Finding(
                "agency-id-check-digit",
                "warning",
                f"{parsed[0]} looks like a corporate number but its check digit is wrong",
                f"{parsed[0]} は法人番号の形式ですが、検査用数字が一致しません",
                file="agency.txt",
                line=line,
                field="agency_id",
                spec="agency.txt",
            )


def routes(feed: Feed) -> Iterator[Finding]:
    for line, row in feed["routes"].with_lines():
        color, text = row.get("route_color", ""), row.get("route_text_color", "")
        if color and not text:
            yield Finding(
                "route-text-color-missing",
                "error",
                "route_text_color must be set when route_color is set",
                "route_color を設定したときは route_text_color も設定します",
                file="routes.txt",
                line=line,
                field="route_text_color",
                spec="routes.txt",
            )
        for col, val in (("route_color", color), ("route_text_color", text)):
            if val and not _HEX.match(val):
                yield Finding(
                    "bad-color",
                    "error",
                    f"{col} must be a 6-digit hex color without #",
                    f"{col} は # なしの 6 桁の 16 進数で設定します",
                    file="routes.txt",
                    line=line,
                    field=col,
                )
        if color and text and _HEX.match(color) and _HEX.match(text):
            ratio = contrast(color, text)
            if ratio < 3:
                yield Finding(
                    "route-color-contrast",
                    "warning",
                    f"route_color / route_text_color contrast is {ratio:.1f}:1 (below 3:1)",
                    f"ルートの色と文字色のコントラストが {ratio:.1f}:1 で低すぎます",
                    file="routes.txt",
                    line=line,
                    field="route_text_color",
                )


def _luminance(hex6: str) -> float:
    def ch(i: int) -> float:
        c = int(hex6[i : i + 2], 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(0) + 0.7152 * ch(2) + 0.0722 * ch(4)


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two hex colors.

    >>> round(contrast("000000", "FFFFFF"), 1)
    21.0
    """
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def fares(feed: Feed) -> Iterator[Finding]:
    for line, row in feed["fare_attributes"].with_lines():
        cur = row.get("currency_type", "")
        if cur and cur != "JPY":
            yield Finding(
                "fare-currency",
                "warning",
                f'currency_type is "{cur}"; domestic fares use "JPY"',
                f"currency_type が「{cur}」です。国内の運賃は「JPY」です",
                file="fare_attributes.txt",
                line=line,
                field="currency_type",
            )
        price = row.get("price", "")
        if cur == "JPY" and price and not re.fullmatch(r"\d+(\.0+)?", price):
            yield Finding(
                "fare-price-yen",
                "error",
                f'price "{price}" is not a whole number of yen',
                f"price「{price}」が円の整数になっていません",
                file="fare_attributes.txt",
                line=line,
                field="price",
            )
    zones = {r.get("zone_id", "") for r in feed["stops"]} - {""}
    uses_zones = any(
        r.get(c) for r in feed["fare_rules"] for c in ("origin_id", "destination_id", "contains_id")
    )
    if uses_zones and not zones:
        yield Finding(
            "zone-id-missing",
            "error",
            "fare_rules.txt uses zones but no stop has a zone_id",
            "fare_rules.txt で区間を使っていますが、stops.txt に zone_id がありません",
            file="stops.txt",
            field="zone_id",
            spec="参考3",
        )
