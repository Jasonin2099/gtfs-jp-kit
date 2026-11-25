"""Value rules that GTFS-JP adds on top of GTFS (the [JP] notes in v4)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from datetime import date
from urllib.parse import urlparse

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
        yield from _phone(row.get("agency_phone", ""), "agency.txt", line, "agency_phone")
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


_PHONE_CHARS = re.compile(r"^\+?[0-9()\- ]+$")
#: Domestic numbers with 11 digits: 020 / 050 / 060 / 070 / 080 / 090 and 0800.
_PHONE_11 = re.compile(r"^(?:0[2-9]0|0800)")


def _phone(value: str, file: str, line: int, field: str) -> Iterator[Finding]:
    if not value:
        return
    problem = phone_problem(value)
    if problem:
        yield Finding(
            "bad-phone",
            "warning",
            f"{field} {value!r}: {problem[0]}",
            f"{field}「{value}」：{problem[1]}",
            file=file,
            line=line,
            field=field,
            spec=file,
        )
    elif value.isdigit():
        yield Finding(
            "phone-no-hyphen",
            "info",
            f"{field} {value!r} has no hyphens; GTFS-JP writes phone numbers with hyphens "
            "(e.g. 03-5253-8111)",
            f"{field}「{value}」にハイフンがありません。電話番号はハイフン入りで設定します"
            "（例：03-5253-8111）",
            file=file,
            line=line,
            field=field,
            spec="§4.13",
        )


def attributions(feed: Feed) -> Iterator[Finding]:
    for line, row in feed["attributions"].with_lines():
        yield from _phone(
            row.get("attribution_phone", ""), "attributions.txt", line, "attribution_phone"
        )


def phone_problem(value: str) -> tuple[str, str] | None:
    """Why ``value`` is not a dialable Japanese phone number, as (en, ja), or None.

    Looks for full-width characters, notes mixed into the field and digit counts
    that cannot be a domestic number (10 digits, 11 for 0X0 / 0800, or +81 without
    the leading 0). Missing hyphens are not a problem here: GTFS-JP §4.13 asks for
    half-width digits with hyphens, which the checks report separately as info
    (``phone-no-hyphen``), because where the hyphens go depends on the area code.

    >>> phone_problem("03-2816-5700") is None
    True
    >>> phone_problem("０３－２８１６－５７００")[0]
    'full-width characters; use half-width (03-2816-5700)'
    """
    half = unicodedata.normalize("NFKC", value)
    half = re.sub(r"[\u2010-\u2015\u2212\u30fc]", "-", half)
    if not _PHONE_CHARS.match(half):
        return (
            "only the phone number goes here (no notes, hours or extensions)",
            "電話番号以外の文字（受付時間・注記など）が含まれています",
        )
    if half != value:
        return (
            f"full-width characters; use half-width ({half})",
            f"全角の数字・記号があります。半角にしてください（{half}）",
        )
    digits = re.sub(r"\D", "", value)
    if value.startswith("+"):
        if not digits.startswith("81") or len(digits) - 2 not in (9, 10):
            return (
                "not a Japanese number in +81 form",
                "+81 形式の日本の電話番号になっていません",
            )
        return None
    if not digits.startswith("0"):
        return ("domestic numbers start with 0", "国内の電話番号は 0 から始まります")
    want = 11 if _PHONE_11.match(digits) else 10
    if len(digits) != want:
        return (
            f"{len(digits)} digits; domestic numbers have 10 (11 for 0X0 / 0800)",
            f"{len(digits)} 桁です（国内の番号は 10 桁、0X0・0800 で始まる番号は 11 桁）",
        )
    return None


#: Words that GTFS-JP says must not be part of platform_code (「番線」「のりば」等).
_PLATFORM_WORDS = re.compile(r"番線|番のりば|番乗り?場|のりば|乗り?場|番ホーム|platform", re.I)
_ALNUM = r"[0-9A-Za-z０-９Ａ-Ｚａ-ｚ]"
#: A platform number inside a stop_name: 「1番のりば」「のりばA」「3番線」「(2番)」.
#: Plain parentheses such as 「博多駅(JR)」 are sub-names and are not matched.
_NAME_PLATFORM = re.compile(
    rf"{_ALNUM}+\s*(?:番?\s*(?:のりば|乗り?場)|番線)|(?:のりば|乗り?場)\s*{_ALNUM}+"
    r"|[(（][0-9０-９]+番[)）]"
)


def platform_code_fix(value: str) -> str:
    """``value`` with the words GTFS-JP forbids in platform_code removed.

    >>> platform_code_fix("1番のりば")
    '1'
    >>> platform_code_fix("のりばA")
    'A'
    >>> platform_code_fix("センタービル前")
    'センタービル前'
    """
    return _PLATFORM_WORDS.sub("", value).strip(" 　-")


def stops(feed: Feed) -> Iterator[Finding]:
    table = feed["stops"]
    for line, row in table.with_lines():
        code = row.get("platform_code", "")
        if code and _PLATFORM_WORDS.search(code):
            fixed = platform_code_fix(code)
            yield Finding(
                "platform-code-words",
                "warning",
                f'platform_code "{code}" contains words like 番線 / のりば; set only the '
                f'number or letter ("{fixed}")',
                f"platform_code「{code}」に「番線」「のりば」等の語が含まれています。"
                f"番号・英字だけを設定します（「{fixed}」）",
                file="stops.txt",
                line=line,
                field="platform_code",
                spec="stops.txt",
            )
        elif code and unicodedata.normalize("NFKC", code) != code and code.isalnum():
            half = unicodedata.normalize("NFKC", code)
            yield Finding(
                "platform-code-full-width",
                "info",
                f'platform_code "{code}" is full-width; half-width "{half}" matches the '
                "spec examples and what route planners show",
                f"platform_code「{code}」が全角です。半角（「{half}」）を推奨します",
                file="stops.txt",
                line=line,
                field="platform_code",
                spec="stops.txt",
            )
        name = row.get("stop_name", "")
        if row.get("location_type", "") in ("", "0") and (m := _NAME_PLATFORM.search(name)):
            yield Finding(
                "stop-name-platform",
                "warning",
                f'stop_name "{name}" contains a platform number ("{m.group(0)}"); '
                "put it in platform_code and keep the stop name only",
                f"stop_name「{name}」に乗り場番号（「{m.group(0)}」）が含まれています。"
                "乗り場番号は platform_code に設定します",
                file="stops.txt",
                line=line,
                field="stop_name",
                spec="stops.txt",
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


# Full-width ASCII (U+FF01–U+FF5E) often shows up in Japanese-edited URLs (ｈｔｔｐｓ：／／…).
_FULLWIDTH_ASCII = re.compile(r"[\uff01-\uff5e]")
_URL_FIELDS = (
    ("agency", "agency.txt", ("agency_url", "agency_fare_url")),
    ("feed_info", "feed_info.txt", ("feed_publisher_url", "feed_contact_url")),
)


def is_http_url(value: str) -> bool:
    """True when value is an http(s) URL with a host, and no whitespace or full-width ASCII.

    >>> is_http_url("https://example.jp/bus")
    True
    >>> is_http_url("www.example.jp")
    False
    >>> is_http_url("https://example.jp/バス")
    True
    """
    if not value or any(ch.isspace() for ch in value) or _FULLWIDTH_ASCII.search(value):
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme.lower() in ("http", "https") and bool(parsed.netloc)


def urls(feed: Feed) -> Iterator[Finding]:
    """agency_url / feed_publisher_url (and the optional URL columns) must be http(s)."""
    for table, filename, fields in _URL_FIELDS:
        rows = feed.get(table)
        if rows is None:
            continue
        for line, row in rows.with_lines():
            for field in fields:
                val = row.get(field, "")
                if val and not is_http_url(val):
                    yield Finding(
                        "bad-url",
                        "error",
                        f'{field} must be an http(s) URL (found "{val}")',
                        f"{field} は http(s) の URL で設定します（現在「{val}」）",
                        file=filename,
                        line=line,
                        field=field,
                    )


#: fare_attributes.txt enum fields -> allowed values (GTFS-JP v4 fare_attributes.txt).
#: An empty ``transfers`` means unlimited transfers (§4.14), so "" is allowed there.
FARE_ENUMS: dict[str, tuple[str, ...]] = {
    "payment_method": ("0", "1"),
    "transfers": ("", "0", "1", "2"),
}


def fare_value_problem(field: str, value: str) -> tuple[str, str] | None:
    """Why a fare_attributes.txt value is invalid, as (en, ja), or None.

    Covers the enums ``payment_method`` (0 / 1, 必須) and ``transfers``
    (empty / 0 / 1 / 2), ``transfer_duration`` (non-negative seconds) and
    ``ic_price`` (whole yen, or -1 when the IC fare does not apply).

    >>> fare_value_problem("transfers", "") is None
    True
    >>> fare_value_problem("transfers", "３")[0]
    'transfers must be empty (unlimited), 0, 1 or 2 (found "３")'
    >>> fare_value_problem("transfers", "２")[1]
    'transfers は空（無制限）・0・1・2 のいずれかです（現在「２」）（半角の 2 にしてください）'
    """
    if field in FARE_ENUMS:
        if value in FARE_ENUMS[field]:
            return None
        hint, hint_ja = "", ""
        half = unicodedata.normalize("NFKC", value)
        if half != value and half in FARE_ENUMS[field]:
            hint, hint_ja = f" (use half-width {half})", f"（半角の {half} にしてください）"
        if field == "payment_method":
            return (
                "payment_method must be 0 (pay after boarding, to the driver or fare box) "
                f'or 1 (pay before boarding) (found "{value}")' + hint,
                "payment_method は 0（乗車後に運転手・運賃箱等に支払う）か"
                f"1（乗車前に窓口・券売機等で支払う）を設定します（現在「{value}」）" + hint_ja,
            )
        return (
            f'transfers must be empty (unlimited), 0, 1 or 2 (found "{value}")' + hint,
            f"transfers は空（無制限）・0・1・2 のいずれかです（現在「{value}」）" + hint_ja,
        )
    if not value:
        return None
    if field == "transfer_duration" and not re.fullmatch(r"[0-9]+", value):
        return (
            f'transfer_duration must be a whole number of seconds (found "{value}")',
            f"transfer_duration は秒数（0 以上の整数）で設定します（現在「{value}」）",
        )
    if field == "ic_price" and not re.fullmatch(r"-1|[0-9]+(\.0+)?", value):
        return (
            f'ic_price must be whole yen, or -1 when no IC fare applies (found "{value}")',
            f"ic_price は円の整数か、IC 運賃が適用されない場合は -1 です（現在「{value}」）",
        )
    return None


def fares(feed: Feed) -> Iterator[Finding]:
    table = feed["fare_attributes"]
    checked = [f for f in (*FARE_ENUMS, "transfer_duration", "ic_price") if f in table.columns]
    for line, row in table.with_lines():
        for field in checked:
            problem = fare_value_problem(field, row.get(field, ""))
            if problem:
                yield Finding(
                    "bad-fare-value",
                    "error",
                    problem[0],
                    problem[1],
                    file="fare_attributes.txt",
                    line=line,
                    field=field,
                    spec="fare_attributes.txt",
                )
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
        if cur == "JPY" and price and not re.fullmatch(r"[0-9]+(\.0+)?", price):
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
