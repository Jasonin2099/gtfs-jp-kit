"""translations.txt rules: reading (ja-Hrkt) coverage, duplicate keys and record references.

GTFS-JP v4 makes translations.txt 必須, readings (``language=ja-Hrkt``) for
names 必須 and English 推奨.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from .. import spec
from ..feed import Feed
from ..findings import Finding

#: table_name -> primary key column used by record_id.
RECORD_KEYS = {
    "agency": "agency_id",
    "stops": "stop_id",
    "routes": "route_id",
    "trips": "trip_id",
    "stop_times": "trip_id",
    "pathways": "pathway_id",
    "levels": "level_id",
    "attributions": "attribution_id",
}
TABLES = (*RECORD_KEYS, "feed_info")
#: GTFS primary key of translations.txt; GTFS-JP v4 uses the GTFS format as is.
PRIMARY_KEY = ("table_name", "field_name", "language", "record_id", "record_sub_id", "field_value")

#: Hiragana, katakana, prolonged sound mark, middle dot, spaces and a few
#: separators that appear in readings of stop names.
_KANA = re.compile(r"^[\u3041-\u309F\u30A0-\u30FF\u31F0-\u31FF\u3000\s・ー～〜()（）\-]+$")
#: Anything that is not plain ASCII is treated as Japanese text that needs a reading.
_NEEDS_READING = re.compile(r"[^\x00-\x7F]")

#: (table, field, severity) of names whose reading is checked.
READING_TARGETS = (
    ("stops", "stop_name", "error"),
    ("agency", "agency_name", "warning"),
    ("routes", "route_long_name", "warning"),
    ("routes", "route_short_name", "warning"),
    ("trips", "trip_headsign", "warning"),
    ("stop_times", "stop_headsign", "warning"),
)


def is_kana_reading(text: str) -> bool:
    """True if ``text`` is written in kana only, as GTFS-JP asks for readings.

    >>> is_kana_reading("しやくしょまえ")
    True
    >>> is_kana_reading("まるのうち２ちょうめ")
    False
    """
    return bool(_KANA.match(text))


class _Index:
    """Which (table, field, language) combinations are translated, by id or value."""

    def __init__(self, feed: Feed) -> None:
        self.by_id: set[tuple[str, str, str, str]] = set()
        self.by_value: set[tuple[str, str, str, str]] = set()
        for row in feed["translations"]:
            key = (row.get("table_name", ""), row.get("field_name", ""), row.get("language", ""))
            if row.get("record_id"):
                self.by_id.add((*key, row["record_id"]))
            if row.get("field_value"):
                self.by_value.add((*key, row["field_value"]))

    def has(self, table: str, field: str, lang: str, record_id: str, value: str) -> bool:
        return (table, field, lang, record_id) in self.by_id or (
            table,
            field,
            lang,
            value,
        ) in self.by_value


def structure(feed: Feed) -> Iterator[Finding]:
    table = feed.get("translations")
    if table is None:
        return
    if "table_name" not in table.columns and "trans_id" in table.columns:
        yield Finding(
            "translations-old-format",
            "error",
            "translations.txt uses the GTFS-JP v1 (trans_id) format; use the GTFS format",
            "translations.txt が GTFS-JP 初版（trans_id）形式です。GTFS 標準の形式にしてください",
            file="translations.txt",
            spec="translations.txt",
        )
        return
    keys: dict[str, set[str]] = {}
    #: primary key (table_name, field_name, language, record_id, record_sub_id,
    #: field_value) -> (first line, its translation)
    first: dict[tuple[str, ...], tuple[int, str]] = {}
    for line, row in table.with_lines():
        name = row.get("table_name", "")
        f = dict(file="translations.txt", line=line, spec="translations.txt")
        pk = tuple(row.get(c, "") for c in PRIMARY_KEY)
        text = row.get("translation", "")
        if pk in first:
            dup_line, dup_text = first[pk]
            if text == dup_text:
                en, ja = " (identical translation)", "（翻訳も同じ）"
            else:
                en = f" with a different translation ({dup_text!r})"
                ja = f"（翻訳が異なる：「{dup_text}」）"
            yield Finding(
                "translation-duplicate",
                "error",
                f"same key as line {dup_line}{en}",
                f"{dup_line} 行目と同じキーです{ja}",
                field="translation",
                **f,
            )
            continue
        first[pk] = (line, text)
        if name not in TABLES and not feed.has(name):
            yield Finding(
                "translation-unknown-table",
                "error",
                f'table_name "{name}" is not a translatable file in this feed',
                f"table_name「{name}」は翻訳できるファイルではありません",
                field="table_name",
                **f,
            )
            continue
        rid, sub, val = (
            row.get("record_id", ""),
            row.get("record_sub_id", ""),
            row.get("field_value", ""),
        )
        if name == "feed_info":
            if rid or sub or val:
                yield Finding(
                    "translation-feed-info-key",
                    "error",
                    "record_id, record_sub_id and field_value must be empty for feed_info",
                    "feed_info の翻訳では record_id・record_sub_id・field_value は禁止です",
                    **f,
                )
            continue
        if bool(rid) == bool(val):
            yield Finding(
                "translation-key",
                "error",
                "set exactly one of record_id and field_value",
                "record_id と field_value はどちらか一方だけを設定します",
                field="record_id",
                **f,
            )
            continue
        if rid and name == "stop_times" and not sub:
            yield Finding(
                "translation-sub-id",
                "error",
                "record_sub_id (stop_sequence) is required for stop_times with record_id",
                "stop_times を record_id で翻訳するときは record_sub_id（stop_sequence）が必須です",
                field="record_sub_id",
                **f,
            )
        if rid and name in RECORD_KEYS:
            if name not in keys:
                keys[name] = {r.get(RECORD_KEYS[name], "") for r in feed[name]}
            if rid not in keys[name]:
                yield Finding(
                    "translation-unknown-record",
                    "error",
                    f"record_id {rid} does not exist in {name}.txt",
                    f"record_id {rid} が {name}.txt に存在しません",
                    field="record_id",
                    **f,
                )
        if val:
            field_name = row.get("field_name", "")
            values = {r.get(field_name, "") for r in feed[name]}
            if val not in values:
                yield Finding(
                    "translation-unused-value",
                    "warning",
                    f"no {name}.{field_name} equals {val!r}; this translation never applies",
                    f"field_value「{val}」と完全一致する {name}.{field_name} がありません",
                    field="field_value",
                    **f,
                )
        if row.get("language") == "ja-Hrkt":
            text = row.get("translation", "")
            if text and not is_kana_reading(text):
                yield Finding(
                    "reading-not-kana",
                    "warning",
                    f"ja-Hrkt reading {text!r} contains non-kana characters",
                    f"読み仮名「{text}」にかな以外の文字が含まれています（数字等もかなで書きます）",
                    field="translation",
                    **f,
                )


def readings(feed: Feed, profile: spec.Profile | str | None = None) -> Iterator[Finding]:
    english = spec.get_profile(profile).english_recommended
    if not feed.has("translations"):
        return
    idx = _Index(feed)
    for table_name, field_name, severity in READING_TARGETS:
        table = feed.get(table_name)
        if table is None or field_name not in table.columns:
            continue
        key_col = RECORD_KEYS[table_name]
        missing: dict[str, int] = {}
        missing_en = 0
        seen: set[str] = set()
        for line, row in table.with_lines():
            value = row.get(field_name, "")
            if not value or not _NEEDS_READING.search(value):
                continue
            if table_name == "stops" and row.get("location_type", "") not in ("", "0", "1"):
                continue
            rid = row.get(key_col, "")
            if not idx.has(table_name, field_name, "ja-Hrkt", rid, value):
                missing.setdefault(value, line)
            if value not in seen:
                seen.add(value)
                if not idx.has(table_name, field_name, "en", rid, value):
                    missing_en += 1
        for value, line in missing.items():
            yield Finding(
                "reading-missing",
                severity,
                f"{field_name} {value!r} has no ja-Hrkt reading in translations.txt",
                f"{field_name}「{value}」の読み仮名（ja-Hrkt）が translations.txt にありません",
                file=f"{table_name}.txt",
                line=line,
                field=field_name,
                spec="translations.txt",
            )
        if english and missing_en:
            yield Finding(
                "english-missing",
                "info",
                f"{missing_en} distinct {field_name} values have no English (en) translation",
                f"{field_name} のうち {missing_en} 件に英語（en）の翻訳がありません（推奨）",
                file=f"{table_name}.txt",
                field=field_name,
                spec="translations.txt",
            )
